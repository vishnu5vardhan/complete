#!/usr/bin/env python3
import os
import json
from enhanced_sms_parser import parse_sms
from typing import Dict, List, Any

# Set to True to use Gemini API, False to use rule-based approach only
os.environ["USE_MOCK_DATA"] = "False"

def test_end_to_end_parsing():
    """Test the end-to-end SMS parsing with various types of messages"""
    
    # Test cases with different types of SMS messages
    test_cases = [
        {
            "description": "Credit Card Transaction",
            "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
            "sender": "HDFCBK",
            "expected_type": "transaction"
        },
        {
            "description": "Debit Card Transaction",
            "sms": "Your a/c XX1234 is debited with Rs.1500.00 for Swiggy order on 2023-07-15. Available balance: Rs.12,345.67.",
            "sender": "SBIINB",
            "expected_type": "transaction"
        },
        {
            "description": "UPI Transaction",
            "sms": "UPI/P2P/VPA-john@upi/Rs.500.00/XX1234/Success/07-15-23/12:30:45/Ref.987654321",
            "sender": "ICICIB",
            "expected_type": "transaction"
        },
        {
            "description": "Promotional Message",
            "sms": "Amazing offer! Get 50% OFF on all products this weekend. Use code SALE50 at checkout. Shop now at www.example.com",
            "sender": "AD-SHOP",
            "expected_type": "promotional"
        },
        {
            "description": "Bank Promotion",
            "sms": "HDFC Bank: Upgrade to our premium credit card and enjoy 5x rewards, lounge access, and more! Apply now at hdfc.in/upgrade",
            "sender": "HDFCBK",
            "expected_type": "promotional"
        },
        {
            "description": "Potential Phishing Message",
            "sms": "URGENT: Your account has been blocked. Click here to verify: bit.ly/3x4mp1e",
            "sender": "UNKNOWN",
            "expected_type": "transaction"  # Should be caught as suspicious
        }
    ]
    
    results = []
    
    print("\n===== SMS PARSING TEST RESULTS =====\n")
    
    for i, case in enumerate(test_cases):
        print(f"Test case #{i+1}: {case['description']}")
        print(f"SMS: {case['sms']}")
        print(f"Sender: {case['sender']}")
        print(f"Expected type: {case['expected_type']}")
        
        # Parse the SMS
        result = parse_sms(case['sms'], case['sender'])
        
        # Determine if correctly classified as promotional or transactional
        is_promotional = result.get("is_promotional", False)
        actual_type = "promotional" if is_promotional else "transaction"
        
        # Check if fraud detection triggered for transaction messages
        fraud_details = ""
        if not is_promotional:
            fraud_info = result.get("fraud_detection", {})
            if fraud_info.get("is_suspicious"):
                fraud_details = f" (Suspicious: {', '.join(fraud_info.get('suspicious_indicators', []))})"
        
        print(f"Actual type: {actual_type}{fraud_details}")
        print(f"Correctly classified: {'✅' if actual_type == case['expected_type'] else '❌'}")
        
        # For transaction messages, show extracted details
        if not is_promotional:
            tx = result.get("transaction", {})
            print(f"Transaction amount: {tx.get('transaction_amount')}")
            print(f"Transaction type: {tx.get('transaction_type')}")
            print(f"Merchant: {tx.get('merchant')}")
        else:
            print(f"Promotional score: {result.get('promo_score', 0)}")
        
        print("\n" + "-"*50 + "\n")
        
        # Store results for summary
        results.append({
            "case": case['description'],
            "correctly_classified": actual_type == case['expected_type'],
            "result": result
        })
    
    # Print summary
    correct = sum(1 for r in results if r["correctly_classified"])
    print(f"\nSummary: {correct}/{len(test_cases)} test cases classified correctly")

if __name__ == "__main__":
    test_end_to_end_parsing() 