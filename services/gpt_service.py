import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from openai import AsyncOpenAI
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class OptimizedGPTService:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Using GPT-4o for better performance
        
    async def batch_analyze_conversations(
        self, 
        conversations: List[Dict], 
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Optimized batch processing of conversations using GPT-4o
        Combines sentiment analysis and satisfaction scoring in single calls
        """
        try:
            results = []
            batch_size = 5  # Process 5 conversations simultaneously
            
            # Process conversations in batches
            for i in range(0, len(conversations), batch_size):
                batch = conversations[i:i + batch_size]
                
                # Create concurrent tasks for the batch
                tasks = [
                    self._analyze_single_conversation(conv)
                    for conv in batch
                ]
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and handle exceptions
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Error processing conversation {batch[j].get('chat_id')}: {result}")
                        # Fallback result
                        results.append(self._create_fallback_result(batch[j]))
                    else:
                        results.append(result)
                
                # Update progress
                if progress_callback:
                    progress = min(100, ((i + len(batch)) / len(conversations)) * 100)
                    await progress_callback(progress, f"Processed {i + len(batch)}/{len(conversations)} conversations")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            raise
    
    async def _analyze_single_conversation(self, conversation: Dict) -> Dict:
        """
        Analyze a single conversation with optimized prompt
        Combines all analysis in one GPT call
        """
        try:
            messages = conversation.get('messages', [])
            chat_id = conversation.get('chat_id')
            
            if not messages:
                return self._create_fallback_result(conversation)
            
            # Create optimized prompt that gets everything in one call
            prompt = self._create_comprehensive_prompt(messages)
            
            # Single GPT call with retry logic
            response = await self._call_gpt_with_retry(prompt)
            
            # Parse the comprehensive response
            analysis = self._parse_comprehensive_response(response, messages)
            analysis['chat_id'] = chat_id
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing conversation {chat_id}: {e}")
            return self._create_fallback_result(conversation)
    
    def _create_comprehensive_prompt(self, messages: List[Dict]) -> str:
        """
        Create an optimized prompt that gets all analysis in one call
        """
        # Format messages for analysis
        conversation_text = self._format_messages_for_analysis(messages)
        
        prompt = f"""
Analyze this customer service conversation and provide a comprehensive analysis in JSON format.

CONVERSATION:
{conversation_text}

Provide analysis in this EXACT JSON format:
{{
    "conversation_analysis": {{
        "satisfaction_score": <1-5 integer>,
        "satisfaction_confidence": <0.0-1.0 float>,
        "is_satisfied": <true/false boolean>,
        "resolution_achieved": <true/false boolean>,
        "common_topics": ["topic1", "topic2", "topic3"]
    }},
    "message_analyses": [
        {{
            "message_content": "<exact message content>",
            "sentiment_score": <-1.0 to 1.0 float>,
            "sentiment_confidence": <0.0-1.0 float>,
            "topics": ["topic1", "topic2"]
        }}
    ]
}}

ANALYSIS GUIDELINES:
- satisfaction_score: 1=very dissatisfied, 3=neutral, 5=very satisfied
- sentiment_score: -1.0=very negative, 0.0=neutral, 1.0=very positive
- Only analyze customer messages (to_company) for sentiment
- Include agent messages in topics but not sentiment
- resolution_achieved: true if issue was resolved or customer expressed satisfaction
- common_topics: 3-5 main topics discussed (e.g., "token error", "technical support", "billing")
- Be concise and accurate
"""
        
        return prompt
    
    def _format_messages_for_analysis(self, messages: List[Dict]) -> str:
        """Format messages in a clean way for GPT analysis"""
        formatted = []
        
        for msg in messages:
            content = msg.get('message_content', '').strip()
            direction = msg.get('direction', '')
            timestamp = msg.get('social_create_time', '')
            
            if not content:
                continue
                
            speaker = "CUSTOMER" if direction == "to_company" else "AGENT"
            formatted.append(f"[{speaker}]: {content}")
        
        return "\n".join(formatted)
    
    async def _call_gpt_with_retry(self, prompt: str, max_retries: int = 2) -> str:
        """Call GPT with exponential backoff retry logic"""
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert customer service analyst. Provide accurate, structured analysis in valid JSON format only."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                    logger.warning(f"GPT call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"GPT call failed after {max_retries + 1} attempts: {e}")
                    raise
    
    def _parse_comprehensive_response(self, response: str, original_messages: List[Dict]) -> Dict:
        """Parse the comprehensive GPT response"""
        try:
            # Extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_text = response[json_start:json_end].strip()
            else:
                json_text = response.strip()
            
            parsed = json.loads(json_text)
            
            # Extract conversation-level analysis
            conv_analysis = parsed.get('conversation_analysis', {})
            message_analyses = parsed.get('message_analyses', [])
            
            # Create message analysis lookup
            msg_analysis_lookup = {}
            for analysis in message_analyses:
                content = analysis.get('message_content', '')
                if content:
                    msg_analysis_lookup[content] = analysis
            
            # Match analyses to original messages
            enriched_messages = []
            for msg in original_messages:
                content = msg.get('message_content', '').strip()
                direction = msg.get('direction', '')
                
                # Get analysis for this message
                analysis = msg_analysis_lookup.get(content, {})
                
                enriched_msg = {
                    'message_content': content,
                    'direction': direction,
                    'social_create_time': msg.get('social_create_time'),
                    'sentiment_score': analysis.get('sentiment_score') if direction == 'to_company' else None,
                    'sentiment_confidence': analysis.get('sentiment_confidence') if direction == 'to_company' else None,
                    'topics': analysis.get('topics', [])
                }
                enriched_messages.append(enriched_msg)
            
            return {
                'satisfaction_score': conv_analysis.get('satisfaction_score', 3),
                'satisfaction_confidence': conv_analysis.get('satisfaction_confidence', 0.5),
                'is_satisfied': conv_analysis.get('is_satisfied', False),
                'resolution_achieved': conv_analysis.get('resolution_achieved', False),
                'common_topics': conv_analysis.get('common_topics', []),
                'message_analyses': enriched_messages
            }
            
        except Exception as e:
            logger.error(f"Error parsing GPT response: {e}")
            logger.debug(f"Response was: {response}")
            
            # Return fallback analysis
            return {
                'satisfaction_score': 3,
                'satisfaction_confidence': 0.5,
                'is_satisfied': False,
                'resolution_achieved': False,
                'common_topics': ['general inquiry'],
                'message_analyses': [
                    {
                        'message_content': msg.get('message_content', ''),
                        'direction': msg.get('direction', ''),
                        'social_create_time': msg.get('social_create_time'),
                        'sentiment_score': 0.0 if msg.get('direction') == 'to_company' else None,
                        'sentiment_confidence': 0.5 if msg.get('direction') == 'to_company' else None,
                        'topics': []
                    }
                    for msg in original_messages
                ]
            }
    
    def _create_fallback_result(self, conversation: Dict) -> Dict:
        """Create fallback result when analysis fails"""
        messages = conversation.get('messages', [])
        
        return {
            'chat_id': conversation.get('chat_id'),
            'satisfaction_score': 3,
            'satisfaction_confidence': 0.5,
            'is_satisfied': False,
            'resolution_achieved': False,
            'common_topics': ['general inquiry'],
            'message_analyses': [
                {
                    'message_content': msg.get('message_content', ''),
                    'direction': msg.get('direction', ''),
                    'social_create_time': msg.get('social_create_time'),
                    'sentiment_score': 0.0 if msg.get('direction') == 'to_company' else None,
                    'sentiment_confidence': 0.5 if msg.get('direction') == 'to_company' else None,
                    'topics': []
                }
                for msg in messages
            ]
        }

# Global optimized service instance
optimized_gpt_service = None

def get_optimized_gpt_service(api_key: str) -> OptimizedGPTService:
    global optimized_gpt_service
    if optimized_gpt_service is None:
        optimized_gpt_service = OptimizedGPTService(api_key)
    return optimized_gpt_service