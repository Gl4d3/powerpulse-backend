import json
import os
import logging
import asyncio
from typing import List, Dict, Any, Tuple
from openai import OpenAI

from config import settings
from models import Conversation

logger = logging.getLogger(__name__)

class GPTService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.GPT_MODEL

    async def analyze_conversations_batch(self, conversations: List[Conversation]) -> List[Dict]:
        """
        Analyzes a batch of conversations using a single GPT API call.
        """
        if not conversations:
            return []

        try:
            prompt = self._create_batch_prompt(conversations)
            response = await self._make_gpt_request_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in customer satisfaction analysis. Analyze conversations holistically and provide structured JSON responses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            analysis_results = self._parse_batch_response(result, conversations)
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in GPT batch analysis: {e}")
            return [self._create_fallback_result(conv) for conv in conversations]

    def _create_batch_prompt(self, conversations: List[Conversation]) -> str:
        """
        Creates a single prompt to analyze a batch of conversations.
        """
        conversations_json = []
        for conv in conversations:
            messages_text = "\n".join([f"{'Customer' if m.direction == 'to_company' else 'Agent'}: {m.message_content}" for m in conv.messages])
            conversations_json.append({
                "chat_id": conv.fb_chat_id,
                "messages": messages_text
            })

        conversations_input = json.dumps(conversations_json, indent=2)

        prompt = f"""
Analyze the following batch of customer service conversations and provide a comprehensive analysis for each in JSON format.

CONVERSATIONS_BATCH:
{conversations_input}

Provide the analysis as a JSON array under the "analyses" key, with one object per conversation. Use this EXACT JSON format for each object in the array:
{{
    "chat_id": "<the original chat_id>",
    "satisfaction_score": <1-5 integer>,
    "satisfaction_confidence": <0.0-1.0 float>,
    "is_satisfied": <true/false boolean>,
    "resolution_achieved": <true/false boolean>,
    "common_topics": ["topic1", "topic2", "topic3"]
}}

ANALYSIS GUIDELINES:
- satisfaction_score: 1=very dissatisfied, 3=neutral, 5=very satisfied
- resolution_achieved: true if the issue was resolved or the customer expressed satisfaction.
- common_topics: 3-5 main topics discussed in the conversation.
- Be concise and accurate.
- Ensure the output is a valid JSON object with the "analyses" key containing an array.
"""
        return prompt

    def _parse_batch_response(self, result: Dict, original_conversations: List[Conversation]) -> List[Dict]:
        """
        Parses the batch response from GPT.
        """
        analyses = result.get("analyses", [])
        results_by_chat_id = {res.get("chat_id"): res for res in analyses}

        final_results = []
        for conv in original_conversations:
            chat_id = conv.fb_chat_id
            res = results_by_chat_id.get(chat_id)
            if res:
                res['id'] = conv.id # Add conversation id for job_service
                final_results.append(res)
            else:
                final_results.append(self._create_fallback_result(conv))
        
        return final_results

    def _create_fallback_result(self, conversation: Conversation) -> Dict:
        """Create fallback result when analysis fails"""
        return {
            'id': conversation.id,
            'chat_id': conversation.fb_chat_id,
            'satisfaction_score': 3,
            'satisfaction_confidence': 0.1,
            'is_satisfied': None,
            'common_topics': [],
            'resolution_achieved': False
        }

    async def _make_gpt_request_with_retry(self, messages: List[Dict], response_format: Dict = None, temperature: float = 0.1, max_retries: int = 2) -> Any:
        """Make GPT request with exponential backoff retry logic"""
        for attempt in range(max_retries + 1):
            try:
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }
                
                if response_format:
                    request_params["response_format"] = response_format
                
                response = self.client.chat.completions.create(**request_params)
                return response
                
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"GPT request failed after {max_retries + 1} attempts: {e}")
                    raise
                
                # Exponential backoff: 2^attempt seconds
                wait_time = 2 ** attempt
                logger.warning(f"GPT request attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

# Global instance
gpt_service = GPTService()