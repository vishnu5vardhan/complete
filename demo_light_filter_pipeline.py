#!/usr/bin/env python3

import time
import json
from enhanced_sms_parser import parse_sms, light_filter

def demo_full_pipeline():
    """
    Demonstrate the full SMS parsing pipeline with light filter as the first stage
    """
    print("=" * 80)
    print("FULL SMS PARSING PIPELINE DEMO")
    print("=" * 80)
    print("This demo shows the complete SMS parsing pipeline with light filtering\n")
    
    # Sample SMS messages to process
    test_cases = [
        # Financial transactions (should pass through the filter)
        {
            "category": "Banking Transaction",
            "sender": "HDFCBK",
            "sms": "Your a/c XX1234 is debited with Rs.1500.00 for Swiggy order on 2023-07-15. Available balance: Rs.12,345.67."
        },
        {
            "category": "Credit Card Transaction",
            "sender": "HDFCBK",
            "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00"
        },
        {
            "category": "Fraud Attempt",
            "sender": "TX-KYCSMS",
            "sms": "URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc"
        },
        
        # Non-financial messages (should be filtered out)
        {
            "category": "OTP Message",
            "sender": "VM-OTPSMS",
            "sms": "Your OTP for login is 123456. Valid for 10 minutes."
        },
        {
            "category": "Delivery Notification",
            "sender": "TM-AMAZON",
            "sms": "Your Amazon order #AB12345 has been delivered. Rate your experience."
        },
        {
            "category": "Recharge Confirmation",
            "sender": "JI-AIRTEL",
            "sms": "Your recharge of Rs.199 was successful. Validity: 28 days."
        }
    ]
    
    # Process each SMS and measure performance
    total_time_without_filter = 0
    total_time_with_filter = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. [{case['category']}]")
        print(f"   Sender: {case['sender']}")
        print(f"   SMS: {case['sms'][:100]}..." if len(case['sms']) > 100 else f"   SMS: {case['sms']}")
        
        # First check with light filter
        start_time = time.time()
        should_process = light_filter(case["sms"])
        filter_time = time.time() - start_time
        
        print(f"   Light Filter: {'PASS' if should_process else 'FILTERED'} ({filter_time*1000:.2f}ms)")
        
        # Full parsing if it passes the filter
        if should_process:
            # Measure time for full parsing
            start_time = time.time()
            result = parse_sms(case["sms"], case["sender"])
            full_parse_time = time.time() - start_time
            
            # Calculate the total time with filter in place
            total_time_with_filter += (filter_time + full_parse_time)
            
            # Estimate time without filter (would always do full parsing)
            total_time_without_filter += full_parse_time
            
            # Print result summary
            print(f"   Full Parse: COMPLETED ({full_parse_time*1000:.2f}ms)")
            
            # Print transaction details if available
            if "transaction" in result and not result.get("is_promotional", False):
                txn = result["transaction"]
                print(f"   → Amount: {'₹' + str(txn.get('amount', 0))} | Type: {txn.get('transaction_type', 'Unknown')}")
                print(f"   → Merchant: {txn.get('merchant', 'Unknown')} | Category: {txn.get('category', 'Unknown')}")
                
                # Check for fraud
                if result.get("fraud_detection", {}).get("is_suspicious", False):
                    risk = result["fraud_detection"]["risk_level"]
                    print(f"   → ⚠️ FRAUD ALERT! Risk Level: {risk.upper()}")
                    indicators = result["fraud_detection"].get("suspicious_indicators", [])
                    if indicators:
                        print(f"   → Indicators: {', '.join(indicators[:3])}" + ("..." if len(indicators) > 3 else ""))
            
            elif result.get("is_promotional", False):
                print(f"   → Promotional SMS (Score: {result.get('promo_score', 0):.2f})")
            
            # Raw result for debugging
            # print(f"   Raw Result: {json.dumps(result, indent=2)}")
        else:
            # If filtered, we only count the filter time
            total_time_with_filter += filter_time
            
            # Without the filter, we would have done full parsing (estimate this as average of other parses)
            # We'll update this estimate at the end
            
            print(f"   → Skipped full parsing (irrelevant SMS)")
    
    # Estimate the time saved
    # For filtered messages, estimate full parse time based on average of processed messages
    avg_parse_time = total_time_without_filter / sum(1 for case in test_cases if light_filter(case["sms"]))
    for case in test_cases:
        if not light_filter(case["sms"]):
            total_time_without_filter += avg_parse_time
    
    time_saved = total_time_without_filter - total_time_with_filter
    efficiency_gain = (time_saved / total_time_without_filter) * 100
    
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print(f"Total SMS processed: {len(test_cases)}")
    print(f"SMS parsed fully: {sum(1 for case in test_cases if light_filter(case['sms']))}")
    print(f"SMS filtered out: {sum(1 for case in test_cases if not light_filter(case['sms']))}")
    print("\nEstimated processing time:")
    print(f"Without filter: {total_time_without_filter*1000:.2f}ms")
    print(f"With filter:    {total_time_with_filter*1000:.2f}ms")
    print(f"Time saved:     {time_saved*1000:.2f}ms ({efficiency_gain:.1f}% efficiency gain)")
    
    print("\nConclusion:")
    print("The light filter provides significant performance improvements by quickly rejecting")
    print("irrelevant SMS messages before they reach the expensive parsing and LLM stages.")
    print("This translates to faster response times and reduced API costs in production.")
    print("=" * 80)

if __name__ == "__main__":
    demo_full_pipeline() 