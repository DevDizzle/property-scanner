from google import genai
import os
client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
response = client.models.generate_content(
    model='gemini-3.0-flash',
    contents='Tell me a 1 sentence joke.'
)
print('Response for gemini-3.0-flash:', response.text)
