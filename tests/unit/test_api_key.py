# This file makes a simple test to check if the API returns a valid response
"""
    Test using openai API in config.py
"""

from config import Settings
from openai import OpenAI
from google import genai

openai_key = Settings().OPENAI_API_KEY
gemini_key = Settings().GEMINI_API_KEY

def test_gemini_api_key():
    assert gemini_key is not None
    assert gemini_key != "YOUR_GEMINI_API_KEY_HERE"

    client = genai.Client(api_key=gemini_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents = "Hello, how can I use the Gemini API?"
    )
    print(response)


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