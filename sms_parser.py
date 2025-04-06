#!/usr/bin/env python3

import json
import os
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

class Transaction(BaseModel):
    """Pydantic model for transaction data extracted from SMS"""
    transaction_type: str = Field(..., description="Type of transaction (credit, debit, refund, failed)")
    amount: float = Field(..., description="Transaction amount")
    merchant_name: str = Field("", description="Name of merchant or vendor")
    account_masked: str = Field(..., description="Masked account number like xxxx1234")
    date: str = Field(..., description="Transaction date in YYYY-MM-DD format")

def parse_sms(sms_text: str) -> dict:
    """
    Parse financial SMS text using Gemini API
    
    Args:
        sms_text: SMS text containing transaction information
        
    Returns:
        Dictionary with extracted transaction details
        
    Raises:
        ValueError: If parsing fails or response is invalid
    """
    # Try to load prompt from file if available
    prompt_prefix = ""
    try:
        if os.path.exists("prompts/sms_parser.txt"):
            with open("prompts/sms_parser.txt", "r") as f:
                prompt_prefix = f.read().strip() + "\n\n"
    except Exception:
        pass
    
    # Default prompt if file not available
    if not prompt_prefix:
        prompt_prefix = """
Extract the following fields from this financial SMS:
- transaction_type (credit, debit, refund, failed)
- amount (numeric)
- merchant_name (if any)
- account_masked (masked account number or card like xxxx1234)
- date (in YYYY-MM-DD format)

Respond in this exact JSON format:
{
  "transaction_type": "...",
  "amount": ...,
  "merchant_name": "...",
  "account_masked": "...",
  "date": "YYYY-MM-DD"
}

SMS:
"""
    
    # Construct full prompt
    prompt_text = f"{prompt_prefix}{sms_text}"
    
    try:
        # In a real implementation, use Gemini API:
        """
        import google.generativeai as genai
        genai.configure(api_key="your-api-key")  # Replace with actual API key
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt_text)
        llm_response = response.text
        """
        
        # For demonstration, return mocked responses based on SMS patterns
        llm_response = mock_gemini_response(sms_text)
        print("Raw Gemini API response:")
        print(llm_response)
        
        # Parse JSON from response
        try:
            parsed_data = json.loads(llm_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}")
        
        # Validate with Pydantic
        validated_data = Transaction(**parsed_data)
        
        # Return as dictionary using model_dump() instead of dict()
        return validated_data.model_dump()
    
    except ValidationError as e:
        raise ValueError(f"Invalid response format from Gemini: {e}")
    except Exception as e:
        raise ValueError(f"Error processing SMS with Gemini: {e}")

def mock_gemini_response(sms_text: str) -> str:
    """Mock Gemini API response for demonstration purposes"""
    sms_lower = sms_text.lower()
    
    # Mock debited SMS
    if "debited" in sms_lower or "spent" in sms_lower:
        if "swiggy" in sms_lower:
            return """
{
  "transaction_type": "debit",
  "amount": 2499,
  "merchant_name": "Swiggy",
  "account_masked": "xxxx1234",
  "date": "2025-04-04"
}
"""
        else:
            # Generic debit
            return """
{
  "transaction_type": "debit",
  "amount": 1500,
  "merchant_name": "Amazon",
  "account_masked": "xxxx5678",
  "date": "2025-04-03"
}
"""
            
    # Mock credited SMS
    elif "credited" in sms_lower or "received" in sms_lower:
        return """
{
  "transaction_type": "credit",
  "amount": 5000,
  "merchant_name": "",
  "account_masked": "xxxx9999",
  "date": "2025-04-05"
}
"""
    
    # Mock refund
    elif "refund" in sms_lower:
        return """
{
  "transaction_type": "refund",
  "amount": 899,
  "merchant_name": "Flipkart",
  "account_masked": "xxxx4321",
  "date": "2025-04-02"
}
"""
        
    # Default fallback
    else:
        return """
{
  "transaction_type": "debit",
  "amount": 1000,
  "merchant_name": "Unknown",
  "account_masked": "xxxx1111",
  "date": "2025-04-01"
}
"""

def main():
    """Test the SMS parsing functionality with examples"""
    test_sms = [
        "INR 2,499 debited from HDFC A/C xxxx1234 at Swiggy on 04/04/2025. Ref no: 1234567890",
        "INR 5,000 credited to your ICICI A/C xxxx9999 on 05/04/2025",
        "Your refund of INR 899 has been processed to AXIS BANK xxxx4321 for your Flipkart order on 02-04-2025"
    ]
    
    print("SMS PARSING TEST\n")
    
    for i, sms in enumerate(test_sms):
        print(f"\nTest {i+1}: {sms}")
        print("-" * 50)
        
        try:
            parsed_data = parse_sms(sms)
            print("\nValidated Transaction Object:")
            print(json.dumps(parsed_data, indent=2))
        except ValueError as e:
            print(f"Error: {e}")
        
        print("-" * 50)
    
    print("\nNote: In a real implementation, you would need to:")
    print("1. Install required packages: pip install google-generativeai pydantic")
    print("2. Get an API key from Google AI Studio")
    print("3. Uncomment and update the Gemini API code in the parse_sms function")

if __name__ == "__main__":
    main() 