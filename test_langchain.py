#!/usr/bin/env python3

import os
from dotenv import load_dotenv
import sys
import json

# Load environment variables
load_dotenv()

# Test both the direct Gemini API and the LangChain wrapper
def test_direct_vs_langchain():
    """
    Test that both direct Gemini API and LangChain wrapper produce similar results
    """
    # Import both modules
    import google.generativeai as genai
    from langchain_wrapper import ask_gemini as langchain_ask
    
    # Configure Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env file")
        return
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Test prompt
    test_prompt = "What is the capital of France? Respond in one word."
    
    # Direct call to Gemini API
    try:
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro")
        direct_response = model.generate_content(test_prompt).text.strip()
        print(f"Direct Gemini API response: {direct_response}")
    except Exception as e:
        print(f"Error calling direct Gemini API: {e}")
        direct_response = None
    
    # Call via LangChain wrapper
    try:
        langchain_response = langchain_ask(test_prompt)
        print(f"LangChain wrapper response: {langchain_response}")
    except Exception as e:
        print(f"Error calling LangChain wrapper: {e}")
        langchain_response = None
    
    # Compare responses
    if direct_response and langchain_response:
        print(f"\nResponse comparison:")
        print(f"Direct API: {direct_response}")
        print(f"LangChain: {langchain_response}")
        
        # Check if responses are exactly the same or semantically similar
        if direct_response.lower() == langchain_response.lower():
            print("\n✅ PASS: Responses are identical")
        elif "paris" in direct_response.lower() and "paris" in langchain_response.lower():
            print("\n✅ PASS: Responses are semantically similar")
        else:
            print("\n❌ FAIL: Responses differ significantly")
    else:
        print("\n❌ FAIL: One or both tests failed to get a response")

# Test the SMS parsing functionality
def test_sms_parsing():
    """
    Test SMS parsing with the LangChain integration
    """
    # Import enhanced_sms_parser
    from enhanced_sms_parser import parse_sms
    
    # Test SMS
    test_sms = "Your card ending with 1234 has been debited for Rs.2500 at Swiggy on 05-04-2023. Available balance is Rs.45000."
    
    # Parse the SMS
    try:
        parsed_data = parse_sms(test_sms)
        print("\nSMS Parsing Test:")
        print(f"Input SMS: {test_sms}")
        print("Parsed data:")
        print(json.dumps(parsed_data, indent=2))
        
        # Validate parsed data
        if (parsed_data.get("transaction_type") == "debit" and 
            parsed_data.get("amount") == 2500 and
            "swiggy" in parsed_data.get("merchant_name", "").lower() and
            parsed_data.get("account_masked") == "xxxx1234"):
            print("\n✅ PASS: SMS parsed correctly")
        else:
            print("\n❌ FAIL: SMS parsing results differ from expected")
            print("Expected: debit transaction of Rs.2500 at Swiggy from account xxxx1234")
    except Exception as e:
        print(f"\n❌ FAIL: Error in SMS parsing: {e}")

# Test extracting structured data
def test_structured_extraction():
    """
    Test the structured data extraction with JSONOutputParser
    """
    from langchain_wrapper import extract_structured_data
    
    # Test prompt and schema
    prompt = """
    Extract the following details from this text:
    "John Doe is 30 years old and lives in New York."
    
    Return only the structured data.
    """
    
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "number"},
            "location": {"type": "string"}
        }
    }
    
    try:
        result = extract_structured_data(prompt, schema)
        print("\nStructured Extraction Test:")
        print("Result:")
        print(json.dumps(result, indent=2))
        
        # Validate result
        if (result.get("name") == "John Doe" and 
            result.get("age") == 30 and
            result.get("location") == "New York"):
            print("\n✅ PASS: Structured extraction works correctly")
        else:
            print("\n❌ FAIL: Structured extraction results differ from expected")
    except Exception as e:
        print(f"\n❌ FAIL: Error in structured extraction: {e}")

# Test the end-to-end processing
def test_end_to_end():
    """
    Test the end-to-end processing with LangChain integration
    """
    from enhanced_sms_parser import run_end_to_end
    
    # Test SMS
    test_sms = "Your card ending with 1234 has been debited for Rs.2500 at Swiggy on 05-04-2023. Available balance is Rs.45000."
    
    try:
        print("\nEnd-to-End Processing Test:")
        result = run_end_to_end(test_sms)
        
        print(f"Transaction Type: {result['transaction']['transaction_type']}")
        print(f"Amount: ₹{result['transaction']['amount']}")
        print(f"Merchant: {result['transaction']['merchant_name']}")
        print(f"Category: {result['category']}")
        print(f"Archetype: {result['archetype']}")
        print("Recommendations available" if result.get('top_3_recommendations') else "No recommendations")
        
        # Basic validation
        if (result['transaction']['transaction_type'] == 'debit' and
            result['transaction']['amount'] == 2500):
            print("\n✅ PASS: End-to-end processing works correctly")
        else:
            print("\n❌ FAIL: End-to-end processing results differ from expected")
    except Exception as e:
        print(f"\n❌ FAIL: Error in end-to-end processing: {e}")

if __name__ == "__main__":
    print("=== LangChain Integration Tests ===\n")
    
    # Run all tests or specific tests based on arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "compare":
            test_direct_vs_langchain()
        elif sys.argv[1] == "parse":
            test_sms_parsing()
        elif sys.argv[1] == "extract":
            test_structured_extraction()
        elif sys.argv[1] == "e2e":
            test_end_to_end()
        else:
            print(f"Unknown test: {sys.argv[1]}")
    else:
        # Run all tests
        test_direct_vs_langchain()
        test_sms_parsing()
        test_structured_extraction()
        test_end_to_end() 