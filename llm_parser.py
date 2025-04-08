#!/usr/bin/env python3

import os
import json
import time
from typing import Dict, Any, Optional
import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured successfully")
else:
    print("Warning: GEMINI_API_KEY not found in .env file")

def parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Extract JSON object from Gemini response text
    
    Args:
        response_text: Response text from Gemini
        
    Returns:
        Parsed JSON as dictionary, or empty dict on failure
    """
    try:
        # Try to find a JSON block in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            print("[!] No valid JSON found in response")
            return {}
    except Exception as e:
        print(f"[!] Error parsing JSON: {e}")
        return {}

def call_gemini_api(sms_text: str, sender: Optional[str] = None, retries=3, delay=2) -> Dict[str, Any]:
    """
    Call the Gemini API to parse SMS text into structured data
    
    Args:
        sms_text: The SMS text to analyze
        sender: Optional sender ID
        retries: Number of retry attempts
        delay: Delay in seconds between retries
        
    Returns:
        Dictionary containing parsed SMS data
    """
    # Check if we should use mock data for testing
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    
    if use_mock:
        print("[INFO] Using mock data for testing (USE_MOCK_DATA=true)")
        # Import the mock data generator
        try:
            from langchain_wrapper import generate_realistic_sms_data
            return generate_realistic_sms_data(sms_text, sender)
        except ImportError:
            print("[!] Could not import generate_realistic_sms_data, returning empty mock")
            return create_empty_response()
    
    # Initialize Gemini model
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-pro")
    except Exception as e:
        print(f"[!] Error initializing Gemini model: {e}")
        return create_empty_response()
    
    # Construct the prompt
    prompt = f"""You are a financial assistant. Analyze the following SMS and return a JSON object.

SMS: {sms_text}
{f"Sender: {sender}" if sender else ""}

Extract the following fields:
- transaction_amount (float, 0.0 if none)
- available_balance (float, 0.0 if not present)
- account_number (e.g., XX1234 or masked)
- transaction_type (debit, credit, refund, autopay, etc.)
- merchant (store or service name if applicable)
- category (Dining, Grocery, Bill Payment, EMI, etc.)
- transaction_date (yyyy-mm-dd if parsable, else "")
- description (brief summary of what this SMS is about)
- is_promotional (true/false)
- is_fraud (true/false)
- is_banking_sms (true/false — true only for transaction, payment, EMI, credit card use, etc.)
- fraud_risk_level (none, low, high)
- suspicious_indicators (array of strings)

Return JSON only. Example:
{
  "transaction_amount": 689.0,
  "available_balance": 12310.0,
  "account_number": "XX1823",
  "transaction_type": "debit",
  "merchant": "McDonald's",
  "category": "Dining",
  "transaction_date": "2025-04-03",
  "description": "Credit card payment at McDonald's",
  "is_promotional": false,
  "is_fraud": false,
  "is_banking_sms": true,
  "fraud_risk_level": "none",
  "suspicious_indicators": []
}
"""
    
    # Make API call with retries for rate limits
    for attempt in range(retries):
        try:
            completion = model.generate_content(prompt)
            
            # Parse the response
            response_text = completion.text
            parsed_data = parse_json_response(response_text)
            
            if parsed_data:
                # Add metadata
                parsed_data["raw_sms"] = sms_text
                parsed_data["sender"] = sender
                parsed_data["parsed_at"] = datetime.datetime.now().isoformat()
                
                return parsed_data
            else:
                print(f"[!] Failed to parse response (attempt {attempt+1}/{retries})")
        
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                # Rate limit error, retry after delay
                print(f"[!] Rate limit error. Retrying in {delay}s... (Attempt {attempt+1}/{retries})")
                time.sleep(delay)
            else:
                print(f"[!] API call failed: {e}")
                break
    
    # If all retries failed, return empty response with metadata
    return create_empty_response(sms_text, sender)

def create_empty_response(sms_text: str = "", sender: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an empty fallback response when API calls fail
    
    Args:
        sms_text: Original SMS text
        sender: Original sender
        
    Returns:
        Empty structured response
    """
    return {
        "transaction_amount": 0.0,
        "available_balance": 0.0,
        "account_number": "",
        "transaction_type": "",
        "merchant": "",
        "category": "Uncategorized",
        "transaction_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "description": "",
        "is_promotional": False,
        "is_fraud": False,
        "is_banking_sms": False,
        "fraud_risk_level": "none",
        "suspicious_indicators": [],
        "raw_sms": sms_text,
        "sender": sender,
        "parsed_at": datetime.datetime.now().isoformat(),
        "error": "Failed to parse SMS with Gemini API"
    }

if __name__ == "__main__":
    # Simple test
    test_sms = "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00"
    result = call_gemini_api(test_sms, "HDFCBK")
    print(json.dumps(result, indent=2)) 