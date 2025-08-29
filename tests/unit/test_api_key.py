# This file makes a simple test to check if the API returns a valid response
"""
    Test using openai API in config.py
"""

# from config import Settings
from openai import OpenAI
from google import genai

# openai_key = Settings().OPENAI_API_KEY
# gemini_key = Settings().GEMINI_API_KEY
# gemini_key = "AIzaSyDUqzwa_9Z8Nl99PBHQqlN2FjquH-6xdu4"
gemini_key = "AIzaSyC89aAsZ_37Q8UBY9UMlrLOCzQtwgvtWjg"

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



There's something I hadn't said as well. I don't know why we're deleting old records. ofcourse a conversation id will be repeated in future runs. the bigger point should be the day of processing. Also, the logs have two parts, part one uses the gemini 2.5 flash model but the second uses the flash-lite model of the same api.hence why we're seeing two types of errors. Also another big thing I want to plan is i want to be able to query all the conversations based on day or week and each attached metric (both micro, macro and csi) for that conversation. In the frontend I would like to display a table that has a list of conversations with the macro metrics and the topics involved in that conversation along with a view button that displays the transcript of the conversation for the selected day. what would take to build that, do we need a new route or just a well written markdown explaining how to do this in the frontend using existing apis