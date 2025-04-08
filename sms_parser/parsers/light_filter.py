#!/usr/bin/env python3

import re
from typing import List, Dict, Any

from sms_parser.core.logger import get_logger

# Get logger
logger = get_logger(__name__)

def light_filter(sms_text: str) -> bool:
    """
    Fast rule-based filter to immediately identify and filter out irrelevant SMS messages
    that don't need full parsing (e.g., OTPs, delivery notifications, etc.)
    
    Args:
        sms_text: The SMS text to analyze
        
    Returns:
        True if the SMS should be processed (relevant), False if it should be skipped (irrelevant)
    """
    if not sms_text:
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = sms_text.lower()
    
    # First check for specific non-financial message types that might contain amounts
    # but are not financial transactions (higher priority than other checks)
    specific_non_financial = [
        # Recharge confirmations
        {"pattern": r"recharge\s+(?:of|for)?\s*(?:rs\.?|inr|₹)\s*[0-9,.]+\s*(?:was|is)\s*successful", "name": "recharge_confirmation"},
        {"pattern": r"recharge\s+(?:of|for)?\s*[0-9,.]+\s*(?:rs\.?|inr|₹)\s*(?:was|is)\s*successful", "name": "recharge_confirmation"},
        
        # Plan activations
        {"pattern": r"plan\s+activated.*validity", "name": "plan_activation"},
        {"pattern": r"plan\s+of\s*(?:rs\.?|inr|₹)\s*[0-9,.]+\s*activated", "name": "plan_activation"},
        {"pattern": r"your\s+plan\s+has\s+been\s+activated", "name": "plan_activation"},
        {"pattern": r"plan\s+has\s+been\s+activated", "name": "plan_activation"},
        {"pattern": r"data:\s*[0-9.]+\s*gb", "name": "data_plan_detail"},
        
        # Data usage notifications
        {"pattern": r"data\s+usage", "name": "data_usage"},
        {"pattern": r"[0-9]+%\s+of\s+your\s+data", "name": "data_usage_percent"},
        {"pattern": r"you\s+have\s+used\s+[0-9.]+\s*(?:gb|mb)", "name": "data_usage_amount"},
        
        # Entertainment subscriptions
        {"pattern": r"subscription\s+(?:of|for)?\s*(?:rs\.?|inr|₹)\s*[0-9,.]+\s*(?:was|is)\s*renewed", "name": "subscription_renewal"},
    ]
    
    for item in specific_non_financial:
        if re.search(item["pattern"], text_lower):
            return False
    
    # Financial indicators to check for legitimate financial SMS
    financial_indicators = [
        # Transaction terms
        "transaction", "transferred", "received", 
        "credited", "debited", "spent", "paid", "payment", "purchase",
        "sent", "from", "to",  # Added for the given format
        
        # Account/card references 
        "a/c", "account", "card ending", "balance", "available bal", "avl bal", "avl limit",
        "hdfc bank", "sbi bank", "icici bank",  # Added bank names
        
        # Money indicators with amounts (these alone are not enough)
        r"rs\.?\s*[0-9,.]+", r"inr\s*[0-9,.]+", "₹", 
        
        # Banking terms
        "upi", "neft", "rtgs", "imps", "emi", "standing instruction",
        
        # Card usage
        "card used", "card charged", "charged", "spent using"
    ]
    
    # Check if the SMS contains financial indicators
    has_financial_indicators = False
    
    # Look for exact matches
    for indicator in financial_indicators:
        if indicator in text_lower:
            # Special cases for common indicators that might appear in non-financial contexts
            if indicator == "rs." or indicator == "inr" or indicator == "₹":
                # For currency symbols, require additional financial context
                if any(term in text_lower for term in ["debited", "credited", "transaction", "spent", "payment", "balance", "emi"]):
                    has_financial_indicators = True
                    break
            else:
                has_financial_indicators = True
                break
    
    # Look for regex patterns if no exact match found
    if not has_financial_indicators:
        money_patterns = [
            r"rs\.?\s*[0-9,.]+",  # Rs. 1,234.56
            r"inr\s*[0-9,.]+",    # INR 1,234.56
            r"₹\s*[0-9,.]+",      # ₹ 1,234.56
            r"[0-9,.]+\s*rs\.?",  # 1,234.56 Rs.
            r"[0-9,.]+\s*inr",    # 1,234.56 INR
            r"card\s*[a-z0-9]+",  # card XX1234
            r"a/c\s*[a-z0-9]+",   # a/c XX1234
            r"account\s*[a-z0-9]+",  # account XX1234
            r"sent\s+rs\.?\s*[0-9,.]+",  # Sent Rs.500.00
            r"from\s+[a-z]+\s+bank",  # From HDFC Bank
            r"to\s+[a-z\s]+",  # To SRIRANGAPURAM NARESH
            r"on\s+\d{2}/\d{2}/\d{2}"  # On 16/02/25
        ]
        
        for pattern in money_patterns:
            if re.search(pattern, text_lower):
                # For money patterns, do additional check to ensure it's a financial transaction
                # and not just a price or cost mentioned in a non-financial context
                if any(term in text_lower for term in ["debited", "credited", "transaction", "spent", "payment", "balance", "emi"]):
                    has_financial_indicators = True
                    break
    
    # Check for authentication messages directly (higher priority than financial indicators)
    # These patterns are specific enough that they should be fast to check
    auth_patterns = [
        r"2fa\s+code",             # 2FA code 
        r"verification\s+code",     # verification code
        r"otp\s+is",                # OTP is
        r"otp\s+for\s+login",       # OTP for login
        r"one\s+time\s+password",   # one time password
        r"security\s+code",         # security code
        r"login\s+code"             # login code
    ]
    
    for pattern in auth_patterns:
        if re.search(pattern, text_lower):
            # Special case: check if there is payment or transaction info
            if "transaction" in text_lower or "payment" in text_lower or "rs." in text_lower or "inr" in text_lower:
                # Contains both authentication and financial info, process it
                continue
            else:
                # Pure authentication message, filter it out
                return False
    
    # If the SMS has financial indicators, process it
    if has_financial_indicators:
        return True
    
    # Blacklist of terms indicating non-financial SMS
    blacklist = [
        # Authentication (more general terms)
        "otp", "one time password", "verification code", "security code", "login code", 
        "authentication code", "verify your", "verification", "2fa", "authentication", 
        "password reset", "reset your password",
        
        # Delivery/shipping
        "delivered", "out for delivery", "order shipped", "your delivery", "dispatched",
        "your order will", "package", "has been delivered", "order status",
        
        # Marketing (not financial transactions)
        "download our app", "subscribe", "follow us", "join us", 
        
        # Service messages
        "recharge successful", "plan activated", "data usage", "recharge of",
        "mobile number", "internet pack", "unlimited calls", "validity",
        
        # General notifications
        "gentle reminder", "your appointment", "confirmed your", "booking confirmed"
    ]
    
    # Check for blacklisted terms
    for term in blacklist:
        if term in text_lower:
            return False
    
    # No blacklisted terms found and no financial indicators, 
    # let's process it anyway to be safe (false negative is better than false positive)
    return True 