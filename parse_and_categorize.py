#!/usr/bin/env python3

import json
from services.merchant_mapper import load_merchant_map, get_category
from sms_parser import parse_sms

def parse_and_categorize_sms(sms_text):
    """Parse an SMS and categorize the merchant"""
    # Parse the SMS
    parsed_transaction = parse_sms(sms_text)
    
    # Load merchant map (only needs to be done once in a real app)
    merchant_map = load_merchant_map()
    
    # Add category based on merchant name
    merchant_name = parsed_transaction.get("merchant_name", "")
    parsed_transaction["category"] = get_category(merchant_name, merchant_map)
    
    return parsed_transaction

def main():
    """Test SMS parsing and merchant categorization"""
    test_sms = [
        "INR 2,499 debited from HDFC A/C xxxx1234 at Swiggy on 04/04/2025. Ref no: 1234567890",
        "INR 1,299 debited from ICICI A/C xxxx5678 at Amazon.in on 05/04/2025. Order ID: AZ12345",
        "INR 450 debited from SBI A/C xxxx9876 at Zomato on 06/04/2025. Order: #123456",
        "INR 5,000 credited to your ICICI A/C xxxx9999 on 05/04/2025",
        "INR 899 debited from HDFC A/C xxxx1234 at Unknown Store on 07/04/2025"
    ]
    
    print("SMS PARSING AND CATEGORIZATION TEST\n")
    
    for i, sms in enumerate(test_sms):
        print(f"\nTest {i+1}: {sms}")
        print("-" * 60)
        
        try:
            result = parse_and_categorize_sms(sms)
            print("\nParsed and Categorized Transaction:")
            print(json.dumps(result, indent=2))
        except ValueError as e:
            print(f"Error: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    main() 