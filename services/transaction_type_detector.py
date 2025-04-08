#!/usr/bin/env python3

import os
import csv
import re
from typing import Dict, List, Set, Optional

# Global variables to store indicator data
transaction_indicators = {
    'debit': set(),
    'credit': set(),
    'refund': set(),
    'transfer': set(),
    'bill': set(),
    'emi': set()
}

# Default transaction type mappings in case file is not available
DEFAULT_INDICATORS = {
    'debit': [
        'debited', 'spent', 'paid', 'payment', 'purchase', 'shopping',
        'pos', 'txn', 'debit card', 'transaction', 'deducted'
    ],
    'credit': [
        'credited', 'received', 'deposited', 'credit', 'added', 'income',
        'salary', 'cashback', 'bonus', 'interest', 'dividend'
    ],
    'refund': [
        'refund', 'refunded', 'returned', 'reversal', 'chargeback'
    ],
    'transfer': [
        'transfer', 'sent', 'neft', 'imps', 'rtgs', 'upi', 'moved',
        'withdrawn', 'withdrawal', 'atm', 'fund transfer'
    ],
    'bill': [
        'bill', 'payment', 'electricity', 'water', 'gas', 'insurance',
        'premium', 'utility', 'mobile', 'telephone', 'broadband', 'internet',
        'dth', 'fastag', 'recharge'
    ],
    'emi': [
        'emi', 'loan', 'installment', 'repayment', 'due'
    ]
}

def load_transaction_indicators(refresh: bool = False) -> Dict[str, Set[str]]:
    """
    Load transaction indicator keywords from the CSV file
    
    Args:
        refresh: Whether to force reload the data
        
    Returns:
        Dictionary mapping transaction types to sets of indicator keywords
    """
    global transaction_indicators
    
    # If already loaded and not forced to refresh, return cached data
    if transaction_indicators['debit'] and not refresh:
        return transaction_indicators
    
    # Reset indicators to empty sets
    for key in transaction_indicators:
        transaction_indicators[key] = set()
    
    # Path to the transaction indicator keywords file
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    indicator_file = os.path.join(base_path, "data", "transaction_indicator_keywords.csv")
    
    # Try to load from file
    if os.path.exists(indicator_file):
        try:
            with open(indicator_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        keyword = row[0].strip().lower()
                        
                        # Categorize keywords based on content
                        if any(word in keyword for word in ['refund', 'return', 'chargeback']):
                            transaction_indicators['refund'].add(keyword)
                        elif any(word in keyword for word in ['transfer', 'neft', 'imps', 'rtgs', 'upi', 'withdrawn']):
                            transaction_indicators['transfer'].add(keyword)
                        elif any(word in keyword for word in ['bill', 'utility', 'electricity', 'water', 'gas', 'recharge']):
                            transaction_indicators['bill'].add(keyword)
                        elif any(word in keyword for word in ['emi', 'loan', 'installment']):
                            transaction_indicators['emi'].add(keyword)
                        elif any(word in keyword for word in ['debit', 'spent', 'paid', 'payment', 'purchase']):
                            transaction_indicators['debit'].add(keyword)
                        elif any(word in keyword for word in ['credit', 'received', 'deposit', 'added']):
                            transaction_indicators['credit'].add(keyword)
                        else:
                            # Default to debit for ambiguous keywords
                            transaction_indicators['debit'].add(keyword)
                
                print(f"Loaded transaction indicators from {indicator_file}")
        except Exception as e:
            print(f"Error loading transaction indicators: {e}")
            # Fall back to defaults if file loading fails
            use_default_indicators()
    else:
        print(f"Transaction indicator file not found at {indicator_file}, using defaults")
        use_default_indicators()
    
    return transaction_indicators

def use_default_indicators():
    """Load the default transaction indicators when file is not available"""
    global transaction_indicators
    
    for txn_type, keywords in DEFAULT_INDICATORS.items():
        for keyword in keywords:
            transaction_indicators[txn_type].add(keyword)
    
    print(f"Loaded {sum(len(v) for v in transaction_indicators.values())} default indicators")

def detect_transaction_type(sms_text: str) -> str:
    """
    Detect transaction type from SMS text using loaded indicators
    
    Args:
        sms_text: SMS text containing transaction information
        
    Returns:
        Transaction type: 'credit', 'debit', 'refund', 'transfer', 'bill', 'emi' or 'unknown'
    """
    global transaction_indicators
    
    # Load indicators if not loaded
    if not transaction_indicators['debit']:
        load_transaction_indicators()
    
    # Normalize SMS text
    sms_lower = sms_text.lower()
    
    # Enhanced patterns for transaction type detection
    patterns = {
        'debit': [
            r'debited.*?rs\.?\s*\d+',
            r'spent.*?rs\.?\s*\d+',
            r'paid.*?rs\.?\s*\d+',
            r'payment.*?rs\.?\s*\d+',
            r'purchase.*?rs\.?\s*\d+',
            r'shopping.*?rs\.?\s*\d+',
            r'card.*?used.*?rs\.?\s*\d+',
            r'pos.*?rs\.?\s*\d+',
            r'txn.*?rs\.?\s*\d+',
            r'debit.*?card.*?rs\.?\s*\d+',
            r'transaction.*?rs\.?\s*\d+',
            r'deducted.*?rs\.?\s*\d+'
        ],
        'credit': [
            r'credited.*?rs\.?\s*\d+',
            r'received.*?rs\.?\s*\d+',
            r'deposited.*?rs\.?\s*\d+',
            r'credit.*?rs\.?\s*\d+',
            r'added.*?rs\.?\s*\d+',
            r'income.*?rs\.?\s*\d+',
            r'salary.*?rs\.?\s*\d+',
            r'cashback.*?rs\.?\s*\d+',
            r'bonus.*?rs\.?\s*\d+',
            r'interest.*?rs\.?\s*\d+',
            r'dividend.*?rs\.?\s*\d+'
        ],
        'refund': [
            r'refund.*?rs\.?\s*\d+',
            r'refunded.*?rs\.?\s*\d+',
            r'returned.*?rs\.?\s*\d+',
            r'reversal.*?rs\.?\s*\d+',
            r'chargeback.*?rs\.?\s*\d+'
        ],
        'transfer': [
            r'transfer.*?rs\.?\s*\d+',
            r'sent.*?rs\.?\s*\d+',
            r'neft.*?rs\.?\s*\d+',
            r'imps.*?rs\.?\s*\d+',
            r'rtgs.*?rs\.?\s*\d+',
            r'upi.*?rs\.?\s*\d+',
            r'moved.*?rs\.?\s*\d+',
            r'withdrawn.*?rs\.?\s*\d+',
            r'withdrawal.*?rs\.?\s*\d+',
            r'atm.*?rs\.?\s*\d+',
            r'fund.*?transfer.*?rs\.?\s*\d+'
        ],
        'bill': [
            r'bill.*?rs\.?\s*\d+',
            r'payment.*?rs\.?\s*\d+',
            r'electricity.*?rs\.?\s*\d+',
            r'water.*?rs\.?\s*\d+',
            r'gas.*?rs\.?\s*\d+',
            r'insurance.*?rs\.?\s*\d+',
            r'premium.*?rs\.?\s*\d+',
            r'utility.*?rs\.?\s*\d+',
            r'mobile.*?rs\.?\s*\d+',
            r'telephone.*?rs\.?\s*\d+',
            r'broadband.*?rs\.?\s*\d+',
            r'internet.*?rs\.?\s*\d+',
            r'dth.*?rs\.?\s*\d+',
            r'fastag.*?rs\.?\s*\d+',
            r'recharge.*?rs\.?\s*\d+'
        ],
        'emi': [
            r'emi.*?rs\.?\s*\d+',
            r'loan.*?rs\.?\s*\d+',
            r'installment.*?rs\.?\s*\d+',
            r'repayment.*?rs\.?\s*\d+',
            r'due.*?rs\.?\s*\d+'
        ]
    }
    
    # Count pattern matches for each transaction type
    type_scores = {txn_type: 0 for txn_type in patterns.keys()}
    
    for txn_type, txn_patterns in patterns.items():
        for pattern in txn_patterns:
            if re.search(pattern, sms_lower):
                type_scores[txn_type] += 1
    
    # Special rules for ambiguity resolution
    if type_scores['refund'] > 0:
        return 'refund'  # Refund takes precedence
    
    if type_scores['transfer'] > 0:
        if 'to ' in sms_lower and any(word in sms_lower for word in ['sent', 'transfer']):
            return 'transfer'  # Outgoing transfer
        if 'from ' in sms_lower and any(word in sms_lower for word in ['received', 'transfer']):
            return 'credit'  # Incoming transfer is credit
    
    if type_scores['emi'] > 0:
        return 'emi'  # EMI is a special type of debit
    
    if type_scores['bill'] > 0 and type_scores['debit'] > 0:
        return 'bill'  # Bill payment is a specialized debit
    
    # Find the transaction type with the highest score
    max_score_type = max(type_scores.items(), key=lambda x: x[1])
    
    if max_score_type[1] > 0:
        return max_score_type[0]
    
    # Fallback to keyword-based detection if no patterns matched
    if any(keyword in sms_lower for keyword in ['debited', 'spent', 'paid', 'deducted', 'charged']):
        return 'debit'
    
    if any(keyword in sms_lower for keyword in ['credited', 'received', 'added']):
        return 'credit'
    
    # Default to unknown if no match
    return 'unknown'

def get_transaction_details(sms_text: str) -> Dict[str, any]:
    """
    Get more detailed transaction information from SMS text
    
    Args:
        sms_text: SMS text containing transaction information
        
    Returns:
        Dictionary with transaction details
    """
    details = {
        'transaction_type': detect_transaction_type(sms_text),
        'is_bill_payment': False,
        'is_emi': False,
        'is_transfer': False,
        'is_refund': False
    }
    
    # Set additional flags based on transaction type
    if details['transaction_type'] == 'bill':
        details['is_bill_payment'] = True
    elif details['transaction_type'] == 'emi':
        details['is_emi'] = True
    elif details['transaction_type'] == 'transfer':
        details['is_transfer'] = True
    elif details['transaction_type'] == 'refund':
        details['is_refund'] = True
        
    # Map specialized types to base types for backward compatibility
    if details['transaction_type'] in ['bill', 'emi']:
        details['transaction_type'] = 'debit'
    
    return details

# Load indicators on module import
load_transaction_indicators()

if __name__ == "__main__":
    # Test the transaction type detection functionality
    load_transaction_indicators()
    
    # Print indicator counts
    print("Transaction indicators loaded:")
    for txn_type, indicators in transaction_indicators.items():
        print(f"  {txn_type}: {len(indicators)} keywords")
    
    # Test SMS messages
    test_sms = [
        "INR 2,499 debited from HDFC A/C xxxx1234 at Swiggy on 04/04/2025",
        "INR 5,000 credited to your ICICI A/C xxxx9999 on 05/04/2025",
        "Your refund of INR 899 has been processed to AXIS BANK xxxx4321",
        "Payment of INR 1,500 made for your electricity bill",
        "You have spent INR 3,200 using your HDFC Debit Card",
        "Transaction of INR 750 at Amazon successful",
        "A/c XX1234 credited with INR 25,000 NEFT-SALARY",
        "INR 399 paid to Netflix subscription from xx5678",
        "EMI of Rs. 5,000 debited from your HDFC Card ending 1234 for Home Loan",
        "Fund transfer of Rs. 12,000 to Acct XX5678 successful. Ref: UPI12345",
        "Rs.10,000 sent to Ram via PhonePe UPI"
    ]
    
    # Test each SMS
    print("\nTesting transaction type detection:")
    print("-" * 80)
    for sms in test_sms:
        details = get_transaction_details(sms)
        print(f"SMS: {sms}")
        print(f"Detected Type: {details['transaction_type']}")
        if details['is_bill_payment']:
            print("  (Bill Payment)")
        if details['is_emi']:
            print("  (EMI Payment)")
        if details['is_transfer']:
            print("  (Fund Transfer)")
        if details['is_refund']:
            print("  (Refund Transaction)")
        print("-" * 80) 