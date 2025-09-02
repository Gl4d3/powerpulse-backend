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

from models import DailyAnalysis
from config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: str):
        """Initialize Gemini service with API key"""
        genai.configure(api_key=api_key)
        
        # Configure generation parameters for large outputs
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=8192,  # Increase output token limit
            temperature=0.1,         # Low temperature for consistent output
            top_p=0.8,
            top_k=40
        )
        
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config=generation_config
        )
        self.api_key = api_key

    async def analyze_daily_analyses_batch(self, daily_analyses: List[DailyAnalysis]) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Analyzes a batch of DailyAnalysis objects using a single Gemini API call.
        Returns the analysis results and the token usage metadata.
        """
        if not daily_analyses:
            return [], {}

        try:
            logger.info(f"--- Preparing to call Gemini API for {len(daily_analyses)} daily analyses. ---")
            prompt = self._create_daily_analysis_batch_prompt(daily_analyses)
            response, usage_metadata = await self._call_gemini_with_retry(prompt)
            logger.info(f"--- Successfully received response from Gemini API. Parsing now. ---")
            analysis_results = self._parse_daily_analysis_batch_response(response, daily_analyses)
            return analysis_results, usage_metadata
        except Exception as e:
            logger.error(f"--- Gemini API call failed catastrophically after retries. Using fallbacks. ---", exc_info=True)
            return [self._create_fallback_result_daily(da) for da in daily_analyses], {}

    def _create_daily_analysis_batch_prompt(self, daily_analyses: List[DailyAnalysis]) -> str:
        """
        Creates a single prompt to analyze a batch of daily analyses and extract
        the expanded set of micro-metrics for CSI calculation.
        """
        daily_analyses_json = []
        for analysis in daily_analyses:
            # This assumes the conversation and its messages are loaded with the DailyAnalysis object.
            # This might require adjusting the query in the job_service.
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

        prompt = f"""
Analyze the following batch of customer service interactions, grouped by day. For each daily interaction, provide a score for each of the specified micro-metrics.

INTERACTIONS_BATCH:
{daily_analyses_input}

Provide the analysis as a valid JSON array, with one object per daily interaction. Use this EXACT JSON format for each object:
{{
    "daily_analysis_id": "<the original daily_analysis_id>",
    "daily_analysis": {{
        "sentiment_score": <0-10 float>,
        "sentiment_shift": <-5 to +5 float>,
        "resolution_achieved": <0-10 float>,
        "fcr_score": <0-10 float>,
        "ces": <1-7 float, where 1 is high effort and 7 is low effort>,
        "common_topics": ["<list of 3-5 topics discussed>"]
    }}
}}

ANALYSIS GUIDELINES:
- **sentiment_score**: Overall emotional tone from the customer's side for that day.
- **sentiment_shift**: Change in sentiment from the start to the end of the day's interaction.
- **resolution_achieved**: Was the customer's issue resolved by the end of the day's interaction?
- **fcr_score**: Was the issue resolved within this single day's contact, without prior contact days for the same issue?
- **ces**: Customer Effort Score - how easy was it for the customer? 1 indicates very high effort, 7 indicates very low effort.
- **..._response_time**: Calculate these based on the timestamps provided for the day. If not applicable (e.g., no agent response), use null.
- **total_handling_time**: Estimate the total active time spent by the agent on this conversation for the day.
- Ensure the output is a single, valid JSON array.
"""
        return prompt

    def _parse_daily_analysis_batch_response(self, response: str, original_analyses: List[DailyAnalysis]) -> List[Dict]:
        """
        Parses the batch response from Gemini for the daily analysis micro-metrics.
        This function is designed to be robust against malformed JSON or extra text from the LLM.
        """
        try:
            # Find the start and end of the main JSON array
            start_index = response.find('[')
            end_index = response.rfind(']') + 1
            
            if start_index == -1 or end_index == 0:
                logger.error("❌ Could not find a valid JSON array in the Gemini response for daily analysis.")
                logger.debug(f"Full raw response from Gemini: {response}")
                return [self._create_fallback_result_daily(da) for da in original_analyses]

            json_text = response[start_index:end_index]
            
            # Clean up potential markdown formatting
            json_text = json_text.strip().replace("```json", "").replace("```", "").strip()

            # Save raw response for debugging
            self._save_raw_response(response, json_text, len(original_analyses))

            try:
                parsed_results = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from Gemini response: {e}")
                logger.error(f"Batch size: {len(original_analyses)} analyses")
                logger.error(f"JSON text length: {len(json_text)} characters")
                logger.error(f"Response ends with: ...{json_text[-100:] if len(json_text) > 100 else json_text}")
                
                # Try to repair common JSON issues
                repaired_json = self._attempt_json_repair(json_text)
                if repaired_json:
                    try:
                        parsed_results = json.loads(repaired_json)
                        logger.info("Successfully parsed JSON after repair!")
                    except json.JSONDecodeError:
                        logger.error("JSON repair failed, using fallback results")
                        return [self._create_fallback_result_daily(da) for da in original_analyses]
                else:
                    logger.error("Could not repair JSON, using fallback results")
                    return [self._create_fallback_result_daily(da) for da in original_analyses]
            results_by_id = {result.get("daily_analysis_id"): result for result in parsed_results}

            final_results = []
            for analysis in original_analyses:
                result = results_by_id.get(analysis.id)
                if result and "daily_analysis" in result:
                    res = result["daily_analysis"]
                    res['daily_analysis_id'] = analysis.id
                    final_results.append(res)
                else:
                    logger.warning(f"No valid analysis found for daily_analysis_id {analysis.id}. Using fallback.")
                    final_results.append(self._create_fallback_result_daily(analysis))
            
            return final_results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Gemini response: {e}", exc_info=True)
            logger.debug(f"Attempted to parse text: {json_text}")
            return [self._create_fallback_result_daily(da) for da in original_analyses]
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing Gemini daily batch response: {e}", exc_info=True)
            return [self._create_fallback_result_daily(da) for da in original_analyses]

    async def _call_gemini_with_retry(self, prompt: str, max_retries: int = 2) -> Tuple[str, Dict[str, int]]:
        """Call Gemini with exponential backoff retry logic"""
        for attempt in range(max_retries + 1):
            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, lambda: self.model.generate_content(prompt))
                
                if response.text:
                    usage = {
                        "prompt_token_count": response.usage_metadata.prompt_token_count,
                        "candidates_token_count": response.usage_metadata.candidates_token_count,
                        "total_token_count": response.usage_metadata.total_token_count,
                    }
                    return response.text.strip(), usage
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

    def _save_raw_response(self, full_response: str, json_part: str, batch_size: int):
        """Save raw Gemini response for debugging in versioned directories"""
        import os
        from datetime import datetime
        
        # Create versioned debug directory
        today = datetime.now().strftime("%Y%m%d")
        debug_dir = f"logs/gemini_responses/run_{today}"
        os.makedirs(debug_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{debug_dir}/gemini_response_{timestamp}_batch_{batch_size}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Batch size: {batch_size}\n")
                f.write(f"API Key: {self.api_key[:10]}...\n")
                f.write(f"Model: gemini-1.5-flash\n")
                f.write("="*80 + "\n")
                f.write("FULL RESPONSE:\n")
                f.write("="*80 + "\n")
                f.write(full_response)
                f.write("\n" + "="*80 + "\n")
                f.write("EXTRACTED JSON PART:\n")
                f.write("="*80 + "\n")
                f.write(json_part)
                f.write("\n")
            
            logger.info(f"Saved raw Gemini response to: {filename}")
        except Exception as e:
            logger.error(f"Failed to save raw response: {e}")

    def _attempt_json_repair(self, json_text: str) -> str:
        """Attempt to repair common JSON issues, especially truncated arrays"""
        try:
            # Common fixes for Gemini JSON issues
            repaired = json_text
            
            # Fix trailing commas
            repaired = re.sub(r',\s*}', '}', repaired)
            repaired = re.sub(r',\s*]', ']', repaired)
            
            # Fix missing commas between objects (basic attempt)
            repaired = re.sub(r'}\s*{', '},{', repaired)
            
            # Fix unescaped quotes in strings (basic attempt)
            repaired = re.sub(r'(?<!\\)"(?![,:}\]\s])', '\\"', repaired)
            
            # Handle truncated JSON arrays - if the JSON ends abruptly without closing
            if not repaired.rstrip().endswith(']'):
                # Count unclosed objects/arrays and try to close them
                open_braces = repaired.count('{') - repaired.count('}')
                open_brackets = repaired.count('[') - repaired.count(']')
                
                # Remove any incomplete trailing content
                last_complete_brace = repaired.rfind('}')
                if last_complete_brace > -1:
                    # Find if there's incomplete content after the last complete object
                    remaining = repaired[last_complete_brace + 1:].strip()
                    if remaining and not remaining.startswith(',') and not remaining == ']':
                        repaired = repaired[:last_complete_brace + 1]
                        logger.info(f"Removed incomplete trailing content: {remaining[:100]}...")
                
                # Close any remaining open structures
                for _ in range(open_braces):
                    repaired += '}'
                for _ in range(open_brackets):
                    repaired += ']'
                
                logger.info(f"Added {open_braces} closing braces and {open_brackets} closing brackets")
            
            # Try to validate the repaired JSON
            json.loads(repaired)
            logger.info("JSON repair successful")
            return repaired
            
        except Exception as e:
            logger.error(f"JSON repair failed: {e}")
            return None

    def _create_fallback_result_daily(self, daily_analysis: DailyAnalysis) -> Dict:
        """Create a neutral fallback result for daily micro-metrics when analysis fails."""
        return {
            'daily_analysis_id': daily_analysis.id,
            'sentiment_score': 5.0,
            'sentiment_shift': 0.0,
            'resolution_achieved': 5.0,
            'fcr_score': 5.0,
            'ces': 4.0,
            'common_topics': [],
            'error': 'analysis_failed'
        }

# Global Gemini service instance
gemini_service_instance = None

def get_gemini_service(api_key: str) -> GeminiService:
    global gemini_service_instance
    if gemini_service_instance is None:
        gemini_service_instance = GeminiService(api_key)
    return gemini_service_instance