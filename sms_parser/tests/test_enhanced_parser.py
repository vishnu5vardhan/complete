#!/usr/bin/env python3

# Set mock data flag to use fallback data generator instead of calling the API
import os
os.environ["USE_MOCK_DATA"] = "true"

from enhanced_sms_parser import parse_sms
from langchain_wrapper import generate_realistic_sms_data
import json
import traceback

def test_parser():
    """Test the enhanced_sms_parser with different sample SMS messages"""
    
    test_cases = [
        {
            "description": "Credit card transaction",
            "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
            "sender": "HDFCBK"
        },
        {
            "description": "Promotional message",
            "sms": "ARROW End of Season Sale is HERE, Buy 2 Get 2 FREE on Formals, Occasion Wear, & Casuals. Hurry, the best styles will not last! Visit an exclusive store now.",
            "sender": "VK-ARROW"
        },
        {
            "description": "UPI transaction",
            "sms": "Dear Customer, Rs.500.00 debited from your a/c XX5678 to Swiggy on date 05-Apr-25. UPI Ref: 123456789012. Available balance: Rs.12,345.67",
            "sender": "SBIINB"
        },
        {
            "description": "Potential phishing message",
            "sms": "Your SBI account will be blocked today. Please click on https://bit.ly/update-kyc to update your KYC and prevent account suspension.",
            "sender": "INFO-SBI"
        }
    ]
    
    print("Testing generate_realistic_sms_data function...\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test['description']}")
        print(f"SMS: {test['sms']}")
        print(f"Sender: {test['sender']}")
        
        # Call the generate_realistic_sms_data function directly
        try:
            data = generate_realistic_sms_data(test['sms'], test['sender'])
            
            # Print the result in a formatted way
            print("\nDirect Extraction Result:")
            print(f"Type: {data.get('transaction_type', '')}")
            print(f"Amount: {data.get('transaction_amount', 0.0)}")
            print(f"Account: {data.get('account_number', '')}")
            print(f"Merchant: {data.get('merchant', '')}")
            print(f"Balance: {data.get('available_balance', 0.0)}")
        except Exception as e:
            print(f"\nError in direct extraction: {e}")
            traceback.print_exc()
        
        print("\n" + "-" * 80 + "\n")
    
    print("\nTesting enhanced_sms_parser.parse_sms function...\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test['description']}")
        print(f"SMS: {test['sms']}")
        print(f"Sender: {test['sender']}")
        
        # Call the parse_sms function
        try:
            result = parse_sms(test['sms'], test['sender'])
            
            # Print the result in a formatted way
            print("\nResult:")
            print(f"Is Promotional: {result['is_promotional']}")
            print(f"Promo Score: {result['promo_score']}")
            
            if not result['is_promotional']:
                print(f"\nTransaction Details:")
                print(f"  Type: {result['transaction']['transaction_type']}")
                print(f"  Amount: {result['transaction']['transaction_amount']}")
                print(f"  Account: {result['transaction']['account_number']}")
                print(f"  Merchant: {result['transaction']['merchant']}")
                print(f"  Balance: {result['transaction']['available_balance']}")
                
                print(f"\nFraud Detection:")
                print(f"  Is Suspicious: {result['fraud_detection']['is_suspicious']}")
                print(f"  Risk Level: {result['fraud_detection']['risk_level']}")
                print(f"  Indicators: {', '.join(result['fraud_detection']['suspicious_indicators'])}")
        except Exception as e:
            print(f"\nError in parse_sms: {e}")
            traceback.print_exc()
        
        print("\n" + "-" * 80 + "\n")

if __name__ == "__main__":
    test_parser() 