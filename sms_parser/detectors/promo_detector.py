#!/usr/bin/env python3

import re
from typing import Dict, List, Tuple, Union, Optional, Any
from sms_parser.core.logger import get_logger

logger = get_logger(__name__)

def check_fraud_indicators(sms_text: str) -> Tuple[bool, List[str]]:
    """
    Check if an SMS contains typical fraud indicators that would make it 
    inappropriate to classify as merely promotional.
    
    Args:
        sms_text: The SMS text to analyze
        
    Returns:
        Tuple of (is_fraud: bool, indicators: List[str]) where indicators 
        contains the detected fraud patterns
    """
    text_lower = sms_text.lower()
    fraud_indicators = []
    
    # Phishing patterns
    kyc_phrases = ["kyc update", "kyc expire", "kyc verify", "account block", "account suspend"]
    for phrase in kyc_phrases:
        if phrase in text_lower:
            fraud_indicators.append(f"kyc_phishing:{phrase}")
    
    # Credential phishing
    credential_phrases = ["password", "login", "verify identity", "otp", "pin", "security code"]
    for phrase in credential_phrases:
        if phrase in text_lower:
            fraud_indicators.append(f"credential_phishing:{phrase}")
    
    # Prize scams
    prize_phrases = ["won prize", "lucky draw", "winner", "lottery", "prize claim"]
    for phrase in prize_phrases:
        if phrase in text_lower and ("click" in text_lower or "link" in text_lower or "call" in text_lower):
            fraud_indicators.append(f"prize_scam:{phrase}")
    
    # URL shorteners (common in phishing)
    shortener_patterns = [
        r'bit\.ly/[a-zA-Z0-9]+',
        r'goo\.gl/[a-zA-Z0-9]+',
        r'tinyurl\.com/[a-zA-Z0-9]+',
        r't\.co/[a-zA-Z0-9]+'
    ]
    
    for pattern in shortener_patterns:
        if re.search(pattern, text_lower):
            fraud_indicators.append(f"url_shortener:{pattern}")
    
    # Urgent action combined with links
    if ("urgent" in text_lower or "immediate" in text_lower) and \
       ("click" in text_lower or "link" in text_lower or re.search(r'https?://', text_lower)):
        fraud_indicators.append("urgent_with_link")
    
    # Return verdict
    is_fraud = len(fraud_indicators) > 0
    return is_fraud, fraud_indicators

def is_promotional_sms(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """
    Detect if an SMS is promotional and extract relevant information.
    
    Args:
        sms_text: The SMS text to analyze
        sender: Optional sender identifier
        
    Returns:
        Dict containing:
        - is_promotional: bool
        - promo_score: float (0-1)
        - promotion_details: Dict with offer details
    """
    # Convert to lowercase for case-insensitive matching
    text_lower = sms_text.lower()
    
    # Promotional keywords and patterns
    promo_keywords = [
        "offer", "discount", "sale", "cashback", "exclusive", "limited time",
        "special", "deal", "promotion", "promo", "voucher", "coupon", "code",
        "win", "prize", "contest", "lucky", "draw", "festival", "seasonal",
        "anniversary", "celebration", "bonus", "reward", "points", "membership"
    ]
    
    # URL patterns
    url_patterns = [
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        r"www\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}",
        r"[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"
    ]
    
    # Calculate promotional score
    score = 0.0
    matched_keywords = []
    
    # Check for promotional keywords
    for keyword in promo_keywords:
        if keyword in text_lower:
            score += 0.05
            matched_keywords.append(keyword)
    
    # Check for URLs
    for pattern in url_patterns:
        if re.search(pattern, text_lower):
            score += 0.2
            break
    
    # Check for percentage discounts
    if re.search(r"\d+%\s*(?:off|discount)", text_lower):
        score += 0.15
    
    # Check for time-limited offers
    if re.search(r"(?:valid|till|until|offer ends)\s+(?:[0-9]{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", text_lower):
        score += 0.1
    
    # Check for amount-based offers
    if re.search(r"(?:Rs\.?|INR|₹)\s*[0-9,]+(?:\.[0-9]+)?\s*(?:off|discount|cashback)", text_lower):
        score += 0.1
    
    # Cap the score at 1.0
    score = min(score, 1.0)
    
    # Extract promotion details
    promotion_details = {
        "matched_keywords": matched_keywords,
        "has_url": any(re.search(pattern, text_lower) for pattern in url_patterns),
        "has_discount": bool(re.search(r"\d+%\s*(?:off|discount)", text_lower)),
        "has_time_limit": bool(re.search(r"(?:valid|till|until|offer ends)\s+(?:[0-9]{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", text_lower)),
        "has_amount_offer": bool(re.search(r"(?:Rs\.?|INR|₹)\s*[0-9,]+(?:\.[0-9]+)?\s*(?:off|discount|cashback)", text_lower))
    }
    
    return {
        "is_promotional": score >= 0.3,  # Threshold for considering as promotional
        "promo_score": score,
        "promotion_details": promotion_details
    }

def check_promotional_sms(sms_text: str, sender: Optional[str] = None) -> Dict[str, Union[bool, float]]:
    """
    Wrapper function for promotional SMS detection.
    Uses Gemini-based detection when available, falling back to rule-based detection.
    
    Args:
        sms_text: The SMS text to analyze
        sender: Optional sender ID
        
    Returns:
        Dict containing is_promotional (bool) and promo_score (float)
    """
    try:
        # Try using Gemini-based detection first
        from langchain_wrapper import detect_promotional_sms_with_gemini
        import os
        
        # Check if we should bypass Gemini (for testing or if API key is not available)
        use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
        no_api_key = os.getenv("GEMINI_API_KEY", "") == ""
        
        if not use_mock and not no_api_key:
            # Use Gemini for detection
            result = detect_promotional_sms_with_gemini(sms_text, sender)
            # Add explanation to the log
            if "explanation" in result:
                print(f"[Promo Detection] {result['explanation']}")
            return {
                "is_promotional": result["is_promotional"],
                "promo_score": result["promo_score"]
            }
        else:
            # Use rule-based approach as fallback
            is_promo, result = is_promotional_sms(sms_text, sender)
            return {
                "is_promotional": is_promo,
                "promo_score": result["promo_score"]
            }
    except ImportError:
        # If the Gemini-based method is not available, use the rule-based approach
        print("Falling back to rule-based promotional detection")
        is_promo, result = is_promotional_sms(sms_text, sender)
        return {
            "is_promotional": is_promo,
            "promo_score": result["promo_score"]
        }
    except Exception as e:
        # If anything goes wrong, use the rule-based approach
        print(f"Error in promotional detection: {e}. Falling back to rule-based approach.")
        is_promo, result = is_promotional_sms(sms_text, sender)
        return {
            "is_promotional": is_promo,
            "promo_score": result["promo_score"]
        }

# Test the function with examples
if __name__ == "__main__":
    test_cases = [
        # Promotional SMS examples
        {
            "description": "Clothing brand promotion",
            "sms": "Exciting offers at ARROW! Shop the latest collection & enjoy stylish travel accessories, or up to Rs. 3000 OFF! Head to an exclusive store today. T&C Apply"
        },
        {
            "description": "End of season sale",
            "sms": "ARROW End of Season Sale is HERE, Buy 2 Get 2 FREE on Formals, Occasion Wear, & Casuals. Hurry, the best styles will not last! Visit an exclusive store now. TC"
        },
        {
            "description": "Promotion with URL",
            "sms": "This Pujo, sharpen your look with ARROW! Use YF7E54YO for Rs.500 OFF at GVK One Mall, Hyderabad. Enjoy exciting offers - https://bit.ly/4eIu6Sx .TC"
        },
        
        # Banking SMS examples
        {
            "description": "Credit card transaction",
            "sms": "Your KOTAK Credit Card was used for INR 3,150 on 04-Apr-25 at DECATHLON INDIA."
        },
        {
            "description": "Account debit transaction",
            "sms": "Dear Customer, your a/c XX7890 is debited with INR 2,500.00 on 05-Apr-25 at Amazon India. Available balance: INR 45,678.90"
        },
        {
            "description": "UPI transaction",
            "sms": "INR 1,200 debited from your account XX4567 for UPI transaction to PHONEPAY. Ref YGAF765463. UPI Ref UPIYWF6587434"
        },
        {
            "description": "EMI payment",
            "sms": "Your EMI of Rs.3,499 for Loan A/c no.XX1234 has been deducted. Total EMIs paid: 6/24. Next EMI due on 05-May-25. Avl Bal: Rs.45,610.22"
        },
        
        # Edge cases
        {
            "description": "Bank promotion (promotional from bank)",
            "sms": "HDFC Bank: Upgrade to our Platinum Credit Card and get 5X reward points on all purchases. Call 1800-XXX-XXXX or visit hdfcbank.com/upgrade. T&C apply."
        },
        {
            "description": "Transaction confirmation with promotional element",
            "sms": "Thank you for shopping at BigBasket! Your order of Rs.1,500 will be delivered today. Use code BBFIRST for 20% off on your next order!"
        }
    ]
    
    print("Testing Promotional SMS Detector\n")
    print("-" * 60)
    
    for i, case in enumerate(test_cases, 1):
        is_promo, result = is_promotional_sms(case["sms"])
        print(f"Test Case {i}: {case['description']}")
        print(f"SMS: {case['sms'][:60]}..." if len(case["sms"]) > 60 else f"SMS: {case['sms']}")
        print(f"Is promotional: {is_promo}")
        print(f"Promo score: {result['promo_score']:.2f}")
        print(f"Promotion details:")
        
        # Print promotion details
        for detail, value in result["promotion_details"].items():
            print(f"  - {detail}: {value}")
        
        print("-" * 60) 