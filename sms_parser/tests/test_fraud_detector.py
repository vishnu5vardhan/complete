import unittest
from datetime import datetime, timedelta
from fraud_detector import FraudDetector, FraudDetectionResult, RiskLevel, Transaction

class TestFraudDetector(unittest.TestCase):
    def setUp(self):
        self.detector = FraudDetector()
        # Add some known accounts
        self.detector.add_known_account("XX1234")
        self.detector.add_known_account("XXXX5678")

    def test_legitimate_bank_message(self):
        sms = "Dear Customer, your account XX1234 has been credited with Rs. 5000.00 on 15-03-2024. Available balance is Rs. 25000.00. -VK-ICICIBK"
        result = self.detector.detect_fraud(sms, "VK-ICICIBK")
        
        self.assertFalse(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(len(result.reasons), 0)
        self.assertTrue(result.account_match)
        self.assertEqual(len(result.flagged_keywords), 0)

    def test_fraudulent_message_with_keywords(self):
        sms = "Congratulations! You have won Rs. 1,00,000! Click here to claim your prize: bit.ly/winprize"
        result = self.detector.detect_fraud(sms)
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("keyword_match", result.reasons)
        self.assertGreater(len(result.flagged_keywords), 1)

    def test_suspicious_sender(self):
        sms = "Your account has been credited with Rs. 5000.00"
        result = self.detector.detect_fraud(sms, "NOTICE")
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("unknown_sender", result.reasons)

    def test_missing_account_number(self):
        sms = "Your bank account has been credited with Rs. 5000.00. Please check your balance."
        result = self.detector.detect_fraud(sms, "VK-ICICIBK")
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("account_mismatch", result.reasons)
        self.assertFalse(result.account_match)

    def test_loan_scam(self):
        sms = "Your loan of Rs. 5,00,000 has been approved! Click here to verify: tinyurl.com/loanverify"
        result = self.detector.detect_fraud(sms)
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("keyword_match", result.reasons)
        self.assertGreater(len(result.flagged_keywords), 1)

    def test_kyc_scam(self):
        sms = "URGENT: Your KYC needs to be updated. Click here to verify: bit.ly/kycupdate"
        result = self.detector.detect_fraud(sms)
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("keyword_match", result.reasons)
        self.assertGreater(len(result.flagged_keywords), 1)

    def test_card_block_scam(self):
        sms = "Your card has been blocked. Please verify your details: bit.ly/cardverify"
        result = self.detector.detect_fraud(sms)
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("keyword_match", result.reasons)
        self.assertGreater(len(result.flagged_keywords), 1)

    def test_legitimate_upi_transaction(self):
        sms = "UPI transaction of Rs. 1000.00 debited from your account XX1234 on 15-03-2024. Ref No: 1234567890. -VK-HDFCBK"
        result = self.detector.detect_fraud(sms, "VK-HDFCBK")
        
        self.assertFalse(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(len(result.reasons), 0)
        self.assertTrue(result.account_match)

    def test_legitimate_credit_card_transaction(self):
        sms = "Your card XXXX5678 has been charged Rs. 2500.00 at AMAZON INDIA on 15-03-2024. Available limit: Rs. 75000.00. -VK-ICICICRD"
        result = self.detector.detect_fraud(sms, "VK-ICICICRD")
        
        self.assertFalse(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.LOW)
        self.assertEqual(len(result.reasons), 0)
        self.assertTrue(result.account_match)

    def test_unknown_account_number(self):
        sms = "Your account XX9999 has been credited with Rs. 5000.00"
        result = self.detector.detect_fraud(sms, "VK-ICICIBK")
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("unknown_account", result.reasons)
        self.assertFalse(result.account_match)

    def test_mismatched_bank_sender(self):
        sms = "ICICI Bank: Your account XX1234 has been credited with Rs. 5000.00"
        result = self.detector.detect_fraud(sms, "VK-HDFCBK")  # HDFC sender for ICICI message
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.HIGH)
        self.assertIn("mismatched_bank_sender", result.reasons)

    def test_unusual_transaction_amount(self):
        sms = f"Your account XX1234 has been credited with Rs. 150000.00 on {datetime.now().strftime('%d-%m-%Y')}. -VK-ICICIBK"
        result = self.detector.detect_fraud(sms, "VK-ICICIBK")
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("unusually_large_amount", result.reasons)

    def test_unusual_transaction_hour(self):
        # Create a transaction at 3 AM
        transaction = Transaction(
            amount=5000.0,
            timestamp=datetime.now().replace(hour=3),
            account="XX1234",
            transaction_type="credit"
        )
        is_unusual, reasons = self.detector.is_unusual_transaction_pattern(transaction)
        
        self.assertTrue(is_unusual)
        self.assertIn("unusual_hour", reasons)

    def test_excessive_daily_transactions(self):
        # Add 11 transactions for today
        today = datetime.now()
        for i in range(11):
            self.detector.add_transaction(Transaction(
                amount=1000.0,
                timestamp=today,
                account="XX1234",
                transaction_type="debit"
            ))
        
        sms = f"Your account XX1234 has been debited with Rs. 1000.00 on {today.strftime('%d-%m-%Y')}. -VK-ICICIBK"
        result = self.detector.detect_fraud(sms, "VK-ICICIBK")
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("excessive_daily_transactions", result.reasons)

    def test_excessive_daily_amount(self):
        # Add transactions totaling more than max_daily_amount
        today = datetime.now()
        self.detector.add_transaction(Transaction(
            amount=190000.0,
            timestamp=today,
            account="XX1234",
            transaction_type="debit"
        ))
        
        sms = f"Your account XX1234 has been debited with Rs. 20000.00 on {today.strftime('%d-%m-%Y')}. -VK-ICICIBK"
        result = self.detector.detect_fraud(sms, "VK-ICICIBK")
        
        self.assertTrue(result.is_fraud)
        self.assertEqual(result.risk_level, RiskLevel.MEDIUM)
        self.assertIn("excessive_daily_amount", result.reasons)

    def test_transaction_history_cleanup(self):
        # Add an old transaction
        old_date = datetime.now() - timedelta(days=31)
        self.detector.add_transaction(Transaction(
            amount=1000.0,
            timestamp=old_date,
            account="XX1234",
            transaction_type="debit"
        ))
        
        # Add a recent transaction
        recent_date = datetime.now()
        self.detector.add_transaction(Transaction(
            amount=1000.0,
            timestamp=recent_date,
            account="XX1234",
            transaction_type="debit"
        ))
        
        # Check that only recent transaction remains
        self.assertEqual(len(self.detector.transaction_history), 1)
        self.assertEqual(self.detector.transaction_history[0].timestamp.date(), recent_date.date())

if __name__ == '__main__':
    unittest.main() 