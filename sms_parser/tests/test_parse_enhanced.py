#!/usr/bin/env python3

# Set mock data flag to use fallback data generator instead of calling the API
import os
os.environ["USE_MOCK_DATA"] = "true"

from enhanced_sms_parser import parse_sms_enhanced
import json

def test_direct():
    """Directly test the parse_sms_enhanced function with debugging output"""
    
    test_cases = [
        {
            "description": "Credit card transaction",
            "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
            "sender": "HDFCBK"
        },
        {
            "description": "UPI transaction",
            "sms": "Dear Customer, Rs.500.00 debited from your a/c XX5678 to Swiggy on date 05-Apr-25. UPI Ref: 123456789012. Available balance: Rs.12,345.67",
            "sender": "SBIINB"
        }
    ]
    
    print("Testing parse_sms_enhanced function directly...\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test['description']}")
        print(f"SMS: {test['sms']}")
        print(f"Sender: {test['sender']}")
        
        # Call the function directly
        result = parse_sms_enhanced(test['sms'], test['sender'])
        
        print("\nFinal Result from parse_sms_enhanced:")
        print(json.dumps(result, indent=2))
        
        print("\n" + "-" * 80 + "\n")

if __name__ == "__main__":
    test_direct() 