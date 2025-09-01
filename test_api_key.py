# This file makes a simple test to check if the API returns a valid response
"""
    Test using openai API in config.py
"""

from config import Settings
from openai import OpenAI
from google import genai

# openai_key = Settings().OPENAI_API_KEY
# gemini_key = Settings().GEMINI_API_KEY
# gemini_key = "AIzaSyDUqzwa_9Z8Nl99PBHQqlN2FjquH-6xdu4"
gemini_key = "AIzaSyC89aAsZ_37Q8UBY9UMlrLOCzQtwgvtWjg"

def test_gemini_api_key():
    assert gemini_key is not None
    assert gemini_key != "YOUR_GEMINI_API_KEY_HERE"
    response = None
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hello, how can I use the Gemini API?"
        )

        # Show raw response and common metadata fields if present
        print("Raw response:", response)
        model = getattr(response, "model", None)
        resp_id = getattr(response, "id", None) or getattr(response, "response_id", None)
        created = getattr(response, "created", None)
        usage = getattr(response, "usage", None) or getattr(response, "token_usage", None)
        candidates = getattr(response, "candidates", None) or getattr(response, "output", None)

        print("Model:", model, "Response ID:", resp_id, "Created:", created, "Usage:", usage)
        if candidates is not None:
            print("Candidates / output:", candidates)

    except Exception as e:
        err_str = str(e)
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        http_resp = getattr(e, "response", None) or getattr(e, "http_response", None)

        print("Request failed:", err_str)
        if status is not None:
            print("Status/code:", status)
        if http_resp is not None:
            print("HTTP response:", http_resp)

        # Heuristics for common causes
        if "exhaust" in err_str.lower() or "quota" in err_str.lower():
            print("Likely cause: API key exhausted / quota exceeded.")
        if "unavailable" in err_str.lower() or "503" in err_str or "service" in err_str.lower():
            print("Likely cause: service unavailable / down.")
    print("API key being used:", gemini_key, "\n response gotten:", response)


def test_openai_api_key():
    assert openai_key is not None
    assert openai_key != "YOUR_OPENAI_API_KEY_HERE"

    client = OpenAI(api_key=openai_key)
    sample_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": "Hello, how can I use the OpenAI API?"
            }
        ]
    )
    print(sample_response)

test_gemini_api_key()