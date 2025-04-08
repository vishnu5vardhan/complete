#!/usr/bin/env python3

import csv
import os
import re
import argparse
from typing import Dict, List, Set, Tuple, Any

# Define paths to CSV files
DATA_DIR = 'data'  # Relative path for simplicity
BANK_CSV = os.path.join(DATA_DIR, 'bank.csv')
FRAUD_CSV = os.path.join(DATA_DIR, 'fraud.csv')
MERCHANT_CSV = os.path.join(DATA_DIR, 'merchant.csv')
MERCHANT_SHORT_CSV = os.path.join(DATA_DIR, 'merchant_short.csv')
TRANSACTION_INDICATORS_CSV = os.path.join(DATA_DIR, 'transaction_indicator_keywords.csv')

# Data structures to hold loaded data
banks = {}  # bank_name -> typical_sender_ids
fraud_keywords = set()  # Set of fraud indicator keywords
merchants = {}  # merchant_abbreviation -> (merchant_name, category)
transaction_indicators = set()  # Set of transaction indicator keywords

# Lists for language and sensitive information analysis
SENSITIVE_INFO_TERMS = [
    "otp", "one time password", "password", "pin", "cvv", "secret code",
    "verification code", "security code", "credential", "login", "username",
    "account number", "card number", "expiry", "expiration", "atm pin"
]

AGGRESSIVE_TERMS = [
    "urgent", "immediate", "alert", "warning", "action required", "must",
    "important", "attention", "critical", "mandatory", "now", "asap", "emergency",
    "restricted", "suspended", "blocked", "terminated", "deactivated", "compromised"
]

def load_banks() -> Dict[str, str]:
    """Load bank names and their typical sender IDs from CSV"""
    result = {}
    try:
        with open(BANK_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                result[row['bank_name']] = row['typical_sender_ids']
        print(f"Loaded {len(result)} banks from {BANK_CSV}")
        return result
    except Exception as e:
        print(f"Error loading bank data: {e}")
        return {}

def load_fraud_keywords() -> Set[str]:
    """Load fraud indicator keywords from CSV"""
    result = set()
    try:
        with open(FRAUD_CSV, 'r') as f:
            for line in f:
                keyword = line.strip()
                if keyword:  # Skip empty lines
                    result.add(keyword.lower())
        print(f"Loaded {len(result)} fraud keywords from {FRAUD_CSV}")
        return result
    except Exception as e:
        print(f"Error loading fraud keywords: {e}")
        return set()

def load_merchants() -> Dict[str, Tuple[str, str]]:
    """Load merchant data from CSV"""
    result = {}
    try:
        with open(MERCHANT_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                abbr = row['merchant_abbreviation']
                name = row['merchant_name']
                category = row['category']
                result[abbr] = (name, category)
        print(f"Loaded {len(result)} merchants from main file")
        
        # Try to load additional merchants from short file
        try:
            with open(MERCHANT_SHORT_CSV, 'r') as f:
                content = f.read()
                print("Loaded additional merchants from short file")
        except Exception as e:
            print(f"Note: Could not load short merchant file: {e}")
        
        return result
    except Exception as e:
        print(f"Error loading merchant data: {e}")
        return {}

def load_transaction_indicators() -> Set[str]:
    """Load transaction indicator keywords from CSV"""
    result = set()
    try:
        with open(TRANSACTION_INDICATORS_CSV, 'r') as f:
            for line in f:
                keyword = line.strip()
                if keyword:  # Skip empty lines
                    result.add(keyword.lower())
        print(f"Loaded {len(result)} transaction indicators from {TRANSACTION_INDICATORS_CSV}")
        return result
    except Exception as e:
        print(f"Error loading transaction indicators: {e}")
        return set()

def analyze_sms(sms_text, sender=None):
    """Simple SMS analyzer for testing the CSV data integration"""
    # Load the data from CSV files
    global banks, fraud_keywords, merchants, transaction_indicators
    
    if not banks:
        banks = load_banks()
    if not fraud_keywords:
        fraud_keywords = load_fraud_keywords()
    if not merchants:
        merchants = load_merchants()
    if not transaction_indicators:
        transaction_indicators = load_transaction_indicators()
    
    # Analyze the SMS
    result = {
        "raw_sms": sms_text,
        "sender": sender,
        "is_valid_sender": False,
        "merchant": None,
        "category": None,
        "transaction_indicators": [],
        "fraud_indicators": [],
        "language_issues": [],
        "sensitive_info_requests": [],
        "risk_level": "low"
    }
    
    # Check sender
    if sender:
        for bank, sender_id in banks.items():
            if sender == sender_id:
                result["is_valid_sender"] = True
                break
    
    # Check for merchants
    for abbr, (name, category) in merchants.items():
        if name.lower() in sms_text.lower():
            result["merchant"] = name
            result["category"] = category
            break
    
    # Common merchants that might not be in our list
    if not result["merchant"]:
        common_merchants = {
            "swiggy": ("Swiggy", "Food Delivery"),
            "zomato": ("Zomato", "Food Delivery"),
            "amazon": ("Amazon", "Shopping"),
            "flipkart": ("Flipkart", "Shopping"),
        }
        for key, (name, category) in common_merchants.items():
            if key in sms_text.lower():
                result["merchant"] = name
                result["category"] = category
                break
    
    # Check for transaction indicators
    for indicator in transaction_indicators:
        if indicator in sms_text.lower():
            result["transaction_indicators"].append(indicator)
    
    # Check for fraud indicators
    for keyword in fraud_keywords:
        if keyword in sms_text.lower():
            result["fraud_indicators"].append(keyword)
    
    # Check for common fraud patterns
    url_pattern = r'(?:http[s]?://|bit\.ly/|goo\.gl/|tinyurl\.com/|t\.co/)'
    if re.search(url_pattern, sms_text.lower()):
        result["fraud_indicators"].append("contains_url")
    
    if "kyc" in sms_text.lower() and ("update" in sms_text.lower() or "verify" in sms_text.lower()):
        result["fraud_indicators"].append("kyc_scam")
    
    if ("prize" in sms_text.lower() or "won" in sms_text.lower()) and ("claim" in sms_text.lower() or "collect" in sms_text.lower()):
        result["fraud_indicators"].append("prize_scam")
    
    # NEW: Check for language issues
    check_language_issues(sms_text, result)
    
    # NEW: Check for sensitive information requests
    check_sensitive_info_requests(sms_text, result)
    
    # Set risk level
    if len(result["fraud_indicators"]) >= 2 or "kyc_scam" in result["fraud_indicators"] or "prize_scam" in result["fraud_indicators"]:
        result["risk_level"] = "high"
    elif len(result["fraud_indicators"]) >= 1:
        result["risk_level"] = "medium"
    
    # Elevate risk based on language issues
    if len(result["language_issues"]) >= 2 and result["risk_level"] == "low":
        result["risk_level"] = "medium"
    elif len(result["language_issues"]) >= 2 and result["risk_level"] == "medium":
        result["risk_level"] = "high"
    
    # Elevate risk based on sensitive information requests (highest priority)
    if len(result["sensitive_info_requests"]) > 0:
        result["risk_level"] = "high"
    
    return result

def check_language_issues(sms_text, result):
    """Check for suspicious language patterns"""
    text_lower = sms_text.lower()
    
    # Check for excessive capitalization (more than 5 consecutive capital letters)
    if re.search(r'[A-Z]{5,}', sms_text):
        result["language_issues"].append("excessive_caps")
    
    # Check for excessive punctuation
    if re.search(r'[!?]{2,}', sms_text):
        result["language_issues"].append("excessive_punctuation")
    
    # Check for aggressive/threatening language
    for term in AGGRESSIVE_TERMS:
        if term.lower() in text_lower:
            result["language_issues"].append("aggressive_language")
            break
    
    # Check for poor grammar/spelling issues (common examples)
    grammar_issues = [
        (r'\byou(r)?\s+account\b', r'\byour\s+account\b'),  # "you account" vs "your account"
        (r'\bplease\s+to\b', None),  # "please to verify" etc.
        (r'\bkindly\s+(?:do|please)\b', None),  # "kindly please" redundancy
        (r'\bthe\s+the\b', None),  # "the the" duplicate
        (r'\bto\s+to\b', None),  # "to to" duplicate
        (r'\bis\s+been\b', None),  # "is been" incorrect
        (r'\bhas\s+be\b', None),  # "has be" incorrect
    ]
    
    for pattern, correct_pattern in grammar_issues:
        if re.search(pattern, text_lower):
            if correct_pattern and re.search(correct_pattern, text_lower):
                continue  # Skip if the correct pattern is found
            result["language_issues"].append("grammar_issues")
            break

def check_sensitive_info_requests(sms_text, result):
    """Check for requests for sensitive information"""
    text_lower = sms_text.lower()
    
    # Look for sensitive information terms
    for term in SENSITIVE_INFO_TERMS:
        if term in text_lower:
            # Check if it appears in a context of requesting info
            request_patterns = [
                r'(?:send|provide|share|enter|input|verify|confirm|give|text|reply with)\s+(?:\w+\s+){0,3}' + re.escape(term),
                r'' + re.escape(term) + r'\s+(?:\w+\s+){0,3}(?:required|needed|necessary|must|should)'
            ]
            
            for pattern in request_patterns:
                if re.search(pattern, text_lower):
                    result["sensitive_info_requests"].append(term)
                    break
    
    # Check for common phishing phrases
    phishing_phrases = [
        r'(?:verify|confirm|update|validate)\s+(?:\w+\s+){0,3}(?:details|information|account)',
        r'security\s+(?:measures|reasons|purposes|verification)',
        r'(?:prevent|avoid)\s+(?:suspension|termination|blocking|limiting)',
        r'account\s+(?:will\s+be|has\s+been)\s+(?:suspended|terminated|blocked|limited)',
    ]
    
    for phrase in phishing_phrases:
        if re.search(phrase, text_lower):
            result["sensitive_info_requests"].append("phishing_phrase")
            break

def run_test_cases():
    """Run test cases to demonstrate CSV integration"""
    test_cases = [
        {
            "name": "Valid Bank Transaction",
            "sms": "Your a/c XX1234 is debited with Rs.1500.00 for Swiggy order on 2023-07-15. Available balance: Rs.12,345.67.",
            "sender": "HDFCBK"
        },
        {
            "name": "KYC Scam",
            "sms": "URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc",
            "sender": "TX-KYCUPD"
        },
        {
            "name": "Prize Scam",
            "sms": "Congratulations! You've won a prize of Rs.10,00,000 in our lucky draw. To claim your prize, click here: tinyurl.com/claim-prize",
            "sender": "AX-PRIZEX"
        },
        {
            "name": "Merchant Transaction",
            "sms": "Thank you for shopping at Amazon. Rs.3,749.00 has been charged on your card ending with XX9876 on 2023-07-17. Txn ID: TXN123456.",
            "sender": "AMZN"
        },
        {
            "name": "OTP Phishing",
            "sms": "ALERT!! Your account has been compromised. To secure your account, please share your OTP sent to your mobile number immediately.",
            "sender": "SCAM-OTP"
        },
        {
            "name": "Bad Grammar Phishing",
            "sms": "Dear customer, you account is temporary suspended!!! Please to verify your details to avoiding permanent block. Click: bit.ly/verify",
            "sender": "SECALERT"
        }
    ]
    
    for test_case in test_cases:
        print(f"\nAnalyzing: {test_case['name']}")
        print(f"SMS: {test_case['sms']}")
        print(f"Sender: {test_case['sender']}")
        
        result = analyze_sms(test_case['sms'], test_case['sender'])
        
        print("\nResults:")
        print(f"  Merchant: {result['merchant']}")
        print(f"  Category: {result['category']}")
        print(f"  Transaction Indicators: {', '.join(result['transaction_indicators']) if result['transaction_indicators'] else 'None'}")
        print(f"  Fraud Indicators: {', '.join(result['fraud_indicators']) if result['fraud_indicators'] else 'None'}")
        print(f"  Language Issues: {', '.join(result['language_issues']) if result['language_issues'] else 'None'}")
        print(f"  Sensitive Info Requests: {', '.join(result['sensitive_info_requests']) if result['sensitive_info_requests'] else 'None'}")
        print(f"  Risk Level: {result['risk_level']}")
        print("-" * 50)

def interactive_mode():
    """Run in interactive mode to test SMS messages from user input"""
    print("\n" + "=" * 50)
    print("SMS Analyzer Interactive Mode")
    print("=" * 50)
    print("Enter SMS details below. Type 'exit' as the SMS text to quit.\n")
    
    # Preload data for faster analysis
    global banks, fraud_keywords, merchants, transaction_indicators
    banks = load_banks()
    fraud_keywords = load_fraud_keywords()
    merchants = load_merchants()
    transaction_indicators = load_transaction_indicators()
    
    while True:
        print("\n" + "-" * 50)
        sms_text = input("Enter SMS text (or 'exit' to quit): ")
        
        if sms_text.lower() == 'exit':
            print("Exiting interactive mode. Goodbye!")
            break
        
        sender = input("Enter sender ID (optional, press Enter to skip): ")
        if not sender:
            sender = None
        
        print("\nAnalyzing SMS...")
        result = analyze_sms(sms_text, sender)
        
        print("\nAnalysis Results:")
        print(f"  SMS: {result['raw_sms']}")
        print(f"  Sender: {result['sender'] if result['sender'] else 'Not provided'}")
        print(f"  Valid Sender: {'Yes' if result['is_valid_sender'] else 'No'}")
        print(f"  Merchant: {result['merchant'] if result['merchant'] else 'Not detected'}")
        print(f"  Category: {result['category'] if result['category'] else 'Not detected'}")
        print(f"  Transaction Indicators: {', '.join(result['transaction_indicators']) if result['transaction_indicators'] else 'None'}")
        print(f"  Fraud Indicators: {', '.join(result['fraud_indicators']) if result['fraud_indicators'] else 'None'}")
        print(f"  Language Issues: {', '.join(result['language_issues']) if result['language_issues'] else 'None'}")
        print(f"  Sensitive Info Requests: {', '.join(result['sensitive_info_requests']) if result['sensitive_info_requests'] else 'None'}")
        print(f"  Risk Level: {result['risk_level'].upper()}")

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description='SMS Analyzer for Fraud Detection')
    parser.add_argument('--examples', action='store_true', help='Run example test cases')
    parser.add_argument('--sms', type=str, help='SMS text to analyze')
    parser.add_argument('--sender', type=str, help='SMS sender ID')
    
    args = parser.parse_args()
    
    if args.examples:
        run_test_cases()
    elif args.sms:
        result = analyze_sms(args.sms, args.sender)
        print("\nAnalysis Results:")
        print(f"  SMS: {result['raw_sms']}")
        print(f"  Sender: {result['sender'] if result['sender'] else 'Not provided'}")
        print(f"  Valid Sender: {'Yes' if result['is_valid_sender'] else 'No'}")
        print(f"  Merchant: {result['merchant'] if result['merchant'] else 'Not detected'}")
        print(f"  Category: {result['category'] if result['category'] else 'Not detected'}")
        print(f"  Transaction Indicators: {', '.join(result['transaction_indicators']) if result['transaction_indicators'] else 'None'}")
        print(f"  Fraud Indicators: {', '.join(result['fraud_indicators']) if result['fraud_indicators'] else 'None'}")
        print(f"  Language Issues: {', '.join(result['language_issues']) if result['language_issues'] else 'None'}")
        print(f"  Sensitive Info Requests: {', '.join(result['sensitive_info_requests']) if result['sensitive_info_requests'] else 'None'}")
        print(f"  Risk Level: {result['risk_level'].upper()}")
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
