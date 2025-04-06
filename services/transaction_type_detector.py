#!/usr/bin/env python3

import os
import pandas as pd
from typing import Dict, List, Set

# Transaction type mappings
TRANSACTION_TYPE_MAPPING = {
    'debit': ['debited', 'spent', 'paid', 'payment of', 'transaction of', 'txn', 
              'purchased', 'debited from your account', 'amount debited', 
              'you have spent', 'you have paid', 'withdrawn', 'transferred', 
              'charged', 'auto debited', 'insta debit', 'online payment', 
              'card payment', 'pos purchase', 'emi deducted', 'bill payment', 
              'amount transferred', 'debit alert', 'paid via net banking', 
              'upi transaction', 'direct debit', 'auto payment'],
    
    'credit': ['credited', 'received', 'deposited', 'credited to your account', 
               'amount credited', 'refunded', 'settled', 'collected', 'auto credited', 
               'insta credit', 'payment received', 'credit alert'],
    
    'refund': ['refunded', 'refund']
}

def load_transaction_indicators(file_path="data/transaction_indicator_keywords.csv") -> Dict[str, Set[str]]:
    """
    Load transaction indicator keywords and map them to transaction types
    
    Args:
        file_path: Path to the transaction indicator keywords CSV file
        
    Returns:
        Dictionary mapping transaction types to sets of indicator keywords
    """
    # Initialize with default mappings
    indicators = {
        'debit': set(TRANSACTION_TYPE_MAPPING['debit']),
        'credit': set(TRANSACTION_TYPE_MAPPING['credit']),
        'refund': set(TRANSACTION_TYPE_MAPPING['refund']),
    }
    
    # Try to load from file
    if os.path.exists(file_path):
        try:
            # Load keywords from CSV
            df = pd.read_csv(file_path, header=None)
            keywords = [str(kw).lower().strip() for kw in df[0] if str(kw).strip()]
            
            # Add to corresponding transaction types
            for keyword in keywords:
                if any(debit_word in keyword for debit_word in ['debit', 'spent', 'paid', 'payment', 'withdrawn']):
                    indicators['debit'].add(keyword)
                elif any(credit_word in keyword for credit_word in ['credit', 'received', 'deposit']):
                    indicators['credit'].add(keyword)
                elif 'refund' in keyword:
                    indicators['refund'].add(keyword)
                else:
                    # Default to debit for ambiguous keywords
                    indicators['debit'].add(keyword)
                    
            print(f"Loaded {len(keywords)} transaction indicator keywords")
        except Exception as e:
            print(f"Error loading transaction indicators: {e}")
    
    return indicators

def detect_transaction_type(sms_text: str) -> str:
    """
    Detect transaction type from SMS text
    
    Args:
        sms_text: SMS text containing transaction information
        
    Returns:
        Transaction type: 'credit', 'debit', 'refund', or 'unknown'
    """
    # Load indicators (in a real app, this would be loaded once and cached)
    indicators = load_transaction_indicators()
    
    # Normalize SMS text
    sms_lower = sms_text.lower()
    
    # Check for refund first (since it's a special case of credit)
    for keyword in indicators['refund']:
        if keyword in sms_lower:
            return 'refund'
    
    # Check for credit indicators
    for keyword in indicators['credit']:
        if keyword in sms_lower:
            return 'credit'
    
    # Check for debit indicators
    for keyword in indicators['debit']:
        if keyword in sms_lower:
            return 'debit'
    
    # Default to unknown if no match
    return 'unknown'

def main():
    """Test the transaction type detection functionality"""
    # Test SMS messages
    test_sms = [
        "INR 2,499 debited from HDFC A/C xxxx1234 at Swiggy on 04/04/2025",
        "INR 5,000 credited to your ICICI A/C xxxx9999 on 05/04/2025",
        "Your refund of INR 899 has been processed to AXIS BANK xxxx4321",
        "Payment of INR 1,500 made for your electricity bill",
        "You have spent INR 3,200 using your HDFC Debit Card",
        "Transaction of INR 750 at Amazon successful",
        "A/c XX1234 credited with INR 25,000 NEFT-SALARY",
        "INR 399 paid to Netflix subscription from xx5678"
    ]
    
    # Load transaction indicators
    indicators = load_transaction_indicators()
    print(f"\nLoaded indicators for: {', '.join(indicators.keys())}")
    
    # Test each SMS
    print("\nTesting transaction type detection:")
    print("-" * 60)
    for sms in test_sms:
        transaction_type = detect_transaction_type(sms)
        print(f"SMS: {sms}")
        print(f"Detected Type: {transaction_type}")
        print("-" * 60)

if __name__ == "__main__":
    main() 