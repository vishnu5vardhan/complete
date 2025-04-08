#!/usr/bin/env python3

import json
import os
import sys
from sms_parser.parsers.gemini_parser import parse_sms, load_data_from_csv

# Enable mock mode by default but allow overriding for specific tests
os.environ["ENABLE_MOCK_MODE"] = "True"

def print_result(sms, result):
    """Print the SMS and parsed result in a readable format"""
    print("\n" + "-" * 80)
    print(f"SMS: {sms}")
    print("-" * 80)
    print(json.dumps(result, indent=2))
    print("-" * 80)

def test_merchant_detection():
    # Temporarily disable mock mode
    os.environ["ENABLE_MOCK_MODE"] = "False"
    
    test_cases = [
        "Your HDFC Credit Card bill of Rs.12,450 is due on 15-05-2024. Minimum amount due is Rs.1,200.",
        "Your electricity bill payment of Rs.1,200 to TATA POWER has been processed successfully.",
        "Rs.1,299 debited from your account XX7890 at APPLE APP STORE on 03-05-2024.",
        "NEFT transfer of Rs.25,000 to JOHN DOE completed. Transaction ID: NEFT123456",
        "Rs.999 debited from your account XX7890 for NETFLIX subscription. Auto-pay mandate.",
        "Rs.1,499 debited from your account XX7890 for AMAZON PRIME subscription renewal.",
        "Rs.5,000 debited from your account XX7890 for HDFC LOAN EMI payment.",
        "Rs.2,500 debited from your account XX7890 for LIC INSURANCE premium payment.",
        "Rs.1,199 debited from your account XX7890 for SPOTIFY subscription auto-pay."
    ]
    
    print("\nTesting merchant detection:")
    for sms in test_cases:
        print(f"\nTesting SMS: {sms[:50]}...")
        result = parse_sms(sms)
        print(f"  Detected Merchant: {result.get('merchant_name', 'Unknown')}")
        print(f"  Message Type: {result.get('message_type', 'Unknown')}")
    
    # Re-enable mock mode
    os.environ["ENABLE_MOCK_MODE"] = "True"

def main():
    print("Starting SMS parser test...")
    test_merchant_detection()
    print("\nMerchant detection test completed.")

if __name__ == "__main__":
    main() 