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
        Creates a single prompt to analyze a batch of conversations based on the 4 Pillars of Service Quality.
        """
        conversations_json = []
        for conv in conversations:
            messages_text = "\n".join([f"{m.social_create_time} - {m.direction}: {m.message_content}" for m in conv.messages])
            conversations_json.append({
                "chat_id": conv.fb_chat_id,
                "messages": messages_text
            })

        conversations_input = json.dumps(conversations_json, indent=2)

        prompt = f"""
Analyze the following batch of customer service conversations. For each conversation, provide a score from 1 to 10 for each of the Four Pillars of Service Quality.

CONVERSATIONS_BATCH:
{conversations_input}

Provide the analysis as a valid JSON array, with one object per conversation. Use this EXACT JSON format for each object:
{{
    "chat_id": "<the original chat_id>",
    "conversation_analysis": {{
        "effectiveness_score": <1-10 float, how well the issue was resolved>,
        "efficiency_score": <1-10 float, how timely and quick the service was>,
        "effort_score": <1-10 float, how easy it was for the customer>,
        "empathy_score": <1-10 float, the emotional tone and rapport>,
        "common_topics": ["topic1", "topic2"]
    }}
}}

ANALYSIS GUIDELINES:
- **effectiveness_score**: Focus on resolution. 1 = unresolved, 10 = fully resolved and confirmed.
- **efficiency_score**: Focus on speed. 1 = very slow, long waits, 10 = instant, efficient responses.
- **effort_score**: Focus on customer ease. 1 = very difficult, repetitive, 10 = seamless and simple.
- **empathy_score**: Focus on tone. 1 = cold, robotic, 10 = warm, empathetic, personalized.
- **common_topics**: Extract 2-3 main topics.
- Base your scores on the entire conversation flow.
- Ensure the output is a single, valid JSON array.
"""
        return prompt

    def _parse_batch_response(self, response: str, original_conversations: List[Conversation]) -> List[Dict]:
        """
        Parses the batch response from Gemini and maps it to conversations.
        """
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_text = response[json_start:json_end].strip()
            else:
                json_text = response.strip()

            parsed_results = json.loads(json_text)
            results_by_chat_id = {result.get("chat_id"): result for result in parsed_results}

            final_results = []
            for conv in original_conversations:
                chat_id = conv.fb_chat_id
                result = results_by_chat_id.get(chat_id)
                if result and "conversation_analysis" in result:
                    analysis = result["conversation_analysis"]
                    analysis['id'] = conv.id
                    analysis['chat_id'] = chat_id
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
        """Create a neutral fallback result when analysis fails."""
        return {
            'id': conversation.id,
            'chat_id': conversation.fb_chat_id,
            'effectiveness_score': 5.0,
            'efficiency_score': 5.0,
            'effort_score': 5.0,
            'empathy_score': 5.0,
            'common_topics': ['analysis_failed'],
        }

# Global Gemini service instance
gemini_service_instance = None

def get_gemini_service(api_key: str) -> GeminiService:
    global gemini_service_instance
    if gemini_service_instance is None:
        gemini_service_instance = GeminiService(api_key)
    return gemini_service_instance
