"""
Google Gemini Service - Refactored for Daily CSI Analysis
This service analyzes batches of daily interactions to extract an expanded set of micro-metrics.
"""
import logging
import asyncio
import re
from typing import Dict, List, Any, Tuple
import json
from datetime import datetime
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from models import DailyAnalysis
from config import settings

logger = logging.getLogger(__name__)

# region Custom Exceptions
class GeminiApiException(Exception):
    """Base exception for Gemini service errors."""
    pass

class TransientApiError(GeminiApiException):
    """Represents a temporary error that can be retried (e.g., 5xx, rate limit)."""
    pass

class PermanentApiError(GeminiApiException):
    """Represents a permanent error that should not be retried (e.g., 4xx)."""
    pass

class ParsingError(GeminiApiException):
    """Represents an error in parsing the model's JSON response."""
    pass
# endregion

class GeminiService:
    def __init__(self, api_key: str):
        """Initialize Gemini service with API key"""
        if not api_key:
            raise PermanentApiError("Gemini API key is not configured.")
        if not settings.GEMINI_MODEL:
            raise PermanentApiError("Gemini model name is not configured.")
            
        genai.configure(api_key=api_key)
        
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=65536,  # Max tokens for Gemini 2.5
            temperature=0.1,
            response_mime_type="application/json", # Request JSON output
        )
        
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=generation_config
        )
        self.api_key = api_key

    async def analyze_daily_analyses_batch(self, daily_analyses: List[DailyAnalysis]) -> Tuple[List[Dict], List[int], Dict[str, int], str]:
        """
        Analyzes a batch of DailyAnalysis objects using a single Gemini API call.
        Returns the analysis results, a list of IDs for analyses that were missed
        due to truncation, the token usage metadata, and the raw response text.
        Raises exceptions on failure.
        """
        if not daily_analyses:
            return [], [], {}, ""

        logger.info(f"--- Preparing to call Gemini API for {len(daily_analyses)} daily analyses. ---")
        prompt = self._create_daily_analysis_batch_prompt(daily_analyses)
        
        response_text, usage_metadata = await self._call_gemini_with_retry(prompt)
        
        logger.info(f"--- Successfully received response from Gemini API. Parsing now. ---")
        analysis_results, missed_ids = self._parse_response(response_text, daily_analyses)
        
        return analysis_results, missed_ids, usage_metadata, response_text

    def _create_daily_analysis_batch_prompt(self, daily_analyses: List[DailyAnalysis]) -> str:
        """
        Creates a single prompt to analyze a batch of daily analyses.
        """
        daily_analyses_json = []
        for analysis in daily_analyses:
            messages_text = "\n".join([
                f"{m.social_create_time} - {m.direction}: {m.message_content}" 
                for m in analysis.conversation.messages 
                if m.social_create_time.date() == analysis.analysis_date.date()
            ])
            daily_analyses_json.append({
                "daily_analysis_id": analysis.id,
                "messages": messages_text
            })

        daily_analyses_input = json.dumps(daily_analyses_json, indent=2)

        # Predefined list of topics for the model to choose from
        allowed_topics = [
            "Others", "Blocked prepaid Meters", "Inactive Meter- Non vends", "Contracting",
            "Prepaid Integration", "Prepaid Faulty Meters", "Enquiries On Products/Processes",
            "Disconnection/Reconnection", "New Application Queries", "Advertisements",
            "Prepaid Payment Reallocation", "Token Resending", "Danger calls Complints",
            "Re-Billing", "Compliments", "Safety", "Power Outage Reporting",
            "Power Outage Follow Up", "Billing/Statement Request", "Fraud",
            "Post Paid Faulty Meters", "Prepaid Activation"
        ]

        prompt = f"""
        You are an expert, data-driven customer satisfaction analyst for Kenya Power, an electricity utility company. Your primary goal is to provide highly objective, consistent, and evidence-based scores for specific customer experience micro-metrics from chat interactions. You understand that in the utilities sector, customers often reach out during moments of high frustration (e.g., power outages, billing errors), making effective resolution, low effort, and demonstrated empathy critical.

        Analyze the following batch of customer service interactions, grouped by day for specific conversations. For each daily interaction, you must perform a detailed, step-by-step internal reasoning process (Chain of Thought) before providing your final scores. Your reasoning should explicitly reference customer statements, agent responses, and the flow of the conversation to justify each score against the strict guidelines provided below.

        INTERACTIONS_BATCH DATA:
        Each object in the array below represents a single day's worth of messages for a unique chat_id. Messages are ordered chronologically.

        {daily_analyses_input}

        Provide the analysis as a valid JSON array, with one object per daily interaction. Use this **EXACT JSON format** for each object:
        {{
            "daily_analysis_id": "<the original daily_analysis_id>",
            "daily_analysis": {{
                "sentiment_score": <0-10 float>,
                "sentiment_shift": <-5 to +5 float>,
                "resolution_achieved": <0-10 float>,
                "fcr_score": <0-10 float>,
                "ces": <1-7 float, where 1=very high effort, 7=very low effort>,
                "common_topics": ["<array of strings (1-3 from allowed_topics)>"]
            }}
        }}

        ANALYSIS GUIDELINES FOR SCORING (0-10 scale unless specified otherwise):
        - **resolution_achieved (Effectiveness Pillar):**
            *   **Question:** Was the customer's *core issue* explicitly and successfully resolved by the end of this specific day's interaction, from the customer's perspective?
            *   **Guidance:** Score based on *semantic analysis of conversation content*, not just agent claims. Look for direct customer confirmation of resolution (e.g., "Thanks, it's working now," "My bill is corrected").
            *   **0-3 (Low):** Issue clearly unresolved, customer expresses continued frustration, or agent merely promised follow-up without confirmation.
            *   **4-7 (Medium):** Partial resolution, mixed signals, or resolution is implied but not explicitly confirmed by the customer.
            *   **8-10 (High):** Customer explicitly confirms the issue is resolved and expresses satisfaction with the outcome. A 10 means complete and unambiguous resolution.

        - **fcr_score (Effectiveness Pillar - First Contact Resolution):**
            *   **Question:** Was the customer's *core issue* completely resolved within this *single, continuous interaction segment* (i.e., within the boundaries of this daily analysis data), *without requiring the customer to contact again for the same issue on a subsequent day*, and *without referencing a prior unresolved contact for this same issue*?
            *   **Guidance:** This is a strict measure. A resolution is only FCR if the *entire problem* was addressed from start to finish in this one daily chat. If the customer needed to contact previously for the *same specific issue*, or will need to contact again, it is NOT FCR.
            *   **0 (No FCR):** Issue was not resolved, or required prior/future contacts for the same specific problem.
            *   **10 (FCR Achieved):** The issue was definitively resolved in this single daily interaction, and there's no indication of prior unresolved contacts for this problem, nor a need for future contacts for the same problem.

        - **ces (Effort Pillar - Customer Effort Score):**
            *   **Scale:** 1 (Very High Effort) to 7 (Very Low Effort).
            *   **Guidance:** Assess the *customer's perceived effort* required to get their issue handled. Look for clear indicators of *process friction*.
            *   **Indicators of HIGH Effort (scores 1-3):** Repeated questions from customer, having to re-explain the issue multiple times, **agent ignoring previously provided information**, expressing confusion or frustration about the process, navigating complex instructions, multiple transfers, being deflected to another channel (e.g., "visit our office"), long periods of unresponsiveness, explicit complaints about difficulty.
            *   **Indicators of MEDIUM Effort (scores 4-5):** Some minor friction, slight re-explanation needed, but generally smooth.
            *   **Indicators of LOW Effort (scores 6-7):** Customer expresses ease, no noticeable friction, quick and straightforward resolution, agent clearly understood the issue immediately. A 7 means exceptionally effortless interaction.

        - **sentiment_score (Empathy Pillar):**
            *   **Question:** What was the *customer's overall expressed emotional tone* throughout this specific day's interaction?
            *   **Guidance:** Focus on the customer's language, choice of words, and emotional expressions.
            *   **0-3 (Negative):** Expresses anger, severe frustration, despair, strong dissatisfaction, rude language.
            *   **4-7 (Neutral/Mixed):** Factual, no strong emotion, slightly annoyed but not hostile, polite but distant.
            *   **8-10 (Positive):** Expresses gratitude, relief, satisfaction, politeness, friendly tone. A 10 indicates strong delight or appreciation.

        - **sentiment_shift (Empathy Pillar):**
            *   **Scale:** -5 (Significantly Worsened) to +5 (Significantly Improved).
            *   **Guidance:** Measure the *absolute change in the customer's sentiment from their very first message to their very last message* within this specific day's interaction.
            *   **-5 to -1 (Negative Shift):** Customer's emotional state clearly deteriorated by the end of the conversation.
            *   **0 (No Change):** Sentiment remained consistent, or changes were negligible.
            *   **+1 to +5 (Positive Shift):** Customer's emotional state clearly improved by the end of the conversation. A +5 indicates a dramatic positive change (e.g., from angry to grateful).

        TOPIC GUIDELINES:
        - For the "common_topics" field, you MUST choose from the following list of allowed topics.
        - If multiple topics apply, you can select up to 3.
        - If no specific topic fits well, use "Others".
        - Allowed Topics: {json.dumps(allowed_topics)}

        - Ensure the output is a single, valid JSON array of objects.
        - **Do not include any text, comments, or formatting outside of the final JSON array.**
        """
        return prompt

    def _parse_response(self, response: str, original_analyses: List[DailyAnalysis]) -> Tuple[List[Dict], List[int]]:
        """
        Parses the JSON response from Gemini. If the response is truncated,
        it attempts to salvage all complete JSON objects.

        Returns a tuple containing:
        - A list of successfully parsed result dictionaries.
        - A list of integer IDs for the daily analyses that were missed.
        """
        original_ids = {analysis.id for analysis in original_analyses}

        try:
            parsed_results = json.loads(response)
            logger.info(f"Successfully parsed {len(parsed_results)} objects from complete JSON response.")
            final_results, parsed_ids = self._validate_and_map_results(parsed_results, original_analyses)
            missed_ids = list(original_ids - parsed_ids)
            if missed_ids:
                logger.warning(f"Model response was valid JSON but missed processing IDs: {missed_ids}")
            return final_results, missed_ids

        except json.JSONDecodeError:
            logger.warning("JSON decoding failed. Attempting to salvage from truncated response.")
            
            # Find the last occurrence of what looks like a complete object
            last_complete_obj_pos = response.rfind('}]}')
            if last_complete_obj_pos == -1:
                logger.error(f"Could not find a single complete object in the truncated response.")
                raise ParsingError("Truncated response could not be salvaged.")

            salvageable_str = response[:last_complete_obj_pos + 3]
            
            try:
                parsed_results = json.loads(salvageable_str)
                logger.info(f"Successfully salvaged {len(parsed_results)} objects from truncated response.")
                final_results, parsed_ids = self._validate_and_map_results(parsed_results, original_analyses)
                missed_ids = list(original_ids - parsed_ids)
                logger.warning(f"The following daily_analysis_ids were missed and should be retried: {missed_ids}")
                return final_results, missed_ids

            except json.JSONDecodeError as salvage_error:
                logger.error(f"Failed to parse even the salvaged part of the response: {salvage_error}")
                raise ParsingError("Failed to parse even the salvaged part of the response.") from salvage_error

    def _validate_and_map_results(self, parsed_results: List[Dict], original_analyses: List[DailyAnalysis]) -> Tuple[List[Dict], set]:
        """
        Validates the structure of parsed JSON and maps results back to original IDs.
        """
        if not isinstance(parsed_results, list):
            raise ParsingError(f"Expected a JSON list, but got {type(parsed_results).__name__}")

        results_by_id = {result.get("daily_analysis_id"): result for result in parsed_results}
        final_results = []
        parsed_ids = set()

        for analysis in original_analyses:
            result = results_by_id.get(analysis.id)
            if result and "daily_analysis" in result:
                res = result["daily_analysis"]
                res['daily_analysis_id'] = analysis.id
                final_results.append(res)
                parsed_ids.add(analysis.id)
        
        return final_results, parsed_ids

    async def _call_gemini_with_retry(self, prompt: str, max_retries: int = 2) -> Tuple[str, Dict[str, int]]:
        """
        Call Gemini with exponential backoff retry logic for transient errors.
        """
        for attempt in range(max_retries + 1):
            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.model.generate_content(prompt))
                
                usage = {
                    "prompt_token_count": response.usage_metadata.prompt_token_count,
                    "candidates_token_count": response.usage_metadata.candidates_token_count,
                    "total_token_count": response.usage_metadata.total_token_count,
                }
                return response.text.strip(), usage
            
            except google_exceptions.GoogleAPICallError as e:
                # Categorize Google API errors
                if hasattr(e, 'code') and e.code >= 500: # Server errors
                    error = TransientApiError(f"Gemini API server error (HTTP {e.code}): {e.message}")
                elif hasattr(e, 'code') and e.code == 429: # Rate limiting
                    error = TransientApiError(f"Gemini API rate limit exceeded (HTTP {e.code}): {e.message}")
                elif hasattr(e, 'code'): # Other client errors (4xx) are permanent
                    error = PermanentApiError(f"Gemini API client error (HTTP {e.code}): {e.message}")
                else:
                    error = TransientApiError(f"An unexpected Google API error occurred: {e}")

                if isinstance(error, PermanentApiError) or attempt >= max_retries:
                    logger.error(f"Gemini call failed permanently or after {attempt + 1} attempts: {error}")
                    raise error from e
                
            except Exception as e:
                # Catch-all for other unexpected errors (e.g., network issues)
                error = TransientApiError(f"An unexpected error occurred: {e}")
                if attempt >= max_retries:
                    logger.error(f"Gemini call failed after {max_retries + 1} attempts with unexpected error: {e}")
                    raise error from e

            # If we are here, it's a transient error and we can retry
            wait_time = (2 ** attempt) * 1.0 # Exponential backoff starting at 1s
            logger.warning(f"Gemini call failed (attempt {attempt + 1}), retrying in {wait_time}s: {error}")
            await asyncio.sleep(wait_time)

    def _clean_json_response(self, response_text: str) -> str:
        """Clean and extract JSON from AI response text."""
        # Remove markdown code blocks if present
        if '```json' in response_text:
            start = response_text.find('```json') + 7
            end = response_text.find('```', start)
            if end != -1:
                response_text = response_text[start:end]
        elif '```' in response_text:
            start = response_text.find('```') + 3
            end = response_text.find('```', start)
            if end != -1:
                response_text = response_text[start:end]
        
        # Find JSON object boundaries
        response_text = response_text.strip()
        
        # Try to extract JSON object
        start_idx = response_text.find('{')
        if start_idx != -1:
            # Find matching closing brace
            brace_count = 0
            end_idx = start_idx
            for i, char in enumerate(response_text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if brace_count == 0:
                response_text = response_text[start_idx:end_idx]
        
        return response_text

    async def enhance_interaction_boundaries(self, conversation, rule_boundaries: List) -> List[Dict[str, Any]]:
        """
        AI enhancement of rule-based interaction boundaries.
        Reviews existing boundaries and suggests improvements: merge, split, add, remove.
        
        Args:
            conversation: Conversation object with messages
            rule_boundaries: List of InteractionBoundary objects from rule-based detection
            
        Returns:
            List of boundary enhancement suggestions
        """
        if not rule_boundaries or not conversation.messages:
            logger.info("No boundaries or messages to enhance")
            return []
        
        try:
            # Create boundary enhancement prompt
            prompt = self._create_boundary_enhancement_prompt(conversation, rule_boundaries)
            
            # Call Gemini AI
            response_text, usage_metadata = await self._call_gemini_with_retry(prompt)
            
            # Parse enhancement suggestions
            enhancements = self._parse_boundary_enhancements(response_text)
            
            logger.info(f"AI boundary enhancement completed: {len(enhancements)} suggestions, tokens: {usage_metadata}")
            return enhancements
            
        except Exception as e:
            logger.error(f"AI boundary enhancement failed: {e}")
            return []  # Graceful fallback - no enhancements
    
    def _create_boundary_enhancement_prompt(self, conversation, rule_boundaries: List) -> str:
        """Create AI prompt for boundary enhancement review."""
        
        # Format conversation messages
        messages_text = []
        for i, msg in enumerate(conversation.messages):
            direction = "Customer" if msg.direction == 'to_company' else "Agent"
            timestamp = msg.social_create_time.strftime("%Y-%m-%d %H:%M")
            messages_text.append(f"[{i}] {timestamp} {direction}: {msg.message_content}")
        
        formatted_messages = "\n".join(messages_text)
        
        # Format current rule-based boundaries
        boundaries_info = []
        for i, boundary in enumerate(rule_boundaries):
            if boundary.method.value in ['conversation_start', 'conversation_end']:
                continue  # Skip structural boundaries
            boundaries_info.append({
                "boundary_id": i,
                "message_index": boundary.message_index,
                "detection_method": boundary.method.value,
                "confidence": boundary.confidence,
                "reason": boundary.reason
            })
        
        boundaries_json = json.dumps(boundaries_info, indent=2)
        
        prompt = f"""
You are an expert customer service interaction analyst. Review these rule-based interaction boundaries and suggest improvements for better customer service interaction detection.

CONVERSATION MESSAGES:
{formatted_messages}

CURRENT RULE-BASED BOUNDARIES:
{boundaries_json}

Your task: Analyze if these boundaries create logical customer service interactions. Each interaction should represent one complete customer issue/request cycle.

Consider:
1. **Topic Continuity**: Messages about the same issue should stay together
2. **Resolution Cycles**: Problem → Investigation → Resolution → Confirmation
3. **Natural Breaks**: Clear shifts in topics, issues, or conversation context  
4. **Customer Journey**: Each interaction should have clear beginning and end

Provide suggestions in this EXACT JSON format:
{{
    "boundary_suggestions": [
        {{
            "action": "merge_interactions",
            "boundary_indices": [1, 2],
            "reason": "Both boundaries relate to same power outage issue",
            "confidence": 0.85
        }},
        {{
            "action": "add_boundary",
            "after_message_index": 8,
            "reason": "Clear topic shift from billing to technical issue",
            "confidence": 0.90
        }},
        {{
            "action": "remove_boundary", 
            "boundary_index": 3,
            "reason": "False positive - continuation of same interaction",
            "confidence": 0.80
        }}
    ],
    "overall_assessment": "Brief assessment of current boundary quality"
}}

Actions allowed: "merge_interactions", "add_boundary", "remove_boundary"
"""
        return prompt
    
    def _parse_boundary_enhancements(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse AI boundary enhancement suggestions."""
        try:
            # Clean and parse JSON response
            cleaned_response = self._clean_json_response(response_text)
            enhancement_data = json.loads(cleaned_response)
            
            suggestions = enhancement_data.get('boundary_suggestions', [])
            
            # Validate suggestion format
            valid_suggestions = []
            for suggestion in suggestions:
                if self._validate_enhancement_suggestion(suggestion):
                    valid_suggestions.append(suggestion)
                else:
                    logger.warning(f"Invalid boundary suggestion: {suggestion}")
            
            logger.info(f"Parsed {len(valid_suggestions)} valid boundary enhancement suggestions")
            return valid_suggestions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse boundary enhancement JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return []
        except Exception as e:
            logger.error(f"Error parsing boundary enhancements: {e}")
            return []
    
    def _validate_enhancement_suggestion(self, suggestion: Dict[str, Any]) -> bool:
        """Validate boundary enhancement suggestion format."""
        required_fields = ['action', 'reason', 'confidence']
        valid_actions = ['merge_interactions', 'add_boundary', 'remove_boundary']
        
        # Check required fields
        if not all(field in suggestion for field in required_fields):
            return False
        
        # Check valid action
        if suggestion['action'] not in valid_actions:
            return False
        
        # Check confidence range
        confidence = suggestion.get('confidence', 0)
        if not (0 <= confidence <= 1):
            return False
        
        # Action-specific validation
        action = suggestion['action']
        if action == 'merge_interactions' and 'boundary_indices' not in suggestion:
            return False
        elif action == 'add_boundary' and 'after_message_index' not in suggestion:
            return False
        elif action == 'remove_boundary' and 'boundary_index' not in suggestion:
            return False
        
        return True
    
    async def enhance_interaction_boundaries_batch(self, conversations_with_boundaries: List[Tuple]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Batch AI enhancement of rule-based interaction boundaries for multiple conversations.
        Uses a single API call for cost efficiency and rate limit compliance.
        
        Args:
            conversations_with_boundaries: List of (conversation, rule_boundaries) tuples
            
        Returns:
            Dictionary mapping conversation.id to enhancement suggestions list
        """
        if not conversations_with_boundaries:
            logger.info("No conversations to enhance in batch")
            return {}
        
        try:
            # Create batch enhancement prompt
            prompt = self._create_batch_enhancement_prompt(conversations_with_boundaries)
            
            # Single Gemini API call for all conversations
            response_text, usage_metadata = await self._call_gemini_with_retry(prompt)
            
            # Parse batch enhancement results
            batch_results = self._parse_batch_boundary_enhancements(response_text, conversations_with_boundaries)
            
            logger.info(f"Batch AI enhancement completed: {len(conversations_with_boundaries)} conversations, tokens: {usage_metadata}")
            return batch_results
            
        except Exception as e:
            logger.error(f"Batch AI boundary enhancement failed: {e}")
            return {}  # Graceful fallback - no enhancements

    def _create_batch_enhancement_prompt(self, conversations_with_boundaries: List[Tuple]) -> str:
        """Create AI prompt for batch boundary enhancement review."""
        
        conversations_data = []
        for i, (conversation, rule_boundaries) in enumerate(conversations_with_boundaries):
            # Format messages
            messages_text = []
            for j, msg in enumerate(conversation.messages):
                direction = "Customer" if msg.direction == 'to_company' else "Agent"
                timestamp = msg.social_create_time.strftime("%Y-%m-%d %H:%M")
                messages_text.append(f"[{j}] {timestamp} {direction}: {msg.message_content}")
            
            # Format boundaries (skip structural boundaries)
            boundaries_info = []
            for boundary_idx, boundary in enumerate(rule_boundaries):
                if boundary.method.value not in ['conversation_start', 'conversation_end']:
                    boundaries_info.append({
                        "boundary_id": boundary_idx,
                        "message_index": boundary.message_index,
                        "detection_method": boundary.method.value,
                        "confidence": boundary.confidence,
                        "reason": boundary.reason
                    })
            
            conversations_data.append({
                "conversation_id": conversation.id,
                "messages": messages_text,
                "boundaries": boundaries_info
            })
        
        conversations_json = json.dumps(conversations_data, indent=2)
        
        return f"""
You are an expert customer service interaction analyst. Review rule-based interaction boundaries for multiple conversations and suggest improvements for better interaction detection.

BATCH CONVERSATIONS DATA:
{conversations_json}

Your task: For each conversation, analyze if the boundaries create logical customer service interactions. Each interaction should represent one complete customer issue/request cycle.

Consider:
1. **Topic Continuity**: Messages about the same issue should stay together
2. **Resolution Cycles**: Problem → Investigation → Resolution → Confirmation  
3. **Natural Breaks**: Clear shifts in topics, issues, or conversation context
4. **Customer Journey**: Each interaction should have clear beginning and end

Provide suggestions in this EXACT JSON format:
{{
    "batch_results": [
        {{
            "conversation_id": 123,
            "boundary_suggestions": [
                {{
                    "action": "merge_interactions",
                    "boundary_indices": [1, 2],
                    "reason": "Both boundaries relate to same power outage issue",
                    "confidence": 0.85
                }},
                {{
                    "action": "add_boundary", 
                    "after_message_index": 8,
                    "reason": "Clear topic shift from billing to technical issue",
                    "confidence": 0.90
                }}
            ]
        }}
    ]
}}

Valid actions: "merge_interactions", "add_boundary", "remove_boundary"
Only suggest high-confidence improvements (confidence >= 0.7)
Return empty boundary_suggestions array if no improvements needed.
"""

    def _parse_batch_boundary_enhancements(self, response_text: str, conversations_with_boundaries: List[Tuple]) -> Dict[int, List[Dict[str, Any]]]:
        """Parse batch boundary enhancement results."""
        try:
            response_text = self._clean_json_response(response_text)
            data = json.loads(response_text)
            
            results = {}
            if 'batch_results' in data:
                for result in data['batch_results']:
                    conv_id = result.get('conversation_id')
                    suggestions = result.get('boundary_suggestions', [])
                    
                    # Validate suggestions
                    valid_suggestions = []
                    for suggestion in suggestions:
                        if self._validate_enhancement_suggestion(suggestion):
                            valid_suggestions.append(suggestion)
                    
                    if conv_id:
                        results[conv_id] = valid_suggestions
            
            logger.info(f"Parsed batch enhancement results for {len(results)} conversations")
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse batch boundary enhancements: {e}")
            return {}

# Global Gemini service instance
gemini_service_instance = None

def get_gemini_service(api_key: str) -> GeminiService:
    global gemini_service_instance
    if gemini_service_instance is None:
        gemini_service_instance = GeminiService(api_key)
    return gemini_service_instance