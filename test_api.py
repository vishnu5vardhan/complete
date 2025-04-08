#!/usr/bin/env python3

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use the API key directly
api_key = "AIzaSyD7bvox1jFv4z1ZZk6HX1Wssz9q1ppogNY"
print(f"Using API key: {api_key}")

try:
    # Configure the API
    genai.configure(api_key=api_key)
    
    # List available models
    print("\nListing available models:")
    models = genai.list_models()
    for model in models:
        print(f"- {model.name}")
    
    # Create a simple prompt
    print("\nTesting with gemini-1.5-pro")
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content('Write a short greeting')
    
    print("\nAPI Test Result:")
    print(f"Response received: {bool(response)}")
    print(f"Response text: {response.text}")
    print("\nAPI key is working correctly!")
except Exception as e:
    print(f"\nError testing API: {e}")
    print("\nAPI key might be invalid or there might be connectivity issues.") 