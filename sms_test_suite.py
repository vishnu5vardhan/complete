#!/usr/bin/env python3

import json
import os
import sys
import unittest
from enhanced_sms_parser import parse_sms
from typing import Dict, List, Any

class SMSTestSuite:
    """Test suite for SMS parsing with different categories of messages"""
    
    def __init__(self):
        self.test_cases = {
            "legitimate_transactions": [
                {
                    "description": "Credit Card Transaction",
                    "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
                    "sender": "HDFCBK",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 689.0,
                        "merchant": "McDonald's",
                        "category": "Food",
                        "is_promotional": False,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Debit Card Transaction",
                    "sms": "Your a/c XX1234 is debited with Rs.1500.00 for Swiggy order on 2023-07-15. Available balance: Rs.12,345.67.",
                    "sender": "SBIINB",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 1500.0,
                        "merchant": "Swiggy",
                        "category": "Food",
                        "is_promotional": False,
                        "is_fraud": False
                    }
                },
                {
                    "description": "UPI Transaction",
                    "sms": "UPI/P2P/VPA-john@upi/Rs.500.00/XX1234/Success/07-15-23/12:30:45/Ref.987654321",
                    "sender": "ICICIB",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 500.0,
                        "merchant": "",
                        "is_promotional": False,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Credit Transaction",
                    "sms": "Your account XX5678 has been credited with INR 25,000.00 via NEFT. Available balance: INR 35,467.89",
                    "sender": "HDFCBK",
                    "expected": {
                        "transaction_type": "credit",
                        "amount": 25000.0,
                        "merchant": "",
                        "is_promotional": False,
                        "is_fraud": False
                    }
                },
                {
                    "description": "EMI Deduction",
                    "sms": "EMI of Rs.3,456.78 has been deducted from your account XX9876 for loan no. 123456. Bal: Rs.12,500.00",
                    "sender": "AXISBK",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 3456.78,
                        "merchant": "",
                        "category": "EMI/Loan",
                        "is_promotional": False,
                        "is_fraud": False
                    }
                }
            ],
            "promotional_sms": [
                {
                    "description": "Retail Promotion",
                    "sms": "ARROW End of Season Sale is HERE, Buy 2 Get 2 FREE on Formals, Occasion Wear, & Casuals. Hurry, the best styles will not last! Visit an exclusive store now.",
                    "sender": "VK-ARROW",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Bank Card Offer",
                    "sms": "HDFC Bank: Upgrade to our premium credit card and enjoy 5x rewards, lounge access, and more! Apply now at hdfc.in/upgrade",
                    "sender": "HDFCBK",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Food Delivery Discount",
                    "sms": "Weekend special! Use code WEEKEND50 to get 50% OFF (up to Rs.150) on your next 2 Swiggy orders. Valid till Sunday midnight. Order now!",
                    "sender": "SWIGGY",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                },
                {
                    "description": "E-commerce Sale",
                    "sms": "Amazon Great Indian Sale starts tomorrow! Up to 80% off on electronics, fashion, home & more. Prime members get early access today. Shop now: amzn.in/sale",
                    "sender": "AMAZON",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Service Provider Offer",
                    "sms": "Dear Customer, recharge with Rs.249 plan and get unlimited calls, 1.5GB/day data for 28 days + FREE Amazon Prime subscription for 1 month. Recharge now!",
                    "sender": "AIRTEL",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                }
            ],
            "fraudulent_sms": [
                {
                    "description": "KYC Scam",
                    "sms": "URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc",
                    "sender": "TX-KYCSMS",
                    "expected": {
                        "is_promotional": False,
                        "is_fraud": True,
                        "fraud_indicators": ["urgent_action", "account_will_be", "url"]
                    }
                },
                {
                    "description": "Fake Credit Scam",
                    "sms": "Congratulations! Rs.50,000 has been credited to your account. Claim now: tiny.cc/claim-now",
                    "sender": "CASHBNK",
                    "expected": {
                        "is_promotional": False,
                        "is_fraud": True,
                        "fraud_indicators": ["prize_scam", "url"]
                    }
                },
                {
                    "description": "Prize Scam",
                    "sms": "Dear Customer, your mobile number has won Rs.5,00,000 in our lucky draw. Contact 98765-43210 to claim your prize.",
                    "sender": "TX-LUCKY",
                    "expected": {
                        "is_promotional": False,
                        "is_fraud": True,
                        "fraud_indicators": ["prize_scam"]
                    }
                },
                {
                    "description": "Account Block Scam",
                    "sms": "Your bank account will be blocked within 24 hours. Call our customer care immediately at 1800-123-4567 to prevent blocking.",
                    "sender": "BNKALRT",
                    "expected": {
                        "is_promotional": False,
                        "is_fraud": True,
                        "fraud_indicators": ["urgent_action", "account_will_be"]
                    }
                },
                {
                    "description": "Phishing Link",
                    "sms": "Your SBI account needs verification. Update your account details here: sbi-online.co/verify",
                    "sender": "SBI-IND",
                    "expected": {
                        "is_promotional": False,
                        "is_fraud": True,
                        "fraud_indicators": ["url"]
                    }
                }
            ],
            "edge_cases": [
                {
                    "description": "Very Short SMS",
                    "sms": "Txn: Rs.500 at Shop",
                    "sender": "ICICI",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 500.0,
                        "is_promotional": False
                    }
                },
                {
                    "description": "Missing Amount",
                    "sms": "Your purchase at Amazon was successful. Ref: 1234567890",
                    "sender": "SBIINB",
                    "expected": {
                        "transaction_type": "debit",
                        "merchant": "Amazon",
                        "is_promotional": False
                    }
                },
                {
                    "description": "Typos in SMS",
                    "sms": "Your acnt XX1234 is debtied with Rs.1000 for Amozon. Bal: Rs.5000",
                    "sender": "YESBNK",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 1000.0,
                        "merchant": "Amazon",
                        "is_promotional": False
                    }
                },
                {
                    "description": "Unusual Formatting",
                    "sms": "INR=1200.00*DB*AC=XX5678*DT=15/07/23*INFO=UBER INDIA*AVLBAL=INR 3400.00*",
                    "sender": "HDFC",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 1200.0,
                        "merchant": "Uber",
                        "is_promotional": False
                    }
                },
                {
                    "description": "Non-Standard Transaction",
                    "sms": "Pmt processed: 2500 to XX7890 on 15Jun via IMPS. Ref: 123ABC456",
                    "sender": "KOTAK",
                    "expected": {
                        "transaction_type": "debit",
                        "amount": 2500.0,
                        "is_promotional": False
                    }
                }
            ],
            "card_offers": [
                {
                    "description": "Credit Card Reward Points",
                    "sms": "Congratulations! You've earned 1000 reward points on your HDFC Credit Card XX1234. Redeem now on rewards portal.",
                    "sender": "HDFCBK",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Card Cashback",
                    "sms": "You've received Rs.200 cashback on your ICICI Bank Credit Card XX5678 for your recent Amazon transaction.",
                    "sender": "ICICIB",
                    "expected": {
                        "transaction_type": "credit",
                        "amount": 200.0,
                        "merchant": "Amazon",
                        "is_promotional": False
                    }
                },
                {
                    "description": "Card EMI Conversion Offer",
                    "sms": "Convert your recent purchase of Rs.15,000 to 6-month EMI at 0% interest. Reply YES to convert. T&C apply.",
                    "sender": "AXISBK",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Pre-approved Loan",
                    "sms": "Dear Customer, you have a pre-approved personal loan of Rs.5,00,000 at 10.99% p.a. Call 1800-123-4567 to avail.",
                    "sender": "SBIINB",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                },
                {
                    "description": "Credit Limit Increase",
                    "sms": "Good news! Your HDFC Bank Credit Card XX9876 limit has been increased to Rs.2,00,000. Enjoy enhanced spending power!",
                    "sender": "HDFCBK",
                    "expected": {
                        "is_promotional": True,
                        "is_fraud": False
                    }
                }
            ]
        }
    
    def get_all_test_cases(self) -> List[Dict]:
        """Return all test cases as a flat list"""
        all_cases = []
        for category, cases in self.test_cases.items():
            for case in cases:
                case["category"] = category
                all_cases.append(case)
        return all_cases
    
    def get_test_cases_by_category(self, category: str) -> List[Dict]:
        """Return test cases for a specific category"""
        return self.test_cases.get(category, [])
    
    def run_tests(self, verbose=False):
        """Run all tests and print results"""
        results = {
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        print(f"Running SMS Parser Test Suite ({len(self.get_all_test_cases())} test cases)")
        print("=" * 80)
        
        for category, cases in self.test_cases.items():
            print(f"\nCategory: {category} ({len(cases)} tests)")
            print("-" * 80)
            
            for i, case in enumerate(cases, 1):
                if verbose:
                    print(f"\nTest {i}: {case['description']}")
                    print(f"SMS: {case['sms']}")
                else:
                    print(f"Test {i}: {case['description']}...", end="")
                
                # Parse the SMS
                parsed_result = parse_sms(case['sms'], case.get('sender'))
                
                # Check if the expected values match the parsed results
                test_passed = True
                failures = []
                
                for key, expected_value in case['expected'].items():
                    # Handle special case for fraud indicators
                    if key == 'fraud_indicators':
                        fraud_detection = parsed_result.get('fraud_detection', {})
                        indicators = fraud_detection.get('suspicious_indicators', [])
                        # Check if at least one expected indicator is present
                        indicator_found = False
                        for expected_indicator in expected_value:
                            if any(expected_indicator in indicator for indicator in indicators):
                                indicator_found = True
                                break
                        
                        if not indicator_found:
                            test_passed = False
                            failures.append(f"Expected fraud indicator containing '{expected_value}' not found in {indicators}")
                    # Handle normal field checks
                    elif key == 'amount':
                        transaction = parsed_result.get('transaction', {})
                        actual_value = transaction.get('transaction_amount', transaction.get('amount', 0))
                        if abs(actual_value - expected_value) > 0.01:  # Allow small float differences
                            test_passed = False
                            failures.append(f"Expected {key}={expected_value}, got {actual_value}")
                    elif key == 'transaction_type' or key == 'merchant' or key == 'category':
                        transaction = parsed_result.get('transaction', {})
                        actual_value = transaction.get(key, "")
                        if key == 'merchant' and not actual_value:
                            actual_value = transaction.get('merchant_name', "")
                            
                        if expected_value and expected_value.lower() not in actual_value.lower():
                            test_passed = False
                            failures.append(f"Expected {key}={expected_value}, got {actual_value}")
                    elif key == 'is_promotional':
                        actual_value = parsed_result.get('is_promotional', False)
                        if actual_value != expected_value:
                            test_passed = False
                            failures.append(f"Expected is_promotional={expected_value}, got {actual_value}")
                    elif key == 'is_fraud':
                        fraud_detection = parsed_result.get('fraud_detection', {})
                        is_suspicious = fraud_detection.get('is_suspicious', False)
                        risk_level = fraud_detection.get('risk_level', 'none')
                        actual_value = is_suspicious and risk_level != 'none'
                        if actual_value != expected_value:
                            test_passed = False
                            failures.append(f"Expected is_fraud={expected_value}, got {actual_value}")
                
                # Record the result
                if test_passed:
                    results["passed"] += 1
                    if verbose:
                        print("✅ PASSED")
                    else:
                        print(" ✅ PASSED")
                else:
                    results["failed"] += 1
                    if verbose:
                        print("❌ FAILED")
                        for failure in failures:
                            print(f"  - {failure}")
                    else:
                        print(" ❌ FAILED")
                
                results["details"].append({
                    "category": category,
                    "description": case['description'],
                    "passed": test_passed,
                    "failures": failures
                })
        
        # Print summary
        print("\n" + "=" * 80)
        print(f"Summary: {results['passed']} passed, {results['failed']} failed")
        print(f"Pass rate: {results['passed']/len(self.get_all_test_cases())*100:.1f}%")
        
        return results

    def export_to_json(self, filename="sms_test_suite.json"):
        """Export test cases to a JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.test_cases, f, indent=2)
        print(f"Test suite exported to {filename}")
    
    @classmethod
    def load_from_json(cls, filename="sms_test_suite.json"):
        """Load test cases from a JSON file"""
        test_suite = cls()
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                test_suite.test_cases = json.load(f)
        return test_suite

def main():
    """Run the test suite"""
    # Create the test suite
    test_suite = SMSTestSuite()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run SMS Parser test suite')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-e', '--export', action='store_true', help='Export test cases to JSON')
    parser.add_argument('-c', '--category', help='Run tests only for a specific category')
    args = parser.parse_args()
    
    # Export test cases if requested
    if args.export:
        test_suite.export_to_json()
        return
    
    # Run tests
    if args.category:
        if args.category not in test_suite.test_cases:
            print(f"Error: Category '{args.category}' not found")
            print(f"Available categories: {', '.join(test_suite.test_cases.keys())}")
            return
        
        # Create a new test suite with only the selected category
        filtered_suite = SMSTestSuite()
        filtered_suite.test_cases = {args.category: test_suite.test_cases[args.category]}
        test_suite = filtered_suite
    
    # Run the tests
    test_suite.run_tests(verbose=args.verbose)

if __name__ == "__main__":
    main() 