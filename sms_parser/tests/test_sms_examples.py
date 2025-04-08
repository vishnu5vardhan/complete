#!/usr/bin/env python3

"""
Test SMS Examples
================
Collection of test SMS examples organized by category for testing the SMS parser.
"""

import random
from typing import Dict, List, Any, Optional

# Banking Transaction Examples
BANKING_EXAMPLES = [
    {
        "sender": "HDFCBK",
        "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
        "description": "Credit card transaction with merchant and available limit",
        "expected": {
            "transaction_type": "debit",
            "amount": 689.0,
            "merchant": "McDonald's"
        }
    },
    {
        "sender": "ICICIB",
        "sms": "Rs.2,500.00 is debited from your A/c XXXX1234 on 05-Apr-25 18:45:23 by UPI-AMAZON PAY INDIA PVT LTD. Avl Bal: Rs.18,340.50",
        "description": "UPI debit transaction with balance",
        "expected": {
            "transaction_type": "debit",
            "amount": 2500.0,
            "merchant": "Amazon Pay"
        }
    },
    {
        "sender": "SBIINB",
        "sms": "Your a/c no. XX786 is credited with INR 40,000.00 on 01-Apr-25 by a/c linked to VPA xyz@ybl. New balance: INR 42,890.75",
        "description": "UPI credit transaction with new balance",
        "expected": {
            "transaction_type": "credit",
            "amount": 40000.0,
            "merchant": None
        }
    },
    {
        "sender": "IDFCFB",
        "sms": "EMI deducted for loan A/C 12345678. INR 8,750.00 debited from your A/C XX3456 on 05-Apr-25. Available balance: INR 24,650.82",
        "description": "EMI deduction with loan account number",
        "expected": {
            "transaction_type": "debit",
            "amount": 8750.0,
            "merchant": None
        }
    },
    {
        "sender": "AXISBK",
        "sms": "INR 3,250.00 was spent on your Axis Bank GOLD Credit Card XX5678 at MARRIOTT HOTELS on 06-Apr-25. This spend also earned you 325 points.",
        "description": "Credit card transaction with reward points",
        "expected": {
            "transaction_type": "debit",
            "amount": 3250.0,
            "merchant": "Marriott Hotels"
        }
    }
]

# Credit Card Offers and Marketing
CREDIT_CARD_OFFERS = [
    {
        "sender": "HDFCBK",
        "sms": "Exclusive Offer: Get 5% cashback up to Rs.1,000 on all online shopping with your HDFC Credit Card till April 30th, 2025. T&C apply.",
        "description": "Cashback offer for credit card",
        "expected": {
            "is_promotional": True
        }
    },
    {
        "sender": "SBICARD",
        "sms": "Your SBI Card brings you special Diwali offers! Enjoy 10% discount at leading electronics stores and 0% EMI for 6 months. Shop now!",
        "description": "Festival discount offer",
        "expected": {
            "is_promotional": True
        }
    },
    {
        "sender": "ICICIB",
        "sms": "ICICI Bank presents Reward Points Bonanza: Use your Credit Card for fuel purchases and earn 5X reward points until 15th May. Min. transaction: Rs.500",
        "description": "Reward points promotion",
        "expected": {
            "is_promotional": True
        }
    }
]

# Promotional Messages
PROMOTIONAL_EXAMPLES = [
    {
        "sender": "AMZNDL",
        "sms": "Your Amazon order of iPhone 13 will be delivered TODAY before 8 PM. Track your order at: https://amzn.in/track",
        "description": "Order delivery notification",
        "expected": {
            "is_promotional": True
        }
    },
    {
        "sender": "BIGBSKT",
        "sms": "Weekend Sale! Get up to 50% OFF on fresh fruits & vegetables. Use code FRESH50 for extra 10% discount on orders above Rs.999. Order now on BigBasket!",
        "description": "Weekend sale promotion",
        "expected": {
            "is_promotional": True
        }
    },
    {
        "sender": "MYNTRA",
        "sms": "HURRY! Your wishlist items are now on SALE. Tops & dresses starting at Rs.499. Shop in the next 6 hours to avail FREE shipping. T&C apply.",
        "description": "Flash sale notification",
        "expected": {
            "is_promotional": True
        }
    }
]

# Wallet Transactions
WALLET_EXAMPLES = [
    {
        "sender": "PAYTMB",
        "sms": "Rs.500 has been added to your Paytm Wallet from your bank account XXXX1234 on 04-Apr-25. Current balance: Rs.750.25",
        "description": "Wallet loading transaction",
        "expected": {
            "transaction_type": "credit",
            "amount": 500.0,
            "merchant": "Paytm"
        }
    },
    {
        "sender": "PhonePe",
        "sms": "Payment of Rs.245.00 made successfully to SWIGGY from your PhonePe account on 05-Apr-25 12:30:45. Ref no: 123456789. Balance: Rs.855.50",
        "description": "Wallet payment to merchant",
        "expected": {
            "transaction_type": "debit",
            "amount": 245.0,
            "merchant": "Swiggy"
        }
    },
    {
        "sender": "GPAYBNK",
        "sms": "You paid Rs.100 to Rahul S using Google Pay UPI. UPI Ref: 123456789012. Balance: Rs.2,400.50",
        "description": "Peer-to-peer payment through wallet",
        "expected": {
            "transaction_type": "debit",
            "amount": 100.0,
            "merchant": None
        }
    }
]

# Fraudulent Messages
FRAUDULENT_EXAMPLES = [
    {
        "sender": "TX-KYCSMS",
        "sms": "URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc",
        "description": "KYC scam message",
        "expected": {
            "is_suspicious": True,
            "risk_level": "high"
        }
    },
    {
        "sender": "SBIALERT",
        "sms": "Your SBI account is temporarily suspended due to unauthorized login. Verify your details at: sbi-secure.co/verify",
        "description": "Account suspension phishing",
        "expected": {
            "is_suspicious": True,
            "risk_level": "high"
        }
    },
    {
        "sender": "TX-REFUND",
        "sms": "Your tax refund of Rs.12,500 is pending. Download form and submit your bank details on taxrefund-india.com to process refund.",
        "description": "Tax refund phishing",
        "expected": {
            "is_suspicious": True,
            "risk_level": "high"
        }
    },
    {
        "sender": "AADHAR",
        "sms": "ALERT: Your Aadhaar card will be deactivated tomorrow. Call 9876543210 immediately to keep your Aadhaar active.",
        "description": "Aadhaar deactivation scam",
        "expected": {
            "is_suspicious": True,
            "risk_level": "high"
        }
    }
]

# OTP and Authentication Messages
OTP_EXAMPLES = [
    {
        "sender": "HDFCBK",
        "sms": "123456 is your OTP for transaction of INR 4,999.00 at FLIPKART with your HDFC Bank Card XX1234. OTP is valid for 10 mins. Do not share with anyone.",
        "description": "Transaction OTP for online purchase",
        "expected": {
            "is_otp": True,
            "is_suspicious": False
        }
    },
    {
        "sender": "ICICIB",
        "sms": "Your OTP for ICICI Bank Net Banking login is 789012. Valid for 5 mins. DO NOT share with anyone including bank officials.",
        "description": "Net banking login OTP",
        "expected": {
            "is_otp": True,
            "is_suspicious": False
        }
    },
    {
        "sender": "AMAZONIN",
        "sms": "654321 is your Amazon verification code. For your security, do not share this code.",
        "description": "E-commerce verification code",
        "expected": {
            "is_otp": True,
            "is_suspicious": False
        }
    }
]

# UPI Transactions
UPI_EXAMPLES = [
    {
        "sender": "SBIINB",
        "sms": "You've received Rs.5,000.00 from Amit Kumar in your A/c No.XX3456 on 06-Apr-25 on UPI:amit@okicici. UPI Ref: 123456789012",
        "description": "UPI money received",
        "expected": {
            "transaction_type": "credit",
            "amount": 5000.0,
            "merchant": None
        }
    },
    {
        "sender": "HDFCBK",
        "sms": "Rs.3,499.00 debited from your A/c XXXX6789 to xyz@paytm on 07-Apr-25 19:45:23. UPI Ref: 987654321098. Balance: Rs.12,500.75",
        "description": "UPI money sent",
        "expected": {
            "transaction_type": "debit",
            "amount": 3499.0,
            "merchant": "Paytm"
        }
    },
    {
        "sender": "BOIUPI",
        "sms": "Payment of Rs.899 successful to ZOMATO (zomato@hdfcbank) from your Bank of India a/c XX7890 using UPI app. Ref: 567890123456",
        "description": "UPI payment to merchant",
        "expected": {
            "transaction_type": "debit",
            "amount": 899.0,
            "merchant": "Zomato"
        }
    }
]

# Account Updates and Alerts
ACCOUNT_UPDATES = [
    {
        "sender": "AXISBK",
        "sms": "Your Axis Bank credit card statement for Apr 2025 is ready. Total due: Rs.15,756.90. Min. due: Rs.1,500.00. Due date: 18-May-25. Pay now on Axis Mobile App.",
        "description": "Credit card statement notification",
        "expected": {
            "is_promotional": False,
            "is_suspicious": False
        }
    },
    {
        "sender": "HDFCBK",
        "sms": "Your HDFC Bank savings account XX4567 has new interest credit of Rs.345.25 on 31-Mar-25. Updated balance: Rs.45,890.75",
        "description": "Interest credit notification",
        "expected": {
            "transaction_type": "credit",
            "amount": 345.25,
            "merchant": None
        }
    },
    {
        "sender": "KOTAKB",
        "sms": "Your Credit Card payment of Rs.12,000.00 is due on 10-Apr-25. Please ensure sufficient balance in your account for auto-debit.",
        "description": "Payment due reminder",
        "expected": {
            "is_promotional": False,
            "is_suspicious": False
        }
    }
]

# Edge Cases and Complex Messages
EDGE_CASES = [
    {
        "sender": "SBIINB",
        "sms": "INR 5,000.00 transferred from a/c XXXX5678 to XXXX1234 on 08-Apr-25 12:34:56 Ref. NEFT-SBINR-123456789. Avl Bal: INR 25,400.00",
        "description": "NEFT transfer between own accounts",
        "expected": {
            "transaction_type": "debit",
            "amount": 5000.0,
            "merchant": None
        }
    },
    {
        "sender": "HDFCBK",
        "sms": "Congrats! Your loan application is approved. Loan amount: Rs.2,00,000. EMI: Rs.4,200 x 60 months. Disbursed to a/c XXXX5678.",
        "description": "Loan approval and disbursement",
        "expected": {
            "transaction_type": "credit",
            "amount": 200000.0,
            "merchant": None
        }
    },
    {
        "sender": "ICICIB",
        "sms": "Your ICICI Bank Credit Card XX5678 transaction of INR 3,499 at AMAZON.IN was cancelled. Refund initiated and will reflect in 5-7 business days.",
        "description": "Transaction cancellation and refund",
        "expected": {
            "transaction_type": "credit",
            "amount": 3499.0,
            "merchant": "Amazon"
        }
    },
    {
        "sender": "VM-AIRTEL",
        "sms": "Thank you for paying your Airtel DTH bill of Rs.799 for acc no. 123456789. Payment received on 05-Apr-25. Next due date: 05-May-25.",
        "description": "Bill payment confirmation",
        "expected": {
            "is_promotional": False,
            "is_suspicious": False
        }
    }
]

# Combine all examples into a single dictionary
ALL_EXAMPLES = {
    "banking": BANKING_EXAMPLES,
    "credit_card_offers": CREDIT_CARD_OFFERS,
    "promotional": PROMOTIONAL_EXAMPLES,
    "wallet": WALLET_EXAMPLES,
    "fraudulent": FRAUDULENT_EXAMPLES,
    "otp": OTP_EXAMPLES,
    "upi": UPI_EXAMPLES,
    "account_updates": ACCOUNT_UPDATES,
    "edge_cases": EDGE_CASES,
}

# Define types by category
TRANSACTION_TYPES = ["banking", "wallet", "upi", "edge_cases"]
PROMOTIONAL_TYPES = ["credit_card_offers", "promotional"]
FRAUD_TYPES = ["fraudulent"]
OTP_TYPES = ["otp"]
INFO_TYPES = ["account_updates"]

def get_random_example() -> Dict[str, str]:
    """
    Get a random SMS example from all categories
    
    Returns:
        A dictionary containing the SMS text and sender
    """
    # Get a random category
    category = random.choice(list(ALL_EXAMPLES.keys()))
    
    # Get a random example from that category
    if category in ALL_EXAMPLES and ALL_EXAMPLES[category]:
        example = random.choice(ALL_EXAMPLES[category])
        return {
            "sms": example["sms"],
            "sender": example["sender"],
            "description": example.get("description", ""),
            "category": category
        }
    
    # Fallback
    return {
        "sms": "This is a test SMS message",
        "sender": "TESTSMS",
        "description": "Test message",
        "category": "test"
    }

def get_example_by_category(category: str) -> Optional[Dict[str, str]]:
    """
    Get a random SMS example from a specific category
    
    Args:
        category: The category to get an example from
        
    Returns:
        A dictionary containing the SMS text and sender, or None if category doesn't exist
    """
    if category in ALL_EXAMPLES and ALL_EXAMPLES[category]:
        example = random.choice(ALL_EXAMPLES[category])
        return {
            "sms": example["sms"],
            "sender": example["sender"],
            "description": example.get("description", ""),
            "category": category
        }
    
    return None

def get_examples_by_type(type_name: str) -> List[Dict[str, str]]:
    """
    Get all SMS examples of a specific type
    
    Args:
        type_name: The type name (transaction, promotional, fraud, otp, info)
        
    Returns:
        A list of dictionaries containing SMS examples
    """
    examples = []
    
    # Map type name to categories
    if type_name == "transaction":
        categories = TRANSACTION_TYPES
    elif type_name == "promotional":
        categories = PROMOTIONAL_TYPES
    elif type_name == "fraud":
        categories = FRAUD_TYPES
    elif type_name == "otp":
        categories = OTP_TYPES
    elif type_name == "info":
        categories = INFO_TYPES
    else:
        # Unknown type
        return []
    
    # Get examples from each category
    for category in categories:
        if category in ALL_EXAMPLES:
            for example in ALL_EXAMPLES[category]:
                examples.append({
                    "sms": example["sms"],
                    "sender": example["sender"],
                    "description": example.get("description", ""),
                    "category": category
                })
    
    return examples

def get_all_examples() -> List[Dict[str, str]]:
    """
    Get all SMS examples
    
    Returns:
        A list of dictionaries containing all SMS examples
    """
    examples = []
    
    for category, category_examples in ALL_EXAMPLES.items():
        for example in category_examples:
            examples.append({
                "sms": example["sms"],
                "sender": example["sender"],
                "description": example.get("description", ""),
                "category": category
            })
    
    return examples

if __name__ == "__main__":
    # Print summary of available examples
    print(f"SMS Examples Summary:")
    print(f"=====================")
    
    total_examples = 0
    for category, examples in ALL_EXAMPLES.items():
        print(f"- {category.replace('_', ' ').title()}: {len(examples)} examples")
        total_examples += len(examples)
    
    print(f"\nTotal: {total_examples} examples")
    
    # Print a random example
    random_example = get_random_example()
    print(f"\nRandom Example ({random_example['category']}):")
    print(f"Sender: {random_example['sender']}")
    print(f"SMS: {random_example['sms']}")
    if random_example.get('description'):
        print(f"Description: {random_example['description']}")

# Test SMS examples for different categories
BANKING_SMS = [
    {
        "text": "Your account XX1234 has been debited with Rs.1500.00 on 05-04-2023 for a purchase at Swiggy. Available balance is Rs.12,345.67.",
        "sender": "HDFCBK",
        "expected": {
            "is_banking_sms": True,
            "is_promotional": False,
            "transaction_type": "debit",
            "amount": 1500.00,
            "merchant_name": "Swiggy",
            "account_masked": "XX1234",
            "date": "05-04-2023",
            "available_balance": 12345.67
        }
    },
    {
        "text": "Your account XX5678 has been credited with Rs.25,000.00 on 10-04-2023. Available balance is Rs.50,000.00.",
        "sender": "ICICIB",
        "expected": {
            "is_banking_sms": True,
            "is_promotional": False,
            "transaction_type": "credit",
            "amount": 25000.00,
            "merchant_name": "",
            "account_masked": "XX5678",
            "date": "10-04-2023",
            "available_balance": 50000.00
        }
    }
]

PROMOTIONAL_SMS = [
    {
        "text": "SPECIAL OFFER! Get 50% off on your next order at Swiggy. Use code SAVE50. Offer valid till 31-05-2023. Shop now at www.swiggy.com",
        "sender": "SWIGGY",
        "expected": {
            "is_banking_sms": False,
            "is_promotional": True,
            "promo_score": 0.85,
            "promotion_details": {
                "matched_keywords": ["offer", "discount", "code"],
                "has_url": True,
                "has_discount": True,
                "has_time_limit": True,
                "has_amount_offer": False
            }
        }
    },
    {
        "text": "Win exciting prizes! Participate in our lucky draw. Click here: bit.ly/winprizes",
        "sender": "PROMO",
        "expected": {
            "is_banking_sms": False,
            "is_promotional": True,
            "promo_score": 0.75,
            "promotion_details": {
                "matched_keywords": ["win", "prize", "lucky", "draw"],
                "has_url": True,
                "has_discount": False,
                "has_time_limit": False,
                "has_amount_offer": False
            }
        }
    }
]

FRAUD_SMS = [
    {
        "text": "ALERT: Your account is blocked. Urgent action required. Call +91-1234567890 immediately or click on http://suspicious-link.com to verify.",
        "sender": "Unknown",
        "expected": {
            "is_fraud": True,
            "risk_level": "high",
            "reasons": ["urgent_action", "suspicious_link", "unknown_sender"],
            "flagged_keywords": ["blocked", "urgent", "immediately"]
        }
    },
    {
        "text": "Your account needs verification. Please share your OTP 123456 to continue using your account.",
        "sender": "HDFCBK",
        "expected": {
            "is_fraud": True,
            "risk_level": "high",
            "reasons": ["otp_request", "verification_request"],
            "flagged_keywords": ["verification", "share", "otp"]
        }
    }
]

NON_FINANCIAL_SMS = [
    {
        "text": "Your OTP for login is 123456. Valid for 10 minutes.",
        "sender": "AMAZON",
        "expected": {
            "is_banking_sms": False,
            "is_promotional": False,
            "is_fraud": False
        }
    },
    {
        "text": "Your delivery #12345 is out for delivery. Track at www.delivery.com",
        "sender": "DELIVERY",
        "expected": {
            "is_banking_sms": False,
            "is_promotional": False,
            "is_fraud": False
        }
    }
]

def get_test_sms(category: str) -> List[Dict]:
    """
    Get test SMS examples for a specific category.
    
    Args:
        category: One of 'banking', 'promotional', 'fraud', or 'non_financial'
        
    Returns:
        List of test SMS examples
    """
    category_map = {
        'banking': BANKING_SMS,
        'promotional': PROMOTIONAL_SMS,
        'fraud': FRAUD_SMS,
        'non_financial': NON_FINANCIAL_SMS
    }
    
    return category_map.get(category.lower(), []) 