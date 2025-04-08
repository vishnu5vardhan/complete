#!/usr/bin/env python3

import unittest
import sys
import os
import json
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the necessary modules
from sms_parser.cli.main import process_sms
from sms_parser.core.database import init_database
from sms_parser.core.config import ENABLE_MOCK_MODE

class TestSMSParserEndToEnd(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Initialize the database
        init_database()
        
        # Load environment variables
        load_dotenv()
        
        # Print whether we're in mock mode
        print(f"Mock mode is {'enabled' if ENABLE_MOCK_MODE else 'disabled'}")
        
    def test_banking_transaction_sms(self):
        """Test parsing a standard banking transaction SMS"""
        sms = "Your account XX1234 has been debited with Rs.1500.00 on 05-04-2023 for a purchase at Swiggy. Available balance is Rs.12,345.67."
        sender = "HDFCBK"
        
        result = process_sms(sms, sender)
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["is_banking_sms"])
        self.assertFalse(result["is_promotional"])
        self.assertFalse(result["is_fraud"])
        
        # Check parsed data
        parsed_data = result.get("parsed_data", {})
        self.assertIn("transaction_type", parsed_data)
        self.assertIn("amount", parsed_data)
        
        # Print the result for debugging
        print("\nBanking Transaction Test:")
        print(f"Status: {result['status']}")
        print(f"Method: {result.get('parsing_method', 'unknown')}")
        print(f"Amount: {parsed_data.get('amount', 'unknown')}")
        print(f"Transaction Type: {parsed_data.get('transaction_type', 'unknown')}")
        
    def test_promotional_sms(self):
        """Test parsing a promotional SMS"""
        sms = "SPECIAL OFFER! Get 50% off on your next order at Swiggy. Use code SAVE50. Offer valid till 31-05-2023. Shop now at www.swiggy.com"
        sender = "SWIGGY"
        
        result = process_sms(sms, sender)
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["is_banking_sms"])
        self.assertTrue(result["is_promotional"])
        self.assertFalse(result["is_fraud"])
        
        # Print the result for debugging
        print("\nPromotional SMS Test:")
        print(f"Status: {result['status']}")
        print(f"Method: {result.get('parsing_method', 'unknown')}")
        print(f"Is Promotional: {result['is_promotional']}")
        
    def test_fraud_sms(self):
        """Test parsing a potentially fraudulent SMS"""
        sms = "ALERT: Your account is blocked. Urgent action required. Call +91-1234567890 immediately or click on http://suspicious-link.com to verify."
        sender = "Unknown"
        
        result = process_sms(sms, sender)
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["is_fraud"])
        
        # Print the result for debugging
        print("\nFraud SMS Test:")
        print(f"Status: {result['status']}")
        print(f"Method: {result.get('parsing_method', 'unknown')}")
        print(f"Risk Level: {result.get('fraud_detection', {}).get('risk_level', 'unknown')}")
        
    def test_non_financial_sms(self):
        """Test filtering out non-financial SMS"""
        sms = "Your OTP for login is 123456. Valid for 10 minutes."
        sender = "AMAZON"
        
        result = process_sms(sms, sender)
        
        # Verify the result
        self.assertEqual(result["status"], "filtered_out")
        self.assertFalse(result["is_banking_sms"])
        
        # Print the result for debugging
        print("\nNon-Financial SMS Test:")
        print(f"Status: {result['status']}")
        print(f"Is Processed: {result['is_processed']}")

if __name__ == "__main__":
    unittest.main() 