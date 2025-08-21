"""
Google Gemini Service - Drop-in replacement for GPT service
Implements the same interface as OptimizedGPTService
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
        self.model = genai.GenerativeModel('gemini-1.5-flash')  # Fast and capable model
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
            # Return fallback results for all conversations in the batch
            return [self._create_fallback_result(conv) for conv in conversations]

    def _create_batch_prompt(self, conversations: List[Conversation]) -> str:
        """
        Creates a single prompt to analyze a batch of conversations.
        """
        conversations_json = []
        for conv in conversations:
            # This assumes that conversation objects have a 'messages' attribute
            # that contains a list of message objects with 'message_content'.
            # As this relationship is not yet established, this part will need adjustment
            # once the data model is updated.
            messages_text = "\n".join([m.message_content for m in conv.messages])
            conversations_json.append({
                "chat_id": conv.fb_chat_id,
                "messages": messages_text
            })

        conversations_input = json.dumps(conversations_json, indent=2)

        prompt = f"""
Analyze the following batch of customer service conversations and provide a comprehensive analysis for each in JSON format.

CONVERSATIONS_BATCH:
{conversations_input}

Provide the analysis as a JSON array, with one object per conversation. Use this EXACT JSON format for each object in the array:
{{
    "chat_id": "<the original chat_id>",
    "conversation_analysis": {{
        "satisfaction_score": <1-5 integer>,
        "satisfaction_confidence": <0.0-1.0 float>,
        "is_satisfied": <true/false boolean>,
        "resolution_achieved": <true/false boolean>,
        "common_topics": ["topic1", "topic2", "topic3"]
    }}
}}

ANALYSIS GUIDELINES:
- satisfaction_score: 1=very dissatisfied, 3=neutral, 5=very satisfied
- resolution_achieved: true if the issue was resolved or the customer expressed satisfaction.
- common_topics: 3-5 main topics discussed in the conversation.
- Be concise and accurate.
- Ensure the output is a valid JSON array.
"""
        return prompt

    def _parse_batch_response(self, response: str, original_conversations: List[Conversation]) -> List[Dict]:
        """
        Parses the batch response from Gemini.
        """
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_text = response[json_start:json_end].strip()
            else:
                json_text = response.strip()

            parsed_results = json.loads(json_text)

            # Create a lookup for results by chat_id
            results_by_chat_id = {result.get("chat_id"): result for result in parsed_results}

            final_results = []
            for conv in original_conversations:
                chat_id = conv.fb_chat_id
                result = results_by_chat_id.get(chat_id)
                if result:
                    analysis = result.get("conversation_analysis", {})
                    analysis['id'] = conv.id # Add conversation id for job_service
                    final_results.append(analysis)
                else:
                    final_results.append(self._create_fallback_result(conv))
            
            return final_results

        except Exception as e:
            logger.error(f"Error parsing Gemini batch response: {e}")
            logger.debug(f"Response was: {response}")
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
                    wait_time = (2 ** attempt) * 0.5  # Default exponential backoff
                    match = re.search(r"retry_delay {{'seconds': (\d+)}}", str(e)) # Corrected regex for retry_delay
                    if match:
                        wait_time = int(match.group(1))
                        logger.info(f"Gemini API suggested to wait for {wait_time} seconds.")

                    logger.warning(f"Gemini call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Gemini call failed after {max_retries + 1} attempts: {e}")
                    raise

    def _create_fallback_result(self, conversation: Conversation) -> Dict:
        """Create fallback result when analysis fails"""
        return {
            'id': conversation.id,
            'chat_id': conversation.fb_chat_id,
            'satisfaction_score': 3,
            'satisfaction_confidence': 0.5,
            'is_satisfied': False,
            'resolution_achieved': False,
            'common_topics': ['general inquiry'],
        }

# Global Gemini service instance
gemini_service_instance = None

def get_gemini_service(api_key: str) -> GeminiService:
    global gemini_service_instance
    if gemini_service_instance is None:
        gemini_service_instance = GeminiService(api_key)
    return gemini_service_instance