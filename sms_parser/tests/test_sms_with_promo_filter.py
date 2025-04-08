#!/usr/bin/env python3

import json
import os
from enhanced_sms_parser import parse_sms

# Set environment variable to use mock data for testing
os.environ["USE_MOCK_DATA"] = "true"

def test_sms_parser_with_promo_filter():
    """Test the SMS parser with promotional and non-promotional messages"""
    
    test_cases = [
        # Banking SMS examples
        {
            "description": "Credit card transaction",
            "sms": "Your KOTAK Credit Card was used for INR 3,150 on 04-Apr-25 at DECATHLON INDIA.",
            "expected_type": "transaction"
        },
        {
            "description": "Account debit transaction",
            "sms": "Dear Customer, your a/c XX7890 is debited with INR 2,500.00 on 05-Apr-25 at Amazon India. Available balance: INR 45,678.90",
            "expected_type": "transaction"
        },
        {
            "description": "UPI transaction",
            "sms": "INR 1,200 debited from your account XX4567 for UPI transaction to PHONEPAY. Ref YGAF765463. UPI Ref UPIYWF6587434",
            "expected_type": "transaction"
        },
        {
            "description": "EMI payment",
            "sms": "Your EMI of Rs.3,499 for Loan A/c no.XX1234 has been deducted. Total EMIs paid: 6/24. Next EMI due on 05-May-25. Avl Bal: Rs.45,610.22",
            "expected_type": "transaction"
        },
        
        # Promotional SMS examples
        {
            "description": "Clothing brand promotion",
            "sms": "Exciting offers at ARROW! Shop the latest collection & enjoy stylish travel accessories, or up to Rs. 3000 OFF! Head to an exclusive store today. T&C Apply",
            "expected_type": "promotional"
        },
        {
            "description": "End of season sale",
            "sms": "ARROW End of Season Sale is HERE, Buy 2 Get 2 FREE on Formals, Occasion Wear, & Casuals. Hurry, the best styles will not last! Visit an exclusive store now. TC",
            "expected_type": "promotional"
        },
        {
            "description": "Promotion with URL",
            "sms": "This Pujo, sharpen your look with ARROW! Use YF7E54YO for Rs.500 OFF at GVK One Mall, Hyderabad. Enjoy exciting offers - https://bit.ly/4eIu6Sx .TC",
            "expected_type": "promotional"
        },
        
        # Edge cases
        {
            "description": "Bank promotion (promotional from bank)",
            "sms": "HDFC Bank: Upgrade to our Platinum Credit Card and get 5X reward points on all purchases. Call 1800-XXX-XXXX or visit hdfcbank.com/upgrade. T&C apply.",
            "expected_type": "promotional"
        },
        {
            "description": "Transaction confirmation with promotional element",
            "sms": "Thank you for shopping at BigBasket! Your order of Rs.1,500 will be delivered today. Use code BBFIRST for 20% off on your next order!",
            "expected_type": "promotional"
        }
    ]
    
    print("Testing SMS Parser with Promotional Filter\n")
    print("-" * 80)
    
    # Track success/failure counts
    successes = 0
    failures = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['description']}")
        print(f"SMS: {case['sms'][:60]}..." if len(case['sms']) > 60 else f"SMS: {case['sms']}")
        print(f"Expected: {case['expected_type']}")
        
        # Parse the SMS
        result = parse_sms(case["sms"])
        
        # Determine actual type
        actual_type = "promotional" if result.get("is_promotional", False) else "transaction"
        
        print(f"Actual: {actual_type}")
        
        # Check if the classification is correct
        if actual_type == case["expected_type"]:
            print("✅ PASS")
            successes += 1
        else:
            print("❌ FAIL")
            failures += 1
        
        # Print interesting details based on type
        if actual_type == "promotional":
            print(f"Promotional score: {result.get('promo_score', 'N/A')}")
        else:
            # For transaction SMS, show basic transaction details
            transaction = result.get("transaction", {})
            if transaction:
                print(f"Transaction type: {transaction.get('type', 'N/A')}")
                print(f"Amount: {transaction.get('amount', 'N/A')}")
                print(f"Merchant: {transaction.get('merchant', 'N/A')}")
        
        print("-" * 80)
    
    # Print summary
    print(f"\nSummary: {successes} passed, {failures} failed out of {len(test_cases)} test cases")
    print(f"Success rate: {(successes / len(test_cases)) * 100:.1f}%")

if __name__ == "__main__":
    test_sms_parser_with_promo_filter() 