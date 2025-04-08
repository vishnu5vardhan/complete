#!/usr/bin/env python3

from enhanced_sms_parser import light_filter

def demo_light_filter():
    """
    Demonstrate the light filter functionality with a variety of real-world SMS examples
    """
    print("=" * 80)
    print("SMS LIGHT FILTER DEMO")
    print("=" * 80)
    print("This demo shows how the light filter quickly identifies and filters out irrelevant SMS\n")
    
    # Test cases organized by category
    test_cases = [
        # Banking transactions - Should be PROCESSED (not filtered)
        {
            "category": "Banking Transaction",
            "sms": "Your a/c XX1234 is debited with Rs.1500.00 for Swiggy order on 2023-07-15. Available balance: Rs.12,345.67.",
            "expected": "PROCESS"
        },
        {
            "category": "Banking Transaction",
            "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
            "expected": "PROCESS"
        },
        {
            "category": "Banking Transaction",
            "sms": "Your account XX5678 has been credited with Rs.10,000 on 15-Jul-2023. Available balance: Rs.22,345.67.",
            "expected": "PROCESS"
        },
        {
            "category": "UPI Transaction",
            "sms": "UPI: Rs.500.00 debited from A/c XX1234 on 15-Jul-23 to xyz@upi Ref 123456789.",
            "expected": "PROCESS"
        },
        
        # OTP/Authentication - Should be FILTERED
        {
            "category": "Authentication",
            "sms": "Your OTP for login is 123456. Valid for 10 minutes.",
            "expected": "FILTER"
        },
        {
            "category": "Authentication",
            "sms": "2FA code for your account: 112233",
            "expected": "FILTER"
        },
        {
            "category": "Authentication",
            "sms": "Your verification code is 987654. Do not share this with anyone.",
            "expected": "FILTER"
        },
        
        # Delivery notifications - Should be FILTERED
        {
            "category": "Delivery",
            "sms": "Your order #12345 has been delivered. Rate your experience now!",
            "expected": "FILTER"
        },
        {
            "category": "Delivery",
            "sms": "Your package from Amazon is out for delivery and will arrive today.",
            "expected": "FILTER"
        },
        
        # Recharge/Service - Should be FILTERED
        {
            "category": "Recharge",
            "sms": "Your recharge of Rs.199 was successful. Validity: 28 days.",
            "expected": "FILTER"
        },
        {
            "category": "Recharge",
            "sms": "Your plan has been activated. Data: 1.5GB/day, Unlimited calls.",
            "expected": "FILTER"
        },
        
        # Fraud/Phishing - Should be PROCESSED (for fraud detection)
        {
            "category": "Fraud",
            "sms": "URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc",
            "expected": "PROCESS"
        },
        {
            "category": "Fraud",
            "sms": "Your HDFC Bank account has been suspended. Please click http://hdfc-verify.co to verify your identity and restore access.",
            "expected": "PROCESS"
        },
        
        # Mixed content - Authentication with transaction info - Should be PROCESSED
        {
            "category": "Mixed Content",
            "sms": "Your OTP for transaction of Rs.5000 to Flipkart is 123456. Valid for 5 minutes.",
            "expected": "PROCESS"
        },
        {
            "category": "Mixed Content", 
            "sms": "Your order #12345 has been delivered. Your card XX5678 has been charged Rs.1,299.",
            "expected": "PROCESS"
        }
    ]
    
    # Process each test case
    for i, case in enumerate(test_cases, 1):
        result = light_filter(case["sms"])
        actual = "PROCESS" if result else "FILTER"
        is_correct = actual == case["expected"]
        
        print(f"{i}. [{case['category']}] - {'✅' if is_correct else '❌'}")
        print(f"   SMS: {case['sms'][:80]}..." if len(case['sms']) > 80 else f"   SMS: {case['sms']}")
        print(f"   Expected: {case['expected']}, Actual: {actual}")
        print()
    
    # Print summary
    processed = sum(1 for case in test_cases if light_filter(case["sms"]))
    filtered = len(test_cases) - processed
    
    print("-" * 80)
    print(f"Summary: {processed} SMS processed, {filtered} SMS filtered out of {len(test_cases)} total")
    print(f"Processing rate: {processed/len(test_cases)*100:.1f}%")
    print("-" * 80)
    
    # Print information about the performance benefit
    print("\nPerformance Benefit Analysis:")
    print(f"By filtering out {filtered} irrelevant SMS early in the pipeline, we save:")
    print(f"- {filtered} expensive Gemini API calls")
    print(f"- Approximately {filtered * 200}ms of processing time (assuming 200ms per Gemini call)")
    print(f"- Less noise in the transaction database")
    print("=" * 80)

if __name__ == "__main__":
    demo_light_filter() 