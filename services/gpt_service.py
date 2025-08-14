import json
import os
import logging
import asyncio
from typing import List, Dict, Any, Tuple
from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)

class GPTService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # the newest OpenAI model is "gpt-4o-mini" which was released after gpt-4.
        # do not change this unless explicitly requested by the user
        self.model = settings.OPENAI_MODEL
    
    async def analyze_conversation_batch(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict], Dict]:
        """
        Analyze a batch of messages for sentiment and overall conversation satisfaction.
        Returns (message_analyses, conversation_analysis)
        """
        try:
            # Prepare customer messages for sentiment analysis
            customer_messages = [
                msg for msg in messages 
                if msg.get('direction') == 'to_company' and msg.get('message_content', '').strip()
            ]
            
            # Analyze individual message sentiments
            message_analyses = []
            if customer_messages:
                message_analyses = await self._analyze_message_sentiments(customer_messages)
            
            # Analyze overall conversation satisfaction
            conversation_analysis = await self._analyze_conversation_satisfaction(messages)
            
            return message_analyses, conversation_analysis
            
        except Exception as e:
            logger.error(f"Error in GPT batch analysis: {e}")
            raise

    async def _analyze_message_sentiments(self, messages: List[Dict[str, Any]]) -> List[Dict]:
        """Analyze sentiment for individual customer messages"""
        try:
            # Prepare batch prompt for efficiency
            message_texts = []
            for i, msg in enumerate(messages):
                content = msg.get('message_content', '').strip()
                if content:
                    message_texts.append(f"Message {i+1}: {content}")
            
            if not message_texts:
                return []
            
            batch_text = "\n\n".join(message_texts)
            
            prompt = f"""Analyze the sentiment of each customer message below. For each message, provide:
- sentiment_score: Integer from 1 (very negative) to 5 (very positive)
- confidence: Float from 0 to 1 indicating confidence in the analysis
- topics: Array of 2-3 key topics/keywords from the message

Messages to analyze:
{batch_text}

Respond with JSON in this exact format:
{{
    "analyses": [
        {{
            "message_index": 1,
            "sentiment_score": 3,
            "confidence": 0.85,
            "topics": ["billing", "complaint"]
        }}
    ]
}}"""

            response = await self._make_gpt_request_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in customer sentiment analysis. Analyze customer messages accurately and provide structured JSON responses."
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
            analyses = result.get('analyses', [])
            
            # Map results back to original messages
            message_analyses = []
            for analysis in analyses:
                msg_idx = analysis.get('message_index', 1) - 1
                if 0 <= msg_idx < len(messages):
                    message_analyses.append({
                        'fb_chat_id': messages[msg_idx].get('fb_chat_id'),
                        'message_content': messages[msg_idx].get('message_content'),
                        'sentiment_score': max(1, min(5, analysis.get('sentiment_score', 3))),
                        'sentiment_confidence': max(0, min(1, analysis.get('confidence', 0.5))),
                        'topics': analysis.get('topics', [])
                    })
            
            return message_analyses
            
        except Exception as e:
            logger.error(f"Error analyzing message sentiments: {e}")
            # Return empty analysis rather than failing completely
            return []

    async def _analyze_conversation_satisfaction(self, messages: List[Dict[str, Any]]) -> Dict:
        """Analyze overall conversation satisfaction"""
        try:
            # Prepare conversation context
            conversation_text = []
            for msg in messages:
                direction = "Customer" if msg.get('direction') == 'to_company' else "Agent"
                content = msg.get('message_content', '').strip()
                if content:
                    conversation_text.append(f"{direction}: {content}")
            
            if not conversation_text:
                return {
                    'satisfaction_score': 3,
                    'satisfaction_confidence': 0.1,
                    'is_satisfied': None,
                    'common_topics': []
                }
            
            conversation = "\n".join(conversation_text)
            
            prompt = f"""Analyze this customer service conversation for overall customer satisfaction. Consider:
- Was the customer's issue resolved?
- Was the agent helpful and responsive?
- What was the customer's tone at the end vs beginning?
- Overall conversation quality

Conversation:
{conversation}

Provide analysis in JSON format:
{{
    "satisfaction_score": 3,
    "confidence": 0.85,
    "is_satisfied": true,
    "resolution_achieved": true,
    "common_topics": ["billing", "technical_support"],
    "summary": "Brief summary of the conversation outcome"
}}

satisfaction_score: 1 (very dissatisfied) to 5 (very satisfied)
confidence: 0 to 1
is_satisfied: true if customer seems satisfied (score >= 4)"""

            response = await self._make_gpt_request_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in customer satisfaction analysis. Evaluate conversations holistically considering resolution, tone, and service quality."
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
            
            satisfaction_score = max(1, min(5, result.get('satisfaction_score', 3)))
            
            return {
                'satisfaction_score': satisfaction_score,
                'satisfaction_confidence': max(0, min(1, result.get('confidence', 0.5))),
                'is_satisfied': result.get('is_satisfied', satisfaction_score >= 4),
                'common_topics': result.get('common_topics', []),
                'resolution_achieved': result.get('resolution_achieved', False)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation satisfaction: {e}")
            return {
                'satisfaction_score': 3,
                'satisfaction_confidence': 0.1,
                'is_satisfied': None,
                'common_topics': []
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
