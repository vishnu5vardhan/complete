#!/usr/bin/env python3

"""
Test script for comparing rule-based and Gemini-based promotional SMS detection.
"""

import os
import json
from promotional_sms_detector import is_promotional_sms, check_promotional_sms
import unittest
from enhanced_sms_parser import parse_sms
from langchain_wrapper import detect_promotional_sms_with_gemini

# Set this to True to use Gemini for detection, False to use rule-based
USE_GEMINI = True

# Set environment variables
if not USE_GEMINI:
    os.environ["USE_MOCK_DATA"] = "true"  # This will force the use of rule-based detection
else:
    os.environ["USE_MOCK_DATA"] = "false"  # This will allow using Gemini

class TestPromotionalDetection(unittest.TestCase):
    """Test cases for promotional SMS detection"""

    def setUp(self):
        """Set up test environment"""
        # Set environment variable for testing
        os.environ["USE_MOCK_DATA"] = "true"
        self.promotional_test_cases = [
            # Promotional SMS examples
            "Exciting offers at ARROW! Shop the latest collection & enjoy stylish travel accessories, or up to Rs. 3000 OFF! Head to an exclusive store today. T&C Apply",
            "ARROW End of Season Sale is HERE, Buy 2 Get 2 FREE on Formals, Occasion Wear, & Casuals. Hurry, the best styles will not last! Visit an exclusive store now. TC",
            "This Pujo, sharpen your look with ARROW! Use YF7E54YO for Rs.500 OFF at GVK One Mall, Hyderabad. Enjoy exciting offers - https://bit.ly/4eIu6Sx .TC",
            "MYNTRA SALE: 50-80% OFF! Flat 499 store. GRAB NOW: bit.ly/3AKmnP",
            "Celebrate with Amazon! Use code FESTIVE20 for 20% off your next purchase. Shop now: amzn.to/abc123",
        ]
        
        self.transaction_test_cases = [
            # Banking SMS examples
            "Your KOTAK Credit Card was used for INR 3,150 on 04-Apr-25 at DECATHLON INDIA.",
            "Dear Customer, your a/c XX7890 is debited with INR 2,500.00 on 05-Apr-25 at Amazon India. Available balance: INR 45,678.90",
            "INR 1,200 debited from your account XX4567 for UPI transaction to PHONEPAY. Ref YGAF765463. UPI Ref UPIYWF6587434",
            "Your EMI of Rs.3,499 for Loan A/c no.XX1234 has been deducted. Total EMIs paid: 6/24. Next EMI due on 05-May-25. Avl Bal: Rs.45,610.22",
            "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
        ]
        
        self.edge_cases = [
            # Edge cases - promotional content from banks and mixed messages
            "HDFC Bank: Upgrade to our Platinum Credit Card and get 5X reward points on all purchases. Call 1800-XXX-XXXX or visit hdfcbank.com/upgrade. T&C apply.",
            "Thank you for shopping at BigBasket! Your order of Rs.1,500 will be delivered today. Use code BBFIRST for 20% off on your next order!",
        ]

    def test_rule_based_detection(self):
        """Test rule-based promotional SMS detection"""
        # Test promotional messages - at least some should be detected as promotional
        promotional_count = 0
        for sms in self.promotional_test_cases:
            is_promo, result = is_promotional_sms(sms)
            if is_promo:
                promotional_count += 1
                
        self.assertGreater(promotional_count, 0, "Should detect at least some promotional SMS")
        
        # Test transaction messages - none should be detected as promotional
        for sms in self.transaction_test_cases:
            is_promo, result = is_promotional_sms(sms)
            self.assertFalse(is_promo, f"Incorrectly classified transaction SMS as promotional: {sms}")

    def test_enhanced_detection(self):
        """Test check_promotional_sms function that uses both detection methods"""
        # Test promotional messages
        for sms in self.promotional_test_cases:
            result = check_promotional_sms(sms)
            self.assertTrue(result["is_promotional"], f"Failed to detect promotional SMS: {sms}")
            
        # Test transaction messages
        for sms in self.transaction_test_cases:
            result = check_promotional_sms(sms)
            self.assertFalse(result["is_promotional"], f"Incorrectly classified transaction SMS as promotional: {sms}")

    def test_gemini_detection_mock(self):
        """Test the Gemini-based promotional detection with mock data"""
        # Since we're in mock mode, we'll just check if the function runs without errors
        
        # Test a promotional message
        promo_sms = "MYNTRA SALE: 50-80% OFF! Flat 499 store. GRAB NOW: bit.ly/3AKmnP"
        result = detect_promotional_sms_with_gemini(promo_sms)
        self.assertIn("is_promotional", result, "Response should contain is_promotional field")
        self.assertIn("promo_score", result, "Response should contain promo_score field")
        
        # Test a transaction message
        transaction_sms = "Your HDFC Bank account XX1234 was debited with INR 4,500.00 on 05-04-2023 for an online payment. Available balance: INR 15,789.45"
        result = detect_promotional_sms_with_gemini(transaction_sms)
        self.assertIn("is_promotional", result, "Response should contain is_promotional field")
        self.assertIn("promo_score", result, "Response should contain promo_score field")

    def test_end_to_end_parsing(self):
        """Test the full SMS parsing pipeline with promotional detection"""
        # Test a promotional SMS - should have empty transaction data
        promo_sms = "Exciting offers at ARROW! Shop now and get 50% off on all items. Visit arrow.com/sale"
        result = parse_sms(promo_sms)
        self.assertIn("is_promotional", result, "Result should contain promotional status")
        
        # Test a transaction SMS with specific merchant
        credit_transaction = "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00"
        result = parse_sms(credit_transaction)
        
        # In mock mode, we can only check that the structure is correct
        self.assertIn("transaction", result, "Result should contain transaction data")
        self.assertIn("fraud_detection", result, "Result should contain fraud detection")
        self.assertIn("metadata", result, "Result should contain metadata")

if __name__ == "__main__":
    unittest.main() 