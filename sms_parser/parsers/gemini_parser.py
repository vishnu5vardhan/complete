#!/usr/bin/env python3

import re
import json
import datetime
import os
import csv
import time
from typing import Dict, Any, Optional, List, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

from sms_parser.core.logger import get_logger
from sms_parser.core.config import GEMINI_API_KEY, ENABLE_MOCK_MODE

# Add constant for JSON file path
PARSED_SMS_FILE = "parsed_sms_data.json"

def _generate_mock_response(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """Generate a mock response for testing purposes."""
    return {
        "message_type": "transaction",
        "transaction_type": "debit",
        "amount": 1000.0,
        "merchant_name": "Test Merchant",
        "account_masked": "XXXX1234",
        "date": "2024-03-12",
        "available_balance": 5000.0,
        "description": "Test transaction",
        "is_mock": True
    }

def _extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extract JSON from the response text."""
    try:
        # Find JSON in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {}
    except json.JSONDecodeError:
        return {}

def _fallback_regex_parse(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """Fallback parser using regex patterns."""
    result = {}
    sms_text_lower = sms_text.lower()
    
    # First check if this is a balance update message
    balance_update_indicators = [
        "balance update", "current balance", "available balance", "a/c balance", 
        "avl bal", "available bal", "bal:", "balance is", "statement", "ministatement",
        "balance as of", "your a/c", "your account", "bal is", "balance:", "closing balance"
    ]
    
    is_balance_update = any(indicator in sms_text_lower for indicator in balance_update_indicators)
    
    # Also check for balance amount patterns
    balance_patterns = [
        r'balance[^0-9]*(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)',
        r'bal[^0-9]*(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)',
        r'balance is (?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)',
        r'(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)[^0-9]*balance',
        r'(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)[^0-9]*bal'
    ]
    
    has_balance_amount = any(re.search(pattern, sms_text_lower) for pattern in balance_patterns)
    
    # Make sure it's not also a transaction (which would take precedence)
    transaction_indicators = ["debited", "credited", "payment", "spent", "purchase", "transaction"]
    is_transaction = any(indicator in sms_text_lower for indicator in transaction_indicators)
    
    if (is_balance_update or has_balance_amount) and not is_transaction:
        # This appears to be a balance update message
        result["message_type"] = "balance_update"
        
        # Extract balance
        for pattern in balance_patterns:
            balance_match = re.search(pattern, sms_text_lower)
            if balance_match:
                try:
                    result["available_balance"] = float(balance_match.group(1).replace(',', ''))
                    break
                except ValueError:
                    # Handle potential conversion errors
                    pass
        
        # Try simple amount extraction if above patterns didn't work
        if "available_balance" not in result:
            amount_match = re.search(r'(?:rs\.?|inr|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)', sms_text_lower)
            if amount_match:
                try:
                    result["available_balance"] = float(amount_match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        # Extract account number
        account_match = re.search(r'(?:a/c|acc(?:ount)?)[^0-9]*([A-Z0-9]+)', sms_text)
        if account_match:
            result["account_masked"] = account_match.group(1)
        
        # Extract date if available
        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', sms_text)
        if date_match:
            result["date"] = date_match.group(1)
        else:
            # Use current date as fallback
            result["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Extract bank name if available
        for bank in BANKS:
            bank_name = bank.get('name', '').lower()
            if bank_name in sms_text_lower:
                result["bank"] = bank.get('name')
                break
        
        return result
    
    # Check for credit card bills first
    credit_card_pattern = r'(?:your|the)\s+([a-z]+)\s+credit\s+card'
    credit_card_match = re.search(credit_card_pattern, sms_text_lower)
    if credit_card_match:
        result["message_type"] = "bill_payment"
        result["merchant_name"] = credit_card_match.group(1).upper()
        return result
    
    # Check for subscription services
    subscription_keywords = [
        "netflix", "prime", "spotify", "disney", "hotstar", "zee5", "sonyliv", 
        "autopay", "auto pay", "mandate", "recurring", "subscription", "renewal"
    ]
    
    if any(keyword in sms_text_lower for keyword in subscription_keywords):
        result["message_type"] = "subscription"
        # Try to extract the merchant name
        merchant_match = re.search(r'(?:for|to|at)\s+([A-Za-z0-9\s&\-\']+?)(?:\s+(?:subscription|renewal|auto|mandate|\.|$))', sms_text)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
            # Clean up account information
            merchant = re.sub(r'\s*(?:A/C|ACC(?:OUNT)?|XX?\d+)\s*', '', merchant)
            result["merchant_name"] = f"SUBSCRIPTION_{merchant}"
    
    # Check for financial institutions
    financial_keywords = [
        "loan", "finance", "insurance", "bank", "credit", "lending", "mutual fund",
        "investment", "stock", "share", "broker", "demat", "pension", "provident fund"
    ]
    
    if any(keyword in sms_text_lower for keyword in financial_keywords):
        result["message_type"] = "financial"
        # Try to extract the institution name
        institution_match = re.search(r'(?:for|to|at)\s+([A-Za-z0-9\s&\-\']+?)(?:\s+(?:loan|insurance|premium|emi|\.|$))', sms_text)
        if institution_match:
            institution = institution_match.group(1).strip()
            # Clean up account information
            institution = re.sub(r'\s*(?:A/C|ACC(?:OUNT)?|XX?\d+)\s*', '', institution)
            result["merchant_name"] = f"FINANCIAL_{institution}"
    
    # Extract amount
    amount_match = re.search(r'(?:rs\.?|inr|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)', sms_text_lower)
    if amount_match:
        result["amount"] = float(amount_match.group(1).replace(',', ''))
    
    # Extract merchant name if not already set
    if "merchant_name" not in result:
        # Try different patterns for merchant name extraction
        patterns = [
            r'(?:at|to|with|from)\s+([A-Za-z0-9\s&\-\']+?)(?:\s+on|\s+for|\s+via|\s+successful|\s+completed|\.|$)',
            r'(?:for|to|at)\s+([A-Za-z0-9\s&\-\']+?)(?:\s+(?:payment|bill|emi|premium|\.|$))',
            r'(?:payment|bill|emi|premium)\s+(?:to|for|at)\s+([A-Za-z0-9\s&\-\']+?)(?:\s+(?:has|been|is|\.|$))'
        ]
        
        for pattern in patterns:
            merchant_match = re.search(pattern, sms_text)
            if merchant_match:
                merchant = merchant_match.group(1).strip()
                # Clean up account information
                merchant = re.sub(r'\s*(?:A/C|ACC(?:OUNT)?|XX?\d+)\s*', '', merchant)
                # Remove any trailing words like "has been", "is", etc.
                merchant = re.sub(r'\s+(?:has|been|is|successful|completed|processed)$', '', merchant)
                # Remove "your account" if present
                merchant = re.sub(r'^your\s+account\s*', '', merchant, flags=re.IGNORECASE)
                result["merchant_name"] = merchant
                break
    
    # Extract account number
    account_match = re.search(r'(?:a/c|acc(?:ount)?)[^0-9]*(\d+)', sms_text_lower)
    if account_match:
        result["account_masked"] = account_match.group(1)
    
    # Extract date
    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', sms_text)
    if date_match:
        result["date"] = date_match.group(1)
    
    # Extract balance
    balance_match = re.search(r'(?:balance|bal)[^0-9]*(?:rs\.?|inr|₹)[\s]*(\d+(?:,\d+)*(?:\.\d+)?)', sms_text_lower)
    if balance_match:
        result["available_balance"] = float(balance_match.group(1).replace(',', ''))
    
    # Determine message type based on content
    if "block upi" in sms_text_lower or "not you?" in sms_text_lower:
        result["message_type"] = "security_alert"
        result["is_suspicious"] = True
    elif "otp" in sms_text_lower or "password" in sms_text_lower:
        result["message_type"] = "otp"
    elif any(promo in sms_text_lower for promo in ["offer", "discount", "cashback", "promotion"]):
        result["message_type"] = "promotional"
    elif "amount" in result:
        # Default to transaction if we found an amount
        result["message_type"] = "transaction"
    else:
        result["message_type"] = "other"
    
    return result

# Get logger
logger = get_logger(__name__)

# Configure Gemini API with the key
try:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel('gemini-1.5-pro')
    logger.info("Gemini API configured successfully with model: gemini-1.5-pro")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    GEMINI_MODEL = None

# Load data from CSV files
MERCHANTS = []
MERCHANT_SHORT = []
BANKS = []
TRANSACTION_INDICATORS = []
FRAUD_INDICATORS = []

# Define data paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
MERCHANT_FILE = os.path.join(DATA_DIR, "merchants.csv")
MERCHANT_SHORT_FILE = os.path.join(DATA_DIR, "merchant_short.csv")
BANK_FILE = os.path.join(DATA_DIR, "banks.csv")
TRANSACTION_TYPES_FILE = os.path.join(DATA_DIR, "transaction_types.csv")
TRANSACTION_INDICATORS_FILE = os.path.join(DATA_DIR, "transaction_indicator_keywords.csv")
FRAUD_FILE = os.path.join(DATA_DIR, "fraud.csv")

# Define additional data paths for new message types
TRANSACTION_STATUS_FILE = os.path.join(DATA_DIR, "transaction_status_keywords.csv")
BALANCE_UPDATE_FILE = os.path.join(DATA_DIR, "balance_update_keywords.csv")
BILL_STATEMENT_FILE = os.path.join(DATA_DIR, "bill_statement_keywords.csv")
EMI_KEYWORDS_FILE = os.path.join(DATA_DIR, "loan_emi_keywords.csv")

# Add new global variables for additional keywords
TRANSACTION_STATUS_KEYWORDS = []
BALANCE_UPDATE_KEYWORDS = []
BILL_STATEMENT_KEYWORDS = []
EMI_KEYWORDS = []
TRANSACTION_TYPES = []

def load_data_from_csv():
    """Load data from CSV files"""
    global MERCHANTS, MERCHANT_SHORT, BANKS, TRANSACTION_INDICATORS, FRAUD_INDICATORS
    global TRANSACTION_STATUS_KEYWORDS, BALANCE_UPDATE_KEYWORDS, BILL_STATEMENT_KEYWORDS, EMI_KEYWORDS, TRANSACTION_TYPES
    
    try:
        # Load merchant data
        if os.path.exists(MERCHANT_FILE):
            with open(MERCHANT_FILE, 'r') as f:
                reader = csv.DictReader(f)
                MERCHANTS = list(reader)
            logger.info(f"Loaded {len(MERCHANTS)} merchants from main file")
        
        # Load merchant short data
        if os.path.exists(MERCHANT_SHORT_FILE):
            with open(MERCHANT_SHORT_FILE, 'r') as f:
                reader = csv.DictReader(f)
                MERCHANT_SHORT = list(reader)
            logger.info(f"Loaded additional merchants from short file")
        
        # Load bank data
        if os.path.exists(BANK_FILE):
            with open(BANK_FILE, 'r') as f:
                reader = csv.DictReader(f)
                BANKS = list(reader)
            logger.info(f"Loaded {len(BANKS)} banks")
        
        # Load transaction types
        if os.path.exists(TRANSACTION_TYPES_FILE):
            with open(TRANSACTION_TYPES_FILE, 'r') as f:
                reader = csv.DictReader(f)
                TRANSACTION_TYPES = []
                for row in reader:
                    if 'transaction_type' in row:
                        TRANSACTION_TYPES.append(row['transaction_type'])
            logger.info(f"Loaded {len(TRANSACTION_TYPES)} transaction types")
        
        # Load transaction indicators
        if os.path.exists(TRANSACTION_INDICATORS_FILE):
            with open(TRANSACTION_INDICATORS_FILE, 'r') as f:
                TRANSACTION_INDICATORS = [line.strip() for line in f.readlines() if line.strip()]
            logger.info(f"Loaded {len(TRANSACTION_INDICATORS)} transaction indicators")
        
        # Load fraud indicators
        if os.path.exists(FRAUD_FILE):
            with open(FRAUD_FILE, 'r') as f:
                FRAUD_INDICATORS = [line.strip() for line in f.readlines() if line.strip()]
            logger.info(f"Loaded {len(FRAUD_INDICATORS)} fraud indicators")
        
        # Load transaction status keywords (failed, declined, etc.)
        if os.path.exists(TRANSACTION_STATUS_FILE):
            with open(TRANSACTION_STATUS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                TRANSACTION_STATUS_KEYWORDS = []
                for row in reader:
                    if 'keyword' in row:
                        TRANSACTION_STATUS_KEYWORDS.append(row['keyword'])
            logger.info(f"Loaded {len(TRANSACTION_STATUS_KEYWORDS)} transaction status keywords")
        else:
            # Create default keywords if file doesn't exist
            TRANSACTION_STATUS_KEYWORDS = ["failed", "unsuccessful", "declined", "rejected", "not processed", 
                                         "transaction failed", "payment failed", "insufficient balance", 
                                         "could not process", "not successful", "cancelled"]
            logger.info(f"Using default transaction status keywords")
        
        # Load balance update keywords
        if os.path.exists(BALANCE_UPDATE_FILE):
            with open(BALANCE_UPDATE_FILE, 'r') as f:
                reader = csv.DictReader(f)
                BALANCE_UPDATE_KEYWORDS = []
                for row in reader:
                    if 'keyword' in row:
                        BALANCE_UPDATE_KEYWORDS.append(row['keyword'])
            logger.info(f"Loaded {len(BALANCE_UPDATE_KEYWORDS)} balance update keywords")
        else:
            # Create default keywords if file doesn't exist
            BALANCE_UPDATE_KEYWORDS = ["balance is", "available balance", "current balance", "closing balance", 
                                     "bal:", "bal is", "a/c bal", "account balance", "as of", 
                                     "updated balance", "balance statement"]
            logger.info(f"Using default balance update keywords")
        
        # Load bill statement keywords
        if os.path.exists(BILL_STATEMENT_FILE):
            with open(BILL_STATEMENT_FILE, 'r') as f:
                reader = csv.DictReader(f)
                BILL_STATEMENT_KEYWORDS = []
                for row in reader:
                    if 'keyword' in row:
                        BILL_STATEMENT_KEYWORDS.append(row['keyword'])
            logger.info(f"Loaded {len(BILL_STATEMENT_KEYWORDS)} bill statement keywords")
        else:
            # Create default keywords if file doesn't exist
            BILL_STATEMENT_KEYWORDS = ["bill of", "bill amount", "credit card bill", "card bill", "bill generated", 
                                     "bill is ready", "bill statement", "bill due", "due on", "minimum due", 
                                     "min due", "payment due", "last date", "due date"]
            logger.info(f"Using default bill statement keywords")
        
        # Load EMI keywords
        if os.path.exists(EMI_KEYWORDS_FILE):
            with open(EMI_KEYWORDS_FILE, 'r') as f:
                reader = csv.DictReader(f)
                EMI_KEYWORDS = []
                for row in reader:
                    if 'keyword' in row:
                        EMI_KEYWORDS.append(row['keyword'])
            logger.info(f"Loaded {len(EMI_KEYWORDS)} EMI keywords")
        else:
            # Create default keywords if file doesn't exist
            EMI_KEYWORDS = ["emi", "equated monthly installment", "loan emi", "emi due", "auto-debit", 
                          "auto debit", "loan payment", "will be debited", "pre-emi", "loan installment", 
                          "towards loan"]
            logger.info(f"Using default EMI keywords")
            
    except Exception as e:
        logger.error(f"Error loading data from CSV files: {e}")

# Load data when module is imported
load_data_from_csv()

def _save_parsed_data(parsed_data: Dict[str, Any]) -> None:
    """Save parsed SMS data to a JSON file."""
    try:
        # Create the file if it doesn't exist
        if not os.path.exists(PARSED_SMS_FILE):
            with open(PARSED_SMS_FILE, 'w') as f:
                json.dump([], f)
        
        # Read existing data
        with open(PARSED_SMS_FILE, 'r') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
        
        # Add timestamp to parsed data
        parsed_data['parsed_timestamp'] = datetime.datetime.now().isoformat()
        
        # Append new data
        existing_data.append(parsed_data)
        
        # Write back to file
        with open(PARSED_SMS_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
            
        logger.info(f"Successfully saved parsed data to {PARSED_SMS_FILE}")
    except Exception as e:
        logger.error(f"Error saving parsed data: {str(e)}")

def parse_sms(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """Parse SMS text using Gemini API."""
    try:
        # Configure Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Generate prompt
        prompt = f"""Parse this SMS and return a JSON object with the following fields:
        - message_type: transaction, balance_update, bill_payment, transfer, subscription, financial, security_alert, or unknown
        - transaction_type: debit, credit, refund, transfer, bill, emi, or unknown
        - amount: numeric value or null
        - merchant_name: string or null
        - account_masked: string or null
        - date: YYYY-MM-DD format or null
        - available_balance: numeric value or null
        - description: string or null
        - is_fraud: boolean
        - fraud_indicators: list of strings or empty list
        - risk_score: numeric value between 0 and 1
        
        SMS: {sms_text}
        Sender: {sender if sender else 'Unknown'}
        
        Return only the JSON object, no other text."""
        
        # Get response from Gemini API
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from response
        parsed_data = _extract_json_from_response(response_text)
        
        # If JSON extraction failed, use fallback parser
        if not parsed_data:
            logger.warning("Failed to extract JSON from API response, using fallback parser")
            parsed_data = _fallback_regex_parse(sms_text, sender)
        
        # Enhance parsing with CSV data
        parsed_data = _enhance_parsing_with_csv_data(parsed_data, sms_text)
        
        # Save parsed data to JSON file
        _save_parsed_data(parsed_data)
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing SMS: {str(e)}")
        # Use fallback parser in case of error
        parsed_data = _fallback_regex_parse(sms_text, sender)
        # Save parsed data even if it's from fallback
        _save_parsed_data(parsed_data)
        return parsed_data

def _enhance_parsing_with_csv_data(result: Dict[str, Any], sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """
    Enhance the parsing results with data from CSV files
    
    Args:
        result: The parsed result from Gemini API
        sms_text: The original SMS text
        sender: The SMS sender (optional)
        
    Returns:
        Enhanced parsing result
    """
    # Convert sms_text to lowercase for better matching
    sms_text_lower = sms_text.lower()
    
    # Check for transaction status keywords
    if not result.get("message_type") or result.get("message_type") == "transaction":
        for keyword in TRANSACTION_STATUS_KEYWORDS:
            if keyword.lower() in sms_text_lower:
                result["transaction_status"] = "failed"
                if not result.get("message_type"):
                    result["message_type"] = "failed_transaction"
                break
    
    # Check for balance update keywords
    if not result.get("message_type"):
        for keyword in BALANCE_UPDATE_KEYWORDS:
            if keyword.lower() in sms_text_lower:
                result["message_type"] = "balance_update"
                
                # Try to extract balance amount if not already extracted
                if not result.get("available_balance"):
                    balance_pattern = r'(?:balance|bal)[^\d]*?(?:(?:rs|inr|₹)[.\s]*?)?(\d+(?:[,.]\d+)?)'
                    balance_match = re.search(balance_pattern, sms_text_lower, re.IGNORECASE)
                    if balance_match:
                        result["available_balance"] = balance_match.group(1).replace(',', '')
                
                break
    
    # Check for bill statement keywords
    if not result.get("message_type"):
        for keyword in BILL_STATEMENT_KEYWORDS:
            if keyword.lower() in sms_text_lower:
                result["message_type"] = "bill_statement"
                
                # Try to extract bill amount if not already extracted
                if not result.get("bill_amount"):
                    bill_pattern = r'(?:bill|due|payment)[^\d]*?(?:(?:rs|inr|₹)[.\s]*?)?(\d+(?:[,.]\d+)?)'
                    bill_match = re.search(bill_pattern, sms_text_lower, re.IGNORECASE)
                    if bill_match:
                        result["bill_amount"] = bill_match.group(1).replace(',', '')
                
                # Try to extract due date if not already extracted
                if not result.get("due_date"):
                    date_pattern = r'(?:due|by|on)[^\d]*?(\d{1,2}(?:\/|-)\d{1,2}(?:\/|-)\d{2,4}|\d{1,2}(?:\s|-)[a-z]{3}(?:\s|-)\d{2,4})'
                    date_match = re.search(date_pattern, sms_text_lower, re.IGNORECASE)
                    if date_match:
                        result["due_date"] = date_match.group(1)
                
                break
    
    # Check for EMI keywords
    if not result.get("message_type"):
        for keyword in EMI_KEYWORDS:
            if keyword.lower() in sms_text_lower:
                result["message_type"] = "loan_emi"
                result["is_emi"] = True
                
                # Try to extract amount if not already extracted
                if not result.get("amount"):
                    amount_pattern = r'(?:amount|emi|payment|installment)[^\d]*?(?:(?:rs|inr|₹)[.\s]*?)?(\d+(?:[,.]\d+)?)'
                    amount_match = re.search(amount_pattern, sms_text_lower, re.IGNORECASE)
                    if amount_match:
                        result["amount"] = amount_match.group(1).replace(',', '')
                
                break
    
    # Check for transaction type if not identified
    if not result.get("transaction_type") and result.get("message_type") in ["transaction", None]:
        # Set default type to "debit" if amount exists but type is not identified
        if result.get("amount"):
            result["transaction_type"] = "debit"
            
        # Check for type based on keywords
        for t_type in TRANSACTION_TYPES:
            if t_type.lower() in sms_text_lower:
                result["transaction_type"] = t_type.lower()
                break
                
        # Check for credit-specific patterns
        credit_patterns = [
            r'credited',
            r'received',
            r'added',
            r'deposited',
            r'refund',
            r'cashback',
            r'credited to',
            r'sent you',
        ]
        
        for pattern in credit_patterns:
            if re.search(pattern, sms_text_lower, re.IGNORECASE):
                result["transaction_type"] = "credit"
                break
    
    # Try to identify merchant from merchant list if not already identified
    if not result.get("merchant_name") and result.get("message_type") in ["transaction", "failed_transaction", None]:
        for merchant in MERCHANTS:
            merchant_name = merchant.get("merchant_name", "").lower()
            if merchant_name and merchant_name in sms_text_lower:
                result["merchant_name"] = merchant.get("merchant_name")
                if not result.get("category") and merchant.get("category"):
                    result["category"] = merchant.get("category")
                break
    
    # Try to identify bank from bank list
    if not result.get("bank_name"):
        for bank in BANKS:
            # Try full name first
            bank_name = bank.get("bank_name", "").lower()
            if bank_name and bank_name in sms_text_lower:
                result["bank_name"] = bank.get("bank_name")
                break
                
            # Try short code
            bank_code = bank.get("short_code", "").lower()
            if bank_code and bank_code in sms_text_lower:
                result["bank_name"] = bank.get("bank_name")
                break
    
    # If message_type is still not identified, mark as transaction if it has amount
    if not result.get("message_type") and result.get("amount"):
        result["message_type"] = "transaction"
    
    # If message_type is still not identified, mark as promotional
    if not result.get("message_type"):
        result["message_type"] = "promotional"
        
        # Try to identify company name if not present
        if not result.get("company_name") and sender:
            result["company_name"] = sender
            
        # Extract offer details if not present
        if not result.get("offer_details"):
            result["offer_details"] = sms_text[:100] + ("..." if len(sms_text) > 100 else "")
    
    # Clean up the result
    # Convert amounts to float
    for field in ["amount", "available_balance", "bill_amount", "minimum_due"]:
        if field in result and result[field]:
            try:
                # Remove any currency symbols and commas
                amount_str = str(result[field])
                amount_str = re.sub(r'[^\d.]', '', amount_str)
                result[field] = float(amount_str)
            except (ValueError, TypeError):
                pass
    # Check for failed transactions
    if any(keyword in sms_text_lower for keyword in TRANSACTION_STATUS_KEYWORDS):
        result["message_type"] = "failed_transaction"
        result["transaction_status"] = "failed"
            
        # Extract failure reason if not already present
        if not result.get("failure_reason"):
            for keyword in TRANSACTION_STATUS_KEYWORDS:
                if keyword in sms_text_lower:
                    # Extract surrounding context for failure reason
                    keyword_index = sms_text_lower.find(keyword)
                    context_start = max(0, keyword_index - 20)
                    context_end = min(len(sms_text_lower), keyword_index + len(keyword) + 30)
                    failure_context = sms_text_lower[context_start:context_end]
                    result["failure_reason"] = failure_context
                    break
    
    # Check for balance updates
    elif any(keyword in sms_text_lower for keyword in BALANCE_UPDATE_KEYWORDS) and not result.get("message_type"):
        result["message_type"] = "balance_update"
        
        # Extract balance amount if not already present
        if not result.get("available_balance"):
            balance_match = re.search(r'(?:balance[^\d]*?|bal[^\d]*?)(?:rs\.?|inr|₹)?\s*([0-9,.]+)', sms_text_lower)
            if balance_match:
                try:
                    result["available_balance"] = float(balance_match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        # Extract as_of_date if not already present
        if not result.get("as_of_date"):
            date_match = re.search(r'as of\s+([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', sms_text_lower)
            if date_match:
                result["as_of_date"] = date_match.group(1)
            else:
                # Default to today's date
                result["as_of_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Check for bill statements
    elif any(keyword in sms_text_lower for keyword in BILL_STATEMENT_KEYWORDS) and not result.get("message_type"):
        result["message_type"] = "bill_statement"
        
        # Extract bill amount if not already present
        if not result.get("bill_amount"):
            bill_match = re.search(r'(?:bill|due)[^\d]*?(?:rs\.?|inr|₹)?\s*([0-9,.]+)', sms_text_lower)
            if bill_match:
                try:
                    result["bill_amount"] = float(bill_match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        # Extract minimum due if not already present
        if not result.get("minimum_due"):
            min_due_match = re.search(r'(?:min|minimum)[^\d]*?(?:rs\.?|inr|₹)?\s*([0-9,.]+)', sms_text_lower)
            if min_due_match:
                try:
                    result["minimum_due"] = float(min_due_match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        # Extract due date if not already present
        if not result.get("due_date"):
            due_date_match = re.search(r'(?:due|by)[^\d]*?([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', sms_text_lower)
            if due_date_match:
                result["due_date"] = due_date_match.group(1)
    
    # Check for EMI notifications
    elif any(keyword in sms_text_lower for keyword in EMI_KEYWORDS) and not result.get("message_type"):
        result["message_type"] = "loan_emi"
        result["is_emi"] = True
        
        # Extract loan reference if not already present
        if not result.get("loan_reference"):
            loan_ref_match = re.search(r'(?:loan|a\/c)[^\d]*?(?:[xX*]+)?([0-9]{4})', sms_text_lower)
            if loan_ref_match:
                result["loan_reference"] = loan_ref_match.group(1)
        
        # Extract due date if not already present
        if not result.get("due_date"):
            due_date_match = re.search(r'(?:on|dated|due)[^\d]*?([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', sms_text_lower)
            if due_date_match:
                result["due_date"] = due_date_match.group(1)
            else:
                # Check for month name based dates
                month_match = re.search(r'(?:on|dated|due)[^\d]*?([0-9]{1,2}[- ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ][0-9]{2,4})', sms_text_lower, re.IGNORECASE)
                if month_match:
                    result["due_date"] = month_match.group(1)
    
    # Special case for refunds - always mark as credit
    if "refund" in sms_text_lower and result.get("transaction_type") != "credit":
        result["transaction_type"] = "credit"
        
        # Update description to reflect refund
        if result.get("merchant_name"):
            result["description"] = f"Refund from {result['merchant_name']}"
        elif result.get("amount"):
            result["description"] = f"Refund of {result['amount']}"
        else:
            result["description"] = "Refund processed"
    
    # Check if transaction type is detected for regular transactions
    elif result.get("transaction_type") is None and not result.get("message_type"):
        # Try to identify transaction type from transaction indicators
        for indicator in TRANSACTION_INDICATORS:
            if indicator.lower() in sms_text_lower:
                if any(debit_word in indicator.lower() for debit_word in ["debit", "spent", "paid", "payment", "purchase"]):
                    result["transaction_type"] = "debit"
                    break
                elif any(credit_word in indicator.lower() for credit_word in ["credit", "received", "refund", "cashback"]):
                    result["transaction_type"] = "credit"
                    break
    
    # Try to identify merchant from the merchant list if not already present or clear
    if (not result.get("merchant_name") or result.get("merchant_name") == "N/A") and not result.get("message_type"):
        for merchant in MERCHANTS:
            merchant_name = merchant.get("merchant_name", "").lower()
            if merchant_name and merchant_name in sms_text_lower:
                result["merchant_name"] = merchant.get("merchant_name")
                result["category"] = merchant.get("category", "")
                break
            # Also check abbreviation
            merchant_abbr = merchant.get("merchant_abbreviation", "").lower()
            if merchant_abbr and len(merchant_abbr) >= 3 and merchant_abbr in sms_text_lower:
                result["merchant_name"] = merchant.get("merchant_name")
                result["category"] = merchant.get("category", "")
                break
    
    # Identify bank from sender ID or message text
    if sender:
        for bank in BANKS:
            sender_ids = bank.get("typical_sender_ids", "").split(",")
            for sender_id in sender_ids:
                if sender_id.strip().lower() in sender.lower():
                    result["bank_name"] = bank.get("bank_name")
                    break
    
    if not result.get("bank_name"):
        for bank in BANKS:
            bank_name = bank.get("bank_name", "").lower()
            if bank_name and bank_name in sms_text_lower:
                result["bank_name"] = bank.get("bank_name")
                break
    
    # Check for fraud indicators
    fraud_indicators_found = []
    for indicator in FRAUD_INDICATORS:
        if indicator.lower() in sms_text_lower:
            fraud_indicators_found.append(indicator)
    
    if fraud_indicators_found:
        result["suspicious_indicators"] = fraud_indicators_found
        result["is_suspicious"] = True
        result["risk_level"] = "medium" if len(fraud_indicators_found) > 2 else "low"
    
    # Special case for money transfers with "To [Recipient]" format
    to_recipient_match = re.search(r'(?:to|To)\s+([A-Za-z0-9][A-Za-z0-9\s&.,\'-]+)(?:\s+on|\s+for|\s+via|\s+at|\s+using|\s+with|\s+dated|\s+has|\s+ref|\.|$)', sms_text)
    if to_recipient_match and not result.get("merchant_name"):
        potential_merchant = to_recipient_match.group(1).strip()
        # Verify it's not just a phone number or other non-merchant text
        if (len(potential_merchant.split()) > 1 or len(potential_merchant) > 5) and not re.match(r'^\d+$', potential_merchant):
            result["merchant_name"] = potential_merchant
            
            # Update description if this is a debit transaction (payment to recipient)
            if result.get("transaction_type") == "debit":
                result["description"] = f"Payment to {potential_merchant}"
    
    # Check for promotional SMS
    promotional_patterns = [
        r'(?:offer|discount|off|sale|promo|code|coupon|cashback|rewards|points)\s',
        r'limited(?:\s+time)?\s+offer',
        r'special\s+offer',
        r'exclusive\s+offer',
        r'get\s+\d+%\s+off',
        r'save\s+\d+%',
        r'buy\s+\d+\s+get\s+\d+',
        r'use\s+code',
        r'valid\s+(?:till|until)',
        r'hurry',
        r'last\s+day',
        r'don\'t\s+miss',
        r'shop\s+now',
        r'click\s+(?:here|now)'
    ]

    if any(re.search(pattern, sms_text_lower) for pattern in promotional_patterns) and not result.get("message_type"):
        result["message_type"] = "promotional"
        
        # Try to extract company name
        if sender:
            result["company_name"] = sender
        
        # Try to extract offer details
        result["offer_details"] = sms_text[:100] + ("..." if len(sms_text) > 100 else "")
        
        # Try to extract discount percentage
        discount_match = re.search(r'(\d+)%\s+(?:off|discount|cashback)', sms_text_lower)
        if discount_match:
            result["discount_percentage"] = discount_match.group(1) + "%"
        
        # Try to extract promo code
        promo_match = re.search(r'(?:use|code|coupon)[:\s]+([A-Z0-9]+)', sms_text, re.IGNORECASE)
        if promo_match:
            result["promo_code"] = promo_match.group(1)
        
        # Try to extract validity
        validity_match = re.search(r'valid\s+(?:till|until)\s+([^\.\n]+)', sms_text_lower)
        if validity_match:
            result["valid_until"] = validity_match.group(1)
        
        return result

    return result

def _get_mock_response(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """Generate mock response for testing without API key"""
    # Create a basic structure based on text content
    sms_lower = sms_text.lower()
    
    # Check if it looks like a transaction
    is_transaction = any(word in sms_lower for word in ["debited", "credited", "spent", "received", "transaction", "payment"])
    
    # Check if it looks promotional
    is_promotional = any(word in sms_lower for word in ["offer", "discount", "sale", "cashback", "exclusive", "limited time"])
    
    # Extract some basic information with simple regex
    amount_match = re.search(r"(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)", sms_text)
    amount = 0.0
    if amount_match:
        try:
            amount = float(amount_match.group(1).replace(',', ''))
        except ValueError:
            pass
    
    # Create mock response
    if is_transaction:
        return {
            "is_banking_sms": True,
            "is_promotional": False,
            "transaction": {
                "transaction_type": "debit" if "debited" in sms_lower or "spent" in sms_lower else "credit",
                "amount": amount if amount > 0 else 1000.0,
                "merchant_name": "",
                "account_masked": "XX1234" if "xx" in sms_lower or "account" in sms_lower else "",
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "available_balance": 0.0
            },
            "metadata": {
                "parse_method": "mock",
                "raw_sms": sms_text,
                "sender": sender
            }
        }
    elif is_promotional:
        return {
            "is_banking_sms": False,
            "is_promotional": True,
            "promo_score": 0.85,
            "promotion": {
                "merchant": "",
                "offer": "",
                "valid_until": ""
            },
            "metadata": {
                "parse_method": "mock",
                "raw_sms": sms_text,
                "sender": sender
            }
        }
    else:
        return {
            "is_banking_sms": False,
            "is_promotional": False,
            "category": "Uncategorized",
            "metadata": {
                "parse_method": "mock",
                "raw_sms": sms_text,
                "sender": sender
            }
        }

def detect_transaction_type(sms_text: str) -> str:
    """Detect transaction type based on keywords in SMS"""
    text_lower = sms_text.lower()
    
    # Check for bill payment patterns first
    if (re.search(r'(?:credit\s+card|card)\s+bill\s+(?:payment|due)', text_lower) or
        re.search(r'bill\s+(?:payment|due)', text_lower) or
        re.search(r'(?:electricity|water|gas|utility)\s+bill', text_lower)):
        return "bill"
    
    # Check for credit card purchase patterns - these are always debit transactions
    if re.search(r'(?:credit\s+card|card)\s+was\s+used\s+for', text_lower) or \
       re.search(r'(?:credit\s+card|card)\s+has\s+been\s+used', text_lower) or \
       re.search(r'used\s+(?:your|for)\s+(?:credit\s+card|card)', text_lower):
        return "debit"
    
    if any(word in text_lower for word in ["debited", "spent", "paid", "payment", "debit", "deducted", "purchase", "shopping"]):
        return "debit"
    elif any(word in text_lower for word in ["credited", "received", "credit", "added", "deposit"]):
        return "credit"
    elif any(word in text_lower for word in ["refund", "refunded", "returned", "cashback"]):
        return "refund"
    elif any(word in text_lower for word in ["transfer", "sent", "transferred"]):
        return "transfer"
    elif any(word in text_lower for word in ["emi", "installment", "loan"]):
        return "emi"
    else:
        return "unknown"

def _detect_message_type(sms_text):
    """Detect the type of message (transfer, bill_payment, transaction)."""
    sms_text = sms_text.upper()
    
    # Check for transfers first
    transfer_patterns = [
        r'NEFT\s+(?:TRANSFER|CREDIT|DEBIT)',
        r'IMPS\s+(?:TRANSFER|CREDIT|DEBIT)',
        r'UPI\s+(?:TRANSFER|CREDIT|DEBIT)',
        r'(?:TRANSFER|TRANSFERRED)\s+(?:TO|FROM)',
    ]
    
    for pattern in transfer_patterns:
        if re.search(pattern, sms_text):
            return "transfer"
    
    # Check for bill payments
    bill_patterns = [
        r'(?:CREDIT\s+CARD|LOAN|INSURANCE)\s+(?:BILL|PAYMENT|DUE)',
        r'ELECTRICITY\s+BILL',
        r'(?:BILL|PAYMENT)\s+(?:DUE|RECEIVED)',
    ]
    
    for pattern in bill_patterns:
        if re.search(pattern, sms_text):
            return "bill_payment"
    
    return "transaction"

def _extract_merchant_name(sms_text):
    """Extract merchant name from SMS text."""
    sms_text = sms_text.upper()
    
    # Check for bank transfers first
    transfer_patterns = [
        r'NEFT\s+(?:TRANSFER|CREDIT|DEBIT)',
        r'IMPS\s+(?:TRANSFER|CREDIT|DEBIT)',
        r'UPI\s+(?:TRANSFER|CREDIT|DEBIT)',
    ]
    
    for pattern in transfer_patterns:
        if re.search(pattern, sms_text):
            return "BANK_TRANSFER"
    
    # Check for credit card bills
    credit_card_pattern = r'(?:YOUR|THE)\s+([A-Z]+)\s+CREDIT\s+CARD'
    match = re.search(credit_card_pattern, sms_text)
    if match:
        return match.group(1)
    
    # Check for recurring payments and subscriptions
    subscription_keywords = [
        "NETFLIX", "PRIME", "SPOTIFY", "DISNEY", "HOTSTAR", "ZEE5", "SONYLIV", 
        "AUTOPAY", "AUTO PAY", "MANDATE", "RECURRING", "SUBSCRIPTION", "RENEWAL"
    ]
    
    # Check if it's a recurring payment
    if any(keyword in sms_text for keyword in subscription_keywords):
        # Try to extract the merchant name
        merchant_pattern = r'(?:AT|TO|WITH|FROM)\s+([A-Z0-9\s&\-\']+?)(?:\s+(?:ON|FOR|VIA|HAS|BEEN|COMPLETED|SUCCESSFUL|\.|$))'
        match = re.search(merchant_pattern, sms_text)
        if match:
            merchant = match.group(1).strip()
            # Clean up account information
            merchant = re.sub(r'\s*(?:A/C|ACC(?:OUNT)?|XX?\d+)\s*', '', merchant)
            return f"SUBSCRIPTION_{merchant}"
    
    # Check for financial institutions (loans, insurance, etc.)
    financial_institutions = [
        "LOAN", "FINANCE", "INSURANCE", "BANK", "CREDIT", "LENDING", "MUTUAL FUND",
        "INVESTMENT", "STOCK", "SHARE", "BROKER", "DEMAT", "PENSION", "PROVIDENT FUND"
    ]
    
    # Check if it's a financial institution payment
    if any(keyword in sms_text for keyword in financial_institutions):
        # Try to extract the institution name
        institution_pattern = r'(?:AT|TO|WITH|FROM)\s+([A-Z0-9\s&\-\']+?)(?:\s+(?:ON|FOR|VIA|HAS|BEEN|COMPLETED|SUCCESSFUL|\.|$))'
        match = re.search(institution_pattern, sms_text)
        if match:
            institution = match.group(1).strip()
            # Clean up account information
            institution = re.sub(r'\s*(?:A/C|ACC(?:OUNT)?|XX?\d+)\s*', '', institution)
            return f"FINANCIAL_{institution}"
    
    # General merchant pattern
    merchant_pattern = r'(?:AT|TO|WITH|FROM)\s+([A-Z0-9\s&\-\']+?)(?:\s+(?:ON|FOR|VIA|HAS|BEEN|COMPLETED|SUCCESSFUL|\.|$))'
    match = re.search(merchant_pattern, sms_text)
    if match:
        merchant = match.group(1).strip()
        # Clean up account information
        merchant = re.sub(r'\s*(?:A/C|ACC(?:OUNT)?|XX?\d+)\s*', '', merchant)
        return merchant
    
    return "Unknown" 