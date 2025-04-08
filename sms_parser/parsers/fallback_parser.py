#!/usr/bin/env python3

import re
import datetime
from typing import Dict, Any, Optional

from sms_parser.core.logger import get_logger

# Get logger
logger = get_logger(__name__)

# Enhanced regex patterns for transaction parsing
patterns = {
    'amount': r'(?:Rs\.?|INR)\s*([0-9,.]+)',
    'transaction_type': r'(?:Sent|Debited|Credited|Transferred)',
    'merchant_name': r'to\s+([A-Z\s]+)(?:\s+on|$)',
    'account_masked': r'from\s+([A-Za-z\s]+Bank)',
    'date': r'on\s+(\d{2}/\d{2}/\d{2})',
    'category': r'(?:transfer|payment|purchase)'
}

def parse_sms(sms_text: str) -> Dict[str, Any]:
    """Parse SMS using regex patterns as fallback.
    
    Args:
        sms_text: The SMS text to parse
        
    Returns:
        Dictionary containing extracted information
    """
    result = {
        'amount': None,
        'transaction_type': None,
        'merchant_name': None,
        'account_masked': None,
        'date': None,
        'available_balance': None,
        'category': None,
        'description': None,
        'is_banking_sms': False,
        'is_promotional': False,
        'is_other': False
    }

    # Check if it's a banking transaction
    if any(re.search(pattern, sms_text, re.IGNORECASE) for pattern in [
        r'Sent\s+Rs\.',
        r'Debited\s+Rs\.',
        r'Credited\s+Rs\.',
        r'Transferred\s+Rs\.'
    ]):
        result['is_banking_sms'] = True
        
        # Extract amount
        amount_match = re.search(patterns['amount'], sms_text)
        if amount_match:
            result['amount'] = float(amount_match.group(1).replace(',', ''))
        
        # Extract transaction type
        if re.search(r'Sent|Transferred', sms_text):
            result['transaction_type'] = 'transfer'
        elif re.search(r'Debited', sms_text):
            result['transaction_type'] = 'debit'
        elif re.search(r'Credited', sms_text):
            result['transaction_type'] = 'credit'
        
        # Extract merchant name
        merchant_match = re.search(patterns['merchant_name'], sms_text)
        if merchant_match:
            result['merchant_name'] = merchant_match.group(1).strip()
        
        # Extract bank name
        bank_match = re.search(patterns['account_masked'], sms_text)
        if bank_match:
            result['account_masked'] = bank_match.group(1)
        
        # Extract date
        date_match = re.search(patterns['date'], sms_text)
        if date_match:
            date_str = date_match.group(1)
            try:
                # Convert DD/MM/YY to YYYY-MM-DD
                day, month, year = date_str.split('/')
                year = '20' + year if len(year) == 2 else year
                result['date'] = f"{year}-{month}-{day}"
            except:
                result['date'] = date_str
        
        # Set category and description
        result['category'] = 'transfer' if result['transaction_type'] == 'transfer' else 'payment'
        result['description'] = f"{result['transaction_type'].title()} to {result['merchant_name']}" if result['merchant_name'] else None

    return result

def parse_sms_fallback(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """
    Fallback parser that uses regex rules to extract basic information from SMS
    when the Gemini API fails.
    
    Args:
        sms_text: The SMS text to parse
        sender: Optional sender identifier
        
    Returns:
        Dictionary containing extracted information
    """
    # Try to extract basic information
    amount_match = re.search(patterns['amount'], sms_text)
    account_match = re.search(patterns['account_masked'], sms_text)
    date_match = re.search(patterns['date'], sms_text)
    
    # Determine transaction type
    is_debit = any(term in sms_text.lower() for term in [
        "debit", "debited", "spent", "charged", "paid", "payment", "purchase"
    ])
    is_credit = any(term in sms_text.lower() for term in [
        "credit", "credited", "received", "added"
    ])
    
    # Special handling for specific transaction keywords
    if re.search(r'emi.*deducted|deducted.*emi', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    if re.search(r'spent\s+(?:using|on)\s+your', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    if re.search(r'purchase\s+of|your\s+purchase', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    if "made" in sms_text.lower() and any(term in sms_text.lower() for term in ["payment", "purchase", "transaction"]):
        is_debit = True
        is_credit = False
    
    if re.search(r'(?:credit\s+card|card)\s+was\s+used\s+for', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    # Determine if the SMS contains URLs
    contains_urls = bool(re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', sms_text))
    
    # Extract merchant name if possible
    merchant = ""
    merchant_patterns = [
        r"at\s+([A-Za-z0-9\s]+)(?:\s+on|\s+for|$)",
        r"for\s+([A-Za-z0-9\s]+)(?:\s+on|\s+for|$)",
        r"to\s+([A-Za-z0-9\s]+)(?:\s+on|\s+for|$)"
    ]
    
    for pattern in merchant_patterns:
        merchant_match = re.search(pattern, sms_text, re.IGNORECASE)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            break
    
    # Create a minimal transaction data structure with fallback values
    transaction_data = {
        "transaction_type": "debit" if is_debit else "credit" if is_credit else "unknown",
        "amount": float(amount_match.group(1).replace(',', '')) if amount_match else 0.0,
        "merchant_name": merchant,
        "account_masked": account_match.group(1) if account_match else "",
        "date": date_match.group(1) if date_match else datetime.datetime.now().strftime("%Y-%m-%d"),
        "category": "Uncategorized",
        "description": "",
        "is_subscription": False,
        "is_bill_payment": False,
        "is_emi": "emi" in sms_text.lower(),
        "is_transfer": any(term in sms_text.lower() for term in ["transfer", "transferred"]),
        "is_refund": "refund" in sms_text.lower(),
        "balance": 0.0,
        "confidence_score": 0.1,  # Low confidence since this is fallback
        "contains_urls": contains_urls,
        "raw_sms": sms_text,
        "sender": sender,
        "parsed_at": datetime.datetime.now().isoformat(),
        "parsing_method": "fallback"
    }
    
    return transaction_data 