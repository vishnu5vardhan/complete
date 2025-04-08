#!/usr/bin/env python3

import unittest
from enhanced_sms_parser import light_filter, parse_sms

class TestLightFilter(unittest.TestCase):
    """Test cases for the light filter functionality"""
    
    def test_basic_filtering(self):
        """Test basic filtering of non-financial SMS"""
        
        # Non-financial SMS messages (should be filtered out)
        non_financial_sms = [
            # OTP/Authentication messages
            "Your OTP for login is 123456. Valid for 10 minutes.",
            "Your verification code is 987654. Do not share this with anyone.",
            "2FA code for your account: 112233",
            
            # Delivery messages
            "Your order #12345 has been delivered. Rate your experience now!",
            "Your package from Amazon is out for delivery and will arrive today.",
            "Your food order has been dispatched and will arrive in 30 minutes.",
            
            # Marketing messages (non-transaction)
            "Download our app for exclusive deals and offers!",
            "Follow us on Instagram for the latest updates.",
            "Subscribe to our newsletter for weekly discount codes.",
            
            # Service messages
            "Your recharge of Rs.199 was successful. Validity: 28 days.",
            "Your plan has been activated. Data: 1.5GB/day, Unlimited calls.",
            "You have used 80% of your data. Recharge now to avoid interruption."
        ]
        
        # Check that all non-financial SMS are filtered out
        for sms in non_financial_sms:
            self.assertFalse(light_filter(sms), f"Failed to filter: {sms}")
        
        # Financial SMS messages (should not be filtered)
        financial_sms = [
            # Debit transactions
            "Your a/c XX1234 is debited with Rs.1500.00 for Swiggy order on 2023-07-15. Available balance: Rs.12,345.67.",
            "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
            "Dear Customer, your a/c XX7890 is debited with INR 2,500.00 on 05-Apr-25 at Amazon India. Available balance: INR 45,678.90",
            
            # Credit transactions
            "Your account XX5678 has been credited with Rs.10,000 on 15-Jul-2023. Available balance: Rs.22,345.67.",
            "Salary credit: INR 50,000.00 has been credited to your account XX9876 on 01-Apr-2023.",
            
            # UPI transactions
            "UPI: Rs.500.00 debited from A/c XX1234 on 15-Jul-23 to xyz@upi Ref 123456789.",
            "UPI: Payment of Rs.800.00 sent to merchant@okaxis. UPI Ref: 987654321. Balance: Rs.1,234.56",
            
            # Fraud attempts (should still be processed for fraud detection)
            "URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc",
            "Dear customer, you account is temporary suspended!!! Please to verify your details to avoiding permanent block. Click: bit.ly/verify"
        ]
        
        # Check that all financial SMS are not filtered out
        for sms in financial_sms:
            self.assertTrue(light_filter(sms), f"Incorrectly filtered: {sms}")
    
    def test_mixed_content(self):
        """Test SMS with mixed content (both financial and non-financial indicators)"""
        
        mixed_content_sms = [
            # Contains OTP but also transaction info
            "Your OTP for transaction of Rs.5000 to Flipkart is 123456. Valid for 5 minutes.",
            "Your verification code is 987654 for payment of Rs.3,500 to Amazon.",
            
            # Contains delivery but also transaction
            "Your order #12345 has been delivered. Your card XX5678 has been charged Rs.1,299.",
            "Your package from Amazon is out for delivery. Payment of Rs.3,499 successfully processed."
        ]
        
        # Mixed content should not be filtered (financial indicator takes precedence)
        for sms in mixed_content_sms:
            self.assertTrue(light_filter(sms), f"Incorrectly filtered mixed content: {sms}")
    
    def test_integration_with_parse_sms(self):
        """Test the integration of light filter with parse_sms function"""
        
        # Non-financial SMS that should be filtered
        otp_sms = "Your OTP for login is 123456. Valid for 10 minutes."
        
        # Parse the OTP SMS
        result = parse_sms(otp_sms, "OTPSVC")
        
        # Check that it was marked as irrelevant
        self.assertTrue(result.get("is_irrelevant", False), "OTP SMS not marked as irrelevant")
        self.assertEqual(result["transaction"]["category"], "Filtered", "Category should be 'Filtered'")
        
        # Financial SMS that should not be filtered
        transaction_sms = "Your a/c XX1234 is debited with Rs.1500.00 for Swiggy order on 2023-07-15. Available balance: Rs.12,345.67."
        
        # Parse the transaction SMS
        result = parse_sms(transaction_sms, "HDFCBK")
        
        # Check that it was not marked as irrelevant
        self.assertFalse(result.get("is_irrelevant", False), "Transaction SMS incorrectly marked as irrelevant")
        # It should either be categorized or uncategorized, but not "Filtered"
        self.assertNotEqual(result["transaction"]["category"], "Filtered", "Transaction SMS incorrectly filtered")

if __name__ == "__main__":
    unittest.main() 