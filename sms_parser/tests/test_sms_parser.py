#!/usr/bin/env python3

"""
Test script for SMS parser
This script tests the parser with various SMS examples
"""

import unittest
import json
from enhanced_sms_parser import parse_sms
from test_sms_examples import (
    BANKING_EXAMPLES,
    PROMOTIONAL_EXAMPLES,
    FRAUD_EXAMPLES,
    WALLET_CREDIT_OFFERS,
    OTP_EXAMPLES,
    EDGE_CASES
)

class TestSMSParser(unittest.TestCase):
    """Test the SMS parser with various example messages"""
    
    def test_banking_transactions(self):
        """Test the parser's ability to handle banking transactions"""
        print("\n=== Testing Banking Transactions ===")
        for i, example in enumerate(BANKING_EXAMPLES):
            sms = example["sms"]
            sender = example["sender"]
            expected = example["expected"]
            
            result = parse_sms(sms, sender)
            
            # Extract transaction details for comparison
            transaction = result.get("transaction", {})
            
            # Print test details
            print(f"\nTest {i+1}: {sender}\nSMS: {sms[:50]}...")
            
            # Verify transaction type
            if "transaction_type" in expected:
                self.assertEqual(
                    transaction.get("transaction_type"), 
                    expected["transaction_type"],
                    f"Transaction type mismatch in test {i+1}"
                )
                print(f"✓ Transaction type: {transaction.get('transaction_type')}")
            
            # Verify amount
            if "amount" in expected:
                self.assertIsNotNone(transaction.get("amount"), f"Amount not found in test {i+1}")
                self.assertAlmostEqual(
                    float(transaction.get("amount", 0)),
                    float(expected["amount"]),
                    places=1,
                    msg=f"Amount mismatch in test {i+1}"
                )
                print(f"✓ Amount: {transaction.get('amount')}")
            
            # Verify merchant
            if "merchant" in expected:
                self.assertEqual(
                    transaction.get("merchant_name"), 
                    expected["merchant"],
                    f"Merchant mismatch in test {i+1}"
                )
                print(f"✓ Merchant: {transaction.get('merchant_name')}")
            
            # Verify category
            if "category" in expected:
                self.assertEqual(
                    transaction.get("category"), 
                    expected["category"],
                    f"Category mismatch in test {i+1}"
                )
                print(f"✓ Category: {transaction.get('category')}")
            
            # Verify account number
            if "account_number" in expected:
                self.assertEqual(
                    transaction.get("account_masked"), 
                    expected["account_number"],
                    f"Account number mismatch in test {i+1}"
                )
                print(f"✓ Account number: {transaction.get('account_masked')}")
            
            # Verify available balance
            if "available_balance" in expected:
                self.assertIsNotNone(transaction.get("available_balance"), f"Available balance not found in test {i+1}")
                self.assertAlmostEqual(
                    float(transaction.get("available_balance", 0)),
                    float(expected["available_balance"]),
                    places=1,
                    msg=f"Available balance mismatch in test {i+1}"
                )
                print(f"✓ Available balance: {transaction.get('available_balance')}")

    def test_promotional_sms(self):
        """Test the parser's ability to identify promotional SMS"""
        print("\n=== Testing Promotional SMS ===")
        for i, example in enumerate(PROMOTIONAL_EXAMPLES):
            sms = example["sms"]
            sender = example["sender"]
            expected = example["expected"]
            
            result = parse_sms(sms, sender)
            
            # Print test details
            print(f"\nTest {i+1}: {sender}\nSMS: {sms[:50]}...")
            
            # Verify promotional status
            is_promotional = result.get("is_promotional", False)
            self.assertEqual(
                is_promotional, 
                expected["is_promotional"],
                f"Promotional status mismatch in test {i+1}"
            )
            print(f"✓ Is promotional: {is_promotional}")

    def test_fraud_sms(self):
        """Test the parser's ability to identify fraudulent SMS"""
        print("\n=== Testing Fraudulent SMS ===")
        for i, example in enumerate(FRAUD_EXAMPLES):
            sms = example["sms"]
            sender = example["sender"]
            expected = example["expected"]
            
            result = parse_sms(sms, sender)
            
            # Extract fraud details for comparison
            fraud = result.get("fraud_detection", {})
            
            # Print test details
            print(f"\nTest {i+1}: {sender}\nSMS: {sms[:50]}...")
            
            # Verify suspicious status
            if "is_suspicious" in expected:
                self.assertEqual(
                    fraud.get("is_suspicious", False), 
                    expected["is_suspicious"],
                    f"Suspicious status mismatch in test {i+1}"
                )
                print(f"✓ Is suspicious: {fraud.get('is_suspicious', False)}")
            
            # Verify risk level
            if "risk_level" in expected:
                self.assertEqual(
                    fraud.get("risk_level"), 
                    expected["risk_level"],
                    f"Risk level mismatch in test {i+1}"
                )
                print(f"✓ Risk level: {fraud.get('risk_level')}")
            
            # Print detected indicators
            indicators = fraud.get("indicators", [])
            if indicators:
                print(f"✓ Fraud indicators: {', '.join(indicators)}")

    def test_wallet_credit_offers(self):
        """Test the parser's ability to handle wallet and credit card offers"""
        print("\n=== Testing Wallet and Credit Card Offers ===")
        for i, example in enumerate(WALLET_CREDIT_OFFERS):
            sms = example["sms"]
            sender = example["sender"]
            expected = example["expected"]
            
            result = parse_sms(sms, sender)
            
            # Print test details
            print(f"\nTest {i+1}: {sender}\nSMS: {sms[:50]}...")
            
            # Verify promotional status
            is_promotional = result.get("is_promotional", False)
            self.assertEqual(
                is_promotional, 
                expected["is_promotional"],
                f"Promotional status mismatch in test {i+1}"
            )
            print(f"✓ Is promotional: {is_promotional}")

    def test_otp_messages(self):
        """Test the parser's ability to handle OTP and verification messages"""
        print("\n=== Testing OTP Messages ===")
        for i, example in enumerate(OTP_EXAMPLES):
            sms = example["sms"]
            sender = example["sender"]
            expected = example["expected"]
            
            result = parse_sms(sms, sender)
            
            # Extract fraud details for comparison
            fraud = result.get("fraud_detection", {})
            
            # Print test details
            print(f"\nTest {i+1}: {sender}\nSMS: {sms[:50]}...")
            
            # Verify promotional status
            is_promotional = result.get("is_promotional", False)
            self.assertEqual(
                is_promotional, 
                expected["is_promotional"],
                f"Promotional status mismatch in test {i+1}"
            )
            print(f"✓ Is promotional: {is_promotional}")
            
            # Verify suspicious status
            if "is_suspicious" in expected:
                self.assertEqual(
                    fraud.get("is_suspicious", False), 
                    expected["is_suspicious"],
                    f"Suspicious status mismatch in test {i+1}"
                )
                print(f"✓ Is suspicious: {fraud.get('is_suspicious', False)}")

    def test_edge_cases(self):
        """Test the parser's ability to handle edge cases"""
        print("\n=== Testing Edge Cases ===")
        for i, example in enumerate(EDGE_CASES):
            sms = example["sms"]
            sender = example["sender"]
            expected = example["expected"]
            
            result = parse_sms(sms, sender)
            
            # Extract transaction details for comparison
            transaction = result.get("transaction", {})
            
            # Print test details
            print(f"\nTest {i+1}: {sender}\nSMS: {sms[:50]}...")
            
            # Verify promotional status if expected
            if "is_promotional" in expected:
                is_promotional = result.get("is_promotional", False)
                self.assertEqual(
                    is_promotional, 
                    expected["is_promotional"],
                    f"Promotional status mismatch in test {i+1}"
                )
                print(f"✓ Is promotional: {is_promotional}")
            
            # Verify transaction type if expected
            if "transaction_type" in expected:
                self.assertEqual(
                    transaction.get("transaction_type"), 
                    expected["transaction_type"],
                    f"Transaction type mismatch in test {i+1}"
                )
                print(f"✓ Transaction type: {transaction.get('transaction_type')}")
            
            # Verify amount if expected
            if "amount" in expected:
                self.assertIsNotNone(transaction.get("amount"), f"Amount not found in test {i+1}")
                self.assertAlmostEqual(
                    float(transaction.get("amount", 0)),
                    float(expected["amount"]),
                    places=1,
                    msg=f"Amount mismatch in test {i+1}"
                )
                print(f"✓ Amount: {transaction.get('amount')}")
            
            # Verify merchant if expected
            if "merchant" in expected:
                self.assertEqual(
                    transaction.get("merchant_name"), 
                    expected["merchant"],
                    f"Merchant mismatch in test {i+1}"
                )
                print(f"✓ Merchant: {transaction.get('merchant_name')}")
            
            # Verify category if expected
            if "category" in expected:
                self.assertEqual(
                    transaction.get("category"), 
                    expected["category"],
                    f"Category mismatch in test {i+1}"
                )
                print(f"✓ Category: {transaction.get('category')}")

def run_test_suite():
    """Run the full test suite"""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

def run_single_test(sms, sender=None):
    """Run a single test with the given SMS and sender"""
    print(f"\n=== Testing Single SMS ===")
    print(f"SMS: {sms}")
    print(f"Sender: {sender}")
    
    result = parse_sms(sms, sender)
    
    # Pretty print the result
    print("\nResult:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    # Run the full test suite
    run_test_suite()
    
    # Example of running a single test
    # sample_sms = "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00"
    # run_single_test(sample_sms, "HDFCBK") 