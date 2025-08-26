"""
Google Gemini Service - Refactored for Customer Satisfaction Index (CSI)
This service analyzes conversation batches to extract the four pillars of satisfaction:
Effectiveness, Efficiency, Effort, and Empathy.
"""
import logging
import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime
import google.generativeai as genai

from models import Conversation

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: str):
        """Initialize Gemini service with API key"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.api_key = api_key

    async def analyze_conversations_batch(self, conversations: List[Conversation]) -> List[Dict]:
        """
        Analyzes a batch of conversations using a single Gemini API call.
        """
        if not conversations:
            return []

        try:
            prompt = self._create_batch_prompt(conversations)
            response_text = await self._call_gemini_with_retry(prompt)
            analysis_results = self._parse_batch_response(response_text, conversations)
            return analysis_results
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            return [self._create_fallback_result(conv) for conv in conversations]

    def _create_batch_prompt(self, conversations: List[Conversation]) -> str:
        """
        Creates a single prompt to analyze a batch of conversations and extract
        the five core micro-metrics for CSI calculation.
        """
        conversations_json = []
        for conv in conversations:
            # Limit messages to the last 20 to keep the prompt concise
            messages_text = "\n".join([f"{m.social_create_time} - {m.direction}: {m.message_content}" for m in conv.messages[-20:]])
            conversations_json.append({
                "fb_chat_id": conv.fb_chat_id,
                "messages": messages_text
            })

        conversations_input = json.dumps(conversations_json, indent=2)

        prompt = f"""
Analyze the following batch of customer service conversations. For each conversation, provide a score from 1 to 10 for each of the five micro-metrics.

CONVERSATIONS_BATCH:
{conversations_input}

Provide the analysis as a valid JSON array, with one object per conversation. Use this EXACT JSON format for each object:
{{
    "fb_chat_id": "<the original fb_chat_id>",
    "conversation_analysis": {{
        "resolution_achieved": <1-10 float, was the customer's issue fully resolved?>,
        "fcr_score": <1-10 float, was the issue resolved in a single contact? 1 if multiple contacts were needed, 10 if resolved on the first try>,
        "response_time_score": <1-10 float, how timely were the agent's responses?>,
        "customer_effort_score": <1-10 float, how much effort did the customer have to put in? 1 for high effort, 10 for low effort>,
        "empathy_score": <1-10 float, what was the emotional tone and rapport of the interaction?>
    }}
}}

ANALYSIS GUIDELINES:
- **resolution_achieved**: 1 = Not resolved at all. 10 = Issue fully resolved and confirmed by the customer.
- **fcr_score**: 1 = Customer had to follow up multiple times. 10 = Resolved in the very first interaction.
- **response_time_score**: 1 = Very long waits between messages. 10 = Near-instantaneous and efficient replies.
- **customer_effort_score**: 1 = Customer had to repeat information, try multiple channels, or was heavily inconvenienced. 10 = Seamless, easy, and simple for the customer.
- **empathy_score**: 1 = Cold, robotic, and unhelpful. 10 = Warm, understanding, and empathetic.
- Base your scores on the entire conversation flow.
- Ensure the output is a single, valid JSON array.
"""
        return prompt

    def _parse_batch_response(self, response: str, original_conversations: List[Conversation]) -> List[Dict]:
        """
        Parses the batch response from Gemini for the five micro-metrics with improved robustness.
        """
        try:
            # Attempt to find a JSON array within the response text, ignoring surrounding text
            json_match = re.search(r"\[\s*\{.*\}\s*\]", response, re.DOTALL)
            if not json_match:
                logger.error("Could not find a valid JSON array in the Gemini response.")
                logger.debug(f"Response was: {response}")
                return [self._create_fallback_result(conv) for conv in original_conversations]

            json_text = json_match.group(0)
            parsed_results = json.loads(json_text)
            results_by_chat_id = {result.get("fb_chat_id"): result for result in parsed_results}

            final_results = []
            for conv in original_conversations:
                chat_id = conv.fb_chat_id
                result = results_by_chat_id.get(chat_id)
                if result and "conversation_analysis" in result:
                    analysis = result["conversation_analysis"]
                    # Add identifiers for mapping back in the job service
                    analysis['id'] = conv.id
                    analysis['fb_chat_id'] = chat_id
                    final_results.append(analysis)
                else:
                    logger.warning(f"No valid analysis found for chat_id {chat_id}. Using fallback.")
                    final_results.append(self._create_fallback_result(conv))
            
            return final_results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Gemini response: {e}", exc_info=True)
            logger.debug(f"Response text being parsed was: {json_text}")
            return [self._create_fallback_result(conv) for conv in original_conversations]
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing Gemini batch response: {e}", exc_info=True)
            logger.debug(f"Full response was: {response}")
            return [self._create_fallback_result(conv) for conv in original_conversations]

    async def _call_gemini_with_retry(self, prompt: str, max_retries: int = 2) -> str:
        """Call Gemini with exponential backoff retry logic"""
        for attempt in range(max_retries + 1):
            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.model.generate_content(prompt))
                
                if response.text:
                    return response.text.strip()
                else:
                    raise Exception("Empty response from Gemini")
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 0.5
                    match = re.search(r"retry_delay {{'seconds': (\d+)}}", str(e))
                    if match:
                        wait_time = int(match.group(1))
                        logger.info(f"Gemini API suggested to wait for {wait_time} seconds.")

                    logger.warning(f"Gemini call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Gemini call failed after {max_retries + 1} attempts: {e}")
                    raise

    def _create_fallback_result(self, conversation: Conversation) -> Dict:
        """Create a neutral fallback result for micro-metrics when analysis fails."""
        return {
            'id': conversation.id,
            'fb_chat_id': conversation.fb_chat_id,
            'resolution_achieved': 5.0,
            'fcr_score': 5.0,
            'response_time_score': 5.0,
            'customer_effort_score': 5.0,
            'empathy_score': 5.0,
            'error': 'analysis_failed'
        }

# Global Gemini service instance
gemini_service_instance = None

def get_gemini_service(api_key: str) -> GeminiService:
    global gemini_service_instance
    if gemini_service_instance is None:
        gemini_service_instance = GeminiService(api_key)
    return gemini_service_instance
