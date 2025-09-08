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
            max_output_tokens=8192,
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
        "common_topics": ["<list of 1-5 topics discussed>"]
    }}
}}

ANALYSIS GUIDELINES:
- **sentiment_score**: Overall emotional tone from the customer's side for that day.
- **sentiment_shift**: Change in sentiment from the start to the end of the day's interaction.
- **resolution_achieved**: Was the customer's issue resolved by the end of the day's interaction?
- **fcr_score**: Was the issue resolved within this single day's contact, without prior contact days for the same issue?
- **ces**: Customer Effort Score - how easy was it for the customer? 1 indicates very high effort, 7 indicates very low effort.
- Ensure the output is a single, valid JSON array of objects.
- Do not include any text or formatting outside of the JSON array.

TOPIC GUIDELINES:
- For the "common_topics" field, you MUST choose from the following list of allowed topics.
- If multiple topics apply, you can select up to 5.
- If no specific topic fits well, use "Others".
- Allowed Topics: {json.dumps(allowed_topics)}
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

    

    

    

# Global Gemini service instance
gemini_service_instance = None

def get_gemini_service(api_key: str) -> GeminiService:
    global gemini_service_instance
    if gemini_service_instance is None:
        gemini_service_instance = GeminiService(api_key)
    return gemini_service_instance