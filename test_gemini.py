#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")
print(f"API key length: {len(api_key) if api_key else 'None'}")

# Configure the API
if api_key:
    print(f"Configuring Gemini with API key: {api_key[:5]}...{api_key[-4:]}")
    genai.configure(api_key=api_key)
else:
    print("Error: No API key found in .env file")
    sys.exit(1)

# Test the API by listing models
try:
    print("Attempting to list models...")
    models = list(genai.list_models())
    print(f"Success! Found {len(models)} models:")
    for model in models:
        print(f"- {model.name}")
except Exception as e:
    print(f"Error: {e}")
    print("\nPossible reasons for the error:")
    print("1. The API key might be invalid")
    print("2. There could be network connectivity issues")
    print("3. The Gemini API service might be experiencing downtime")
    print("\nTry the following:")
    print("1. Verify your API key in the Google AI Studio")
    print("2. Ensure you have internet connectivity")
    print("3. Check if you need to enable the Generative Language API in your Google Cloud project") 