from google import genai
import sys

client_global = genai.Client(vertexai=True, project='profitscout-fida8', location='global')
try:
    response = client_global.models.generate_content(
        model='gemini-3.0-flash',
        contents='Tell me a joke.'
    )
    print('Response global gemini-3.0-flash:', response.text)
except Exception as e:
    print('Failed global gemini-3.0-flash:', e)

try:
    response = client_global.models.generate_content(
        model='gemini-3-flash-preview',
        contents='Tell me a joke.'
    )
    print('Response global gemini-3-flash-preview:', response.text)
except Exception as e:
    print('Failed global gemini-3-flash-preview:', e)

try:
    response = client_global.models.generate_content(
        model='gemini-3.0-flash-preview',
        contents='Tell me a joke.'
    )
    print('Response global gemini-3.0-flash-preview:', response.text)
except Exception as e:
    print('Failed global gemini-3.0-flash-preview:', e)