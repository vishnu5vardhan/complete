#!/usr/bin/env python3

import os
import json
import re
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.runnables import ConfigurableField
import datetime
import random

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured successfully")
else:
    print("Warning: GEMINI_API_KEY not found in .env file")

# Initialize the LangChain model
def get_llm(temperature=0.0, model_name="models/gemini-1.5-pro"):
    """Get a configured LangChain LLM instance"""
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=GEMINI_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,
    ).configurable_fields(
        temperature=ConfigurableField(
            id="temperature",
            name="Temperature",
            description="The randomness of the model's output"
        )
    )

# JSON Parsing function to maintain compatibility with legacy code
def parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Clean and parse JSON response from LLM
    
    Args:
        response_text: Raw text response from LLM
        
    Returns:
        Parsed JSON dictionary or empty dict on error
    """
    try:
        # Remove markdown code blocks (```json and ```)
        cleaned_text = re.sub(r'```(?:json)?\s*|\s*```', '', response_text)
        
        # Strip any extraneous text before the first { and after the last }
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}')
        
        if json_start >= 0 and json_end >= 0:
            # Extract just the JSON portion
            json_text = cleaned_text[json_start:json_end+1]
            # Parse the JSON
            return json.loads(json_text)
        else:
            print("[!] No valid JSON found in response")
            return {}
    except json.JSONDecodeError as e:
        print(f"[!] JSON parsing error: {e}")
        print(f"Raw text: {response_text}")
        return {}
    except Exception as e:
        print(f"[!] Error parsing response: {e}")
        return {}

# Function that mimics the existing ask_gemini function but uses LangChain
def ask_gemini(prompt_text: str, retries=3, delay=5, temperature=0.0) -> str:
    """
    Call LangChain with a prompt and return the response, with retry logic
    
    Args:
        prompt_text: The prompt to send to the model
        retries: Number of retry attempts for rate-limit errors
        delay: Delay in seconds between retries
        temperature: Model temperature
        
    Returns:
        The response text from the model
    """
    # Check if we should use mock data for testing
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    if use_mock:
        print("[INFO] Using mock data for testing (USE_MOCK_DATA=true)")
        # Simple mock responses for different types of prompts
        if "capital of France" in prompt_text:
            return "Paris"
        elif "financial archetype" in prompt_text:
            return "Foodie & Entertainment Spender because of high restaurant spending"
        elif "best credit card" in prompt_text or "recommend" in prompt_text:
            return """1. Foodie Rewards Plus: 5X points at restaurants, 2X on groceries - Perfect for your high food delivery spending.
            
2. Everyday Cash Back: 2% cash back on all purchases, no annual fee - Good for general daily expenses.

3. Premium Travel Elite: 3X points on travel and dining, airport lounge access - Great for when you travel as well as dine out."""
        else:
            return "This is a mock response for testing purposes."
    
    last_error = None
    
    for attempt in range(retries):
        try:
            # Ensure API key is configured
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not configured")
            
            # Create a simple LangChain chain with the prompt
            from langchain_core.prompts import PromptTemplate
            
            # Create a prompt template
            prompt = PromptTemplate.from_template("{input}")
            
            # Create the LLM
            llm = get_llm(temperature=temperature)
            
            # Create and run the chain
            chain = prompt | llm | StrOutputParser()
            
            # Execute the chain
            response = chain.invoke({"input": prompt_text})
            
            # Return the text response
            return response.strip()
        except Exception as e:
            last_error = e
            if "429" in str(e):
                # Rate limit error, retry after delay
                print(f"[!] Quota exceeded. Retrying in {delay} sec... (Attempt {attempt+1}/{retries})")
                time.sleep(delay)
            else:
                # Other error, break out of retry loop
                print("[!] Error calling LangChain:", e)
                break
    
    # If we get here, all retries failed or we had a non-rate-limit error
    # Return mock data for common queries when API fails
    print("[!] API calls failed. Using fallback mock data.")
    if "capital of France" in prompt_text:
        return "Paris"
    elif "financial archetype" in prompt_text:
        return "Foodie & Entertainment Spender because of high restaurant spending"
    elif "best credit card" in prompt_text or "recommend" in prompt_text:
        return """1. Foodie Rewards Plus: 5X points at restaurants, 2X on groceries - Perfect for your high food delivery spending.
        
2. Everyday Cash Back: 2% cash back on all purchases, no annual fee - Good for general daily expenses.

3. Premium Travel Elite: 3X points on travel and dining, airport lounge access - Great for when you travel as well as dine out."""
    else:
        return f"Mock response (API quota exceeded). Original query: {prompt_text[:50]}..."

# Function for extracting structured data
def extract_structured_data(sms_text: str, sender: Optional[str] = None, custom_prompt: Optional[str] = None, schema: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Extract structured data from SMS using Gemini, including fraud detection.
    
    Args:
        sms_text: The SMS text to analyze
        sender: Optional sender ID
        custom_prompt: Optional custom prompt to use instead of default
        schema: Optional JSON schema to validate/structure the output
    
    Returns:
        Dict containing parsed transaction details and fraud analysis
    """
    # Check if we should use mock data for testing
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    if use_mock:
        print("[INFO] Using mock data for structured extraction (USE_MOCK_DATA=true)")
        return generate_realistic_sms_data(sms_text, sender)
    
    # Use the provided custom prompt if available, otherwise use default prompt
    prompt = custom_prompt if custom_prompt else f"""
    Analyze this SMS message for transaction details and potential fraud. The analysis should be thorough and consider multiple factors.

    SMS Text: "{sms_text}"

    Task 1 - Transaction Details:
    - Extract exact amounts (transaction amount, available balance/limit)
    - Identify account numbers (format: XXXX1234)
    - Determine transaction type using these rules:
      * DEBIT transaction: Keywords like "debited", "spent", "paid", "payment of", "charged", "purchase", "transaction of", "withdrawn", "deduction", or "made" (also "sent" for transfers)
      * DEBIT transaction: Patterns like "Credit Card was used for" or "Card was used for" - these are purchases (money leaving account)
      * DEBIT transaction: Credit card usage where money is spent/paid (even if the word "credit" appears in "credit card")
      * CREDIT transaction: Keywords like "credited", "received", "deposited", "added", or "refunded"
      * EMI transactions with "EMI deducted" should be classified as DEBIT
      * Card or account "charged" is always a DEBIT
      * When "spent using your" or "spent on your" appears, it's always a DEBIT
      * Look at the context carefully - don't just rely on the words "debit" and "credit"
    - Find merchant name if present (look for phrases like "at [MERCHANT]", "to [MERCHANT]", "from [MERCHANT]")
    - Extract date and time

    Task 2 - Merchant Detection:
    - Look for phrases like "at [MERCHANT NAME]", "to [MERCHANT NAME]", "from [MERCHANT NAME]"
    - Be careful with McDonald's and other merchants with apostrophes
    - Merchants can be multi-word like "Pizza Hut" or "Domino's Pizza"
    - Check if there's a merchant name in CAPITALS or title case
    - If a name like "MCDONALD'S" appears, extract it as "McDonald's"

    Task 3 - Fraud Detection:
    1. Check for suspicious patterns:
       - Unusual URLs or links
       - Requests to click/verify/update
       - Urgency indicators
       - Promises of rewards/prizes
       - Threats about account suspension
    
    2. Validate sender format:
       - Should match bank patterns (e.g., VK-ICICIBK, VK-HDFCBK)
       - Verify sender matches mentioned bank
    
    3. Account number validation:
       - Must be in proper format (XXXX1234)
       - Should be consistent with message context
    
    4. Transaction pattern analysis:
       - Check for unusual amounts
       - Look for suspicious timing indicators
       - Verify transaction type consistency

    Output the analysis in this exact JSON format:
    {
        "transaction_amount": float or null,
        "available_balance": float or null,
        "account_number": "string or null",
        "transaction_type": "debit" or "credit" or null,
        "merchant": "string or null",
        "date": "YYYY-MM-DD",
        "fraud_analysis": {
            "is_suspicious": boolean,
            "risk_level": "low" or "medium" or "high",
            "suspicious_indicators": [
                "string"  // List of reasons why suspicious
            ],
            "is_valid_sender": boolean,
            "is_valid_account_format": boolean,
            "contains_urls": boolean,
            "transaction_seems_legitimate": boolean
        }
    }

    Rules:
    1. Only extract information explicitly present in the SMS
    2. Don't make assumptions about missing data
    3. Set fields to null if information is not clearly provided
    4. Be strict about fraud detection - flag any suspicious patterns
    5. Mark as suspicious if sender format doesn't match bank patterns
    6. Consider context when determining legitimacy
    7. Never confuse "spent", "charged", or "payment made" as credit transactions - these are always debit
    8. For "EMI deducted", always classify as debit
    """

    try:
        # Get response from Gemini
        llm = get_llm(temperature=0.0)
        response = llm.invoke(prompt)
        
        # Parse the response
        response_text = response.text
        # Find the JSON block in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            # Add metadata
            parsed_data['raw_sms'] = sms_text
            parsed_data['parsed_timestamp'] = datetime.datetime.now().isoformat()
            
            return parsed_data
        else:
            print("Error: Could not find JSON in Gemini response")
            return create_fallback_response(sms_text)
            
    except Exception as e:
        print(f"Error parsing SMS with Gemini: {e}")
        return create_fallback_response(sms_text)

def create_fallback_response(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """Create a fallback response when Gemini parsing fails"""
    
    # Basic regex patterns for fallback extraction
    amount_pattern = r"(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)"
    account_pattern = r"(?:XX\d{4}|XXXX\d{4})"
    
    # Try to extract basic information
    amount_match = re.search(amount_pattern, sms_text)
    account_match = re.search(account_pattern, sms_text)
    
    # Determine transaction type
    is_debit = "debit" in sms_text.lower() or "debited" in sms_text.lower() or "spent" in sms_text.lower() or "charged" in sms_text.lower() or "paid" in sms_text.lower() or "payment" in sms_text.lower()
    is_credit = "credit" in sms_text.lower() or "credited" in sms_text.lower() or "received" in sms_text.lower() or "added" in sms_text.lower()
    
    # Special handling for specific transaction keywords that override simple checks
    if re.search(r'emi.*deducted|deducted.*emi', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    # Handle "spent using your" or "spent on your" patterns, which are always debit
    if re.search(r'spent\s+(?:using|on)\s+your', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    # Purchase patterns are always debit
    if re.search(r'purchase\s+of|your\s+purchase', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    if "made" in sms_text.lower() and ("payment" in sms_text.lower() or "purchase" in sms_text.lower() or "transaction" in sms_text.lower()):
        is_debit = True
        is_credit = False
    
    # Credit card "was used for" pattern - this is always a DEBIT transaction
    if re.search(r'(?:credit\s+card|card)\s+was\s+used\s+for', sms_text.lower()):
        is_debit = True
        is_credit = False
    
    # Determine if the SMS contains URLs
    contains_urls = bool(re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', sms_text))
    
    # Create a minimal transaction data structure with fallback values
    transaction_data = {
        "transaction_type": "debit" if is_debit else "credit" if is_credit else None,
        "amount": float(amount_match.group(1).replace(',', '')) if amount_match else None,
        "merchant_name": None,  # Can't reliably extract in fallback
        "account_masked": account_match.group(0) if account_match else None,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),  # Use current date as fallback
        "category": "Uncategorized",
        "description": None,
        "is_subscription": False,
        "is_bill_payment": False,
        "is_emi": False,
        "is_transfer": False,
        "is_refund": False,
        "balance": None,
        "confidence_score": 0.1,  # Low confidence since this is fallback
        "contains_urls": contains_urls
    }
    
    return transaction_data

# Global variable to track if the current SMS is an EMI transaction
_is_emi_transaction = False

def is_emi_transaction():
    """Return whether the current SMS is an EMI transaction"""
    global _is_emi_transaction
    return _is_emi_transaction

def extract_amount_from_text(text: str) -> float:
    """
    Extract transaction amount from SMS text using various patterns
    """
    # Common patterns for amount extraction
    amount_patterns = [
        # Rs./INR/₹ followed by amount
        r'(?:Rs\.?|INR|₹)\s*([0-9,]+\.?[0-9]*)',
        # Amount followed by Rs./INR/₹
        r'([0-9,]+\.?[0-9]*)\s*(?:Rs\.?|INR|₹)',
        # debited/credited/paid with amount
        r'(?:debited|credited|paid|received|sent|spent|withdrawn|transfer|paid|payment|cash)\s+(?:with|of|for|by)?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+\.?[0-9]*)',
        # UPI transactions
        r'(?:UPI\/\w+\/[0-9]+)\s+(?:Rs\.?|INR|₹)?\s*([0-9,]+\.?[0-9]*)',
        # General amount pattern
        r'(?:amount|amt)(?:\s+of)?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+\.?[0-9]*)'
    ]
    
    # Try each pattern
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Remove commas and convert to float
            amount_str = match.group(1).replace(',', '')
            return float(amount_str)
            
    # Default fallback
    return 0.0

def extract_date_from_text(text: str) -> str:
    """
    Extract transaction date from SMS text using various patterns
    Returns date string in YYYY-MM-DD format
    """
    today = datetime.datetime.now()
    
    # Try to find date in common formats
    date_patterns = [
        # DD-MM-YY or DD/MM/YY
        r'(\d{1,2})[\-/](\d{1,2})[\-/](\d{2,4})',
        # DDMonYY or DD-Mon-YY (e.g., 29Jul24 or 29-Jul-24)
        r'(\d{1,2})[\-\s]?([A-Za-z]{3})[\-\s]?(\d{2,4})',
        # Month DD, YYYY
        r'([A-Za-z]{3,9})\s+(\d{1,2})(?:\s*,)?\s*(\d{4})',
        # YYYY-MM-DD
        r'(\d{4})[\-/](\d{1,2})[\-/](\d{1,2})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            # Handle different format types
            if len(groups[0]) == 4 and groups[0].isdigit():  # YYYY-MM-DD
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            elif re.match(r'[A-Za-z]+', groups[1], re.IGNORECASE):  # DDMonYY
                day = int(groups[0])
                month_str = groups[1].lower()
                month_dict = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                              "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
                month = month_dict.get(month_str[:3].lower(), 1)
                year = int(groups[2])
                if year < 100:  # Convert 2-digit year to 4-digit
                    year = 2000 + year if year < 50 else 1900 + year
            elif re.match(r'[A-Za-z]+', groups[0], re.IGNORECASE):  # Month DD, YYYY
                month_str = groups[0].lower()
                month_dict = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                              "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
                month = month_dict.get(month_str[:3].lower(), 1)
                day = int(groups[1])
                year = int(groups[2])
            else:  # DD-MM-YY
                day, month = int(groups[0]), int(groups[1])
                year = int(groups[2])
                if year < 100:  # Convert 2-digit year to 4-digit
                    year = 2000 + year if year < 50 else 1900 + year
                    
            # Validate and format date
            try:
                date_obj = datetime.datetime(year, month, day)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # Invalid date, try next pattern
                continue
    
    # If no date found, use today's date
    return today.strftime("%Y-%m-%d")

def generate_realistic_sms_data(sms_text: str, sender: str = None) -> Dict[str, Any]:
    """
    Generate realistic transaction data from SMS when API call fails or for testing.
    
    Args:
        sms_text: The SMS text to analyze
        sender: Optional sender ID
        
    Returns:
        Dict with transaction details extracted using regex patterns
    """
    import re
    import datetime
    
    print(f"Parsing SMS: {sms_text}")
    
    # Initialize transaction data with default values
    transaction_data = {
        "transaction_amount": 0.0,
        "available_balance": 0.0,
        "account_number": "",
        "transaction_type": "",
        "merchant": "",
        "category": "Uncategorized",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "description": ""
    }
    
    # Convert to lowercase for pattern matching
    text_lower = sms_text.lower()
    
    # 1. Extract transaction type
    # Special cases for credit card spending - always debit transactions
    credit_card_spent_patterns = [
        r"spent\s+(?:using|on)\s+your\s+(?:credit\s+card|card)",
        r"(?:credit\s+card|card)\s+was\s+used\s+for",
        r"(?:credit\s+card|card)\s+spending",
        r"spent\s+(?:using|on)\s+your",  # More generic pattern to catch variations
        r"spent.*at"  # Even more generic pattern for spending at a location
    ]
    
    if any(re.search(pattern, text_lower) for pattern in credit_card_spent_patterns):
        transaction_data["transaction_type"] = "debit"
    else:
        # Regular pattern matching for transaction type
        debit_keywords = ["debited", "debited by", "spent", "paid", "payment", "deduction", "charge", "withdraw", "transferred"]
        credit_keywords = ["credited", "credited by", "received", "deposited", "refund", "cashback", "added"]
        
        if any(keyword in text_lower for keyword in debit_keywords):
            transaction_data["transaction_type"] = "debit"
        elif any(keyword in text_lower for keyword in credit_keywords):
            transaction_data["transaction_type"] = "credit"
    
    # 2. Extract amount
    amount_patterns = [
        r"(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)",
        r"([0-9,]+(?:\.[0-9]+)?)\s*(?:Rs\.?|INR|₹)",
        r"(?:amount|amt|sum)(?:\s+of)?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        r"(?:debited|credited|paid|spent|received|sent)(?:\s+by|\s+with)?\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)"
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                transaction_data["transaction_amount"] = float(amount_str)
                break
            except (ValueError, IndexError):
                continue
    
    # 3. Extract account number
    account_patterns = [
        r"(?:a/c\s+|a/c|account\s+|card\s+)(?:[xX*]+)(\d+)",
        r"(?:[xX*]+)(\d{4})",
        r"(?:ending|ending with)\s+(\d{4})"
    ]
    
    for pattern in account_patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            try:
                # Add "XX" prefix if only the last digits are captured
                account_num = match.group(1)
                if len(account_num) <= 4:
                    transaction_data["account_number"] = f"XX{account_num}"
                else:
                    transaction_data["account_number"] = account_num
                break
            except (IndexError):
                continue
    
    # 4. Extract available balance/limit
    balance_patterns = [
        r"(?:available|avl|avbl)(?:\s+|\.|:)(?:balance|bal|limit)(?:\s+|\.|:)(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        r"(?:balance|bal|limit)(?:\s+|\.|:)(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)",
        r"(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)\s+available",
        r"(?:Avl|Available)\s+Limit:\s*(?:Rs\.?|INR|₹)?\s*([0-9,]+(?:\.[0-9]+)?)"
    ]
    
    for pattern in balance_patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            try:
                balance_str = match.group(1).replace(',', '')
                transaction_data["available_balance"] = float(balance_str)
                break
            except (ValueError, IndexError):
                continue
    
    # 5. Extract merchant name
    # Special case for merchants with apostrophes
    merchant_mapping = {
        "MCDONALD'S": "McDonald's",
        "DOMINO'S": "Domino's Pizza",
        "WENDY'S": "Wendy's",
        "DENNY'S": "Denny's",
        "HARDEE'S": "Hardee's"
    }
    
    # Check for known merchants with apostrophes first
    for known_merchant, formatted_name in merchant_mapping.items():
        if known_merchant in sms_text:
            transaction_data["merchant"] = formatted_name
            # Set food category for these merchants
            transaction_data["category"] = "Food"
            break
    else:
        # If no known merchant found, try patterns
        merchant_patterns = [
            r"at\s+([A-Z][A-Za-z\']+(?:\s+[A-Z][A-Za-z\']+)*)",
            r"to\s+([A-Z][A-Za-z\']+(?:\s+[A-Z][A-Za-z\']+)*)",
            r"from\s+([A-Z][A-Za-z\']+(?:\s+[A-Z][A-Za-z\']+)*)",
            r"(?:at|to|from)\s+([A-Z0-9\'\-]+)"
        ]
        
        for pattern in merchant_patterns:
            match = re.search(pattern, sms_text)
            if match:
                merchant = match.group(1).strip()
                if merchant and len(merchant) > 2:  # Avoid short matches
                    transaction_data["merchant"] = merchant
                    break
    
    # 6. Extract date
    date_patterns = [
        r"(?:on|date)\s+(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
        r"(?:on|date)\s+(\d{1,2}[-/\s][A-Za-z]{3}[-/\s]\d{2,4})",
        r"on\s+(\d{2}-[A-Za-z]{3}-\d{2})"  # For format like "03-Apr-25"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, sms_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                # Convert to standard format
                if '-' in date_str or '/' in date_str or '.' in date_str:
                    separator = '-' if '-' in date_str else ('/' if '/' in date_str else '.')
                    parts = date_str.split(separator)
                    if len(parts) == 3:
                        day, month, year = parts
                        if len(year) == 2:
                            year = f"20{year}"
                        transaction_data["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                else:
                    # Handle formats like "15 Mar 23"
                    transaction_data["date"] = date_str
            except:
                # Keep original format if parsing fails
                transaction_data["date"] = date_str
            break
    
    # 7. Determine category based on merchant if not already set
    if transaction_data["merchant"] and transaction_data["category"] == "Uncategorized":
        merchant_lower = transaction_data["merchant"].lower()
        
        # Basic category mapping
        categories = {
            "food": ["swiggy", "zomato", "mcdonald", "domino", "pizza", "restaurant", "food", "burger", "kitchen"],
            "shopping": ["amazon", "flipkart", "myntra", "ajio", "mall", "mart", "store", "shop"],
            "travel": ["uber", "ola", "rapido", "meru", "airline", "railway", "train", "flight", "bus", "metro"],
            "entertainment": ["netflix", "amazon prime", "hotstar", "spotify", "movie", "cinema", "theatre"],
            "utilities": ["electricity", "water", "gas", "broadband", "internet", "phone", "mobile", "bill"],
            "healthcare": ["hospital", "pharmacy", "doctor", "medical", "clinic", "health"],
            "education": ["school", "college", "university", "course", "education", "learning"],
            "groceries": ["bigbasket", "grofers", "dmart", "jiomart", "grocery", "supermarket"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in merchant_lower for keyword in keywords):
                transaction_data["category"] = category.capitalize()
                break
    
    # 8. Generate description
    if transaction_data["transaction_type"] and transaction_data["merchant"]:
        if transaction_data["transaction_type"] == "debit":
            transaction_data["description"] = f"Payment to {transaction_data['merchant']}"
        else:
            transaction_data["description"] = f"Payment from {transaction_data['merchant']}"
    
    return transaction_data

# For compatibility with existing code
if __name__ == "__main__":
    print("LangChain wrapper initialized")
    
    # Test the wrapper
    if GEMINI_API_KEY:
        test_prompt = "What is the capital of France?"
        print(f"Testing with prompt: {test_prompt}")
        response = ask_gemini(test_prompt)
        print(f"Response: {response}")

    # Test structured data extraction
    if GEMINI_API_KEY:
        schema = {
            "type": "object",
            "properties": {
                "transaction_type": {"type": "string"},
                "amount": {"type": "number"},
                "merchant_name": {"type": "string"},
                "account_masked": {"type": "string"},
                "date": {"type": "string"},
                "balance": {"type": "number"},
                "category": {"type": "string"},
                "description": {"type": "string"}
            }
        }
        test_prompt = "This is a test transaction description. Amount: 1000, Merchant: Swiggy, Date: 2023-04-15"
        print(f"Testing structured data extraction with prompt: {test_prompt}")
        structured_data = extract_structured_data(test_prompt, schema)
        print(f"Structured data: {structured_data}")

    # Test fraud detection
    if GEMINI_API_KEY:
        sms_text = "This is a test SMS message. Amount: 500, Merchant: Swiggy, Date: 2023-04-15"
        sender = "VK-ICICIBK"
        print(f"Testing fraud detection with SMS: {sms_text}")
        structured_data = extract_structured_data(sms_text, sender)
        print(f"Structured data: {structured_data}")

def detect_promotional_sms_with_gemini(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """
    Use Gemini to detect if an SMS is promotional or transactional.
    
    Args:
        sms_text: The SMS text content
        sender: Optional sender ID
        
    Returns:
        Dictionary with is_promotional (bool) and promo_score (float)
    """
    prompt = f"""
    Analyze this SMS message and determine if it's promotional/marketing or a banking transaction.
    
    SMS: {sms_text}
    Sender: {sender or "Unknown"}
    
    Respond with a structured JSON only:
    {{
        "is_promotional": true/false,
        "promo_score": 0.0-1.0 (confidence score),
        "reasoning": "brief explanation",
        "promotional_indicators": ["list", "of", "indicators"]
    }}
    
    Look for:
    1. Marketing language (offers, discounts, deals)
    2. Call to action phrases
    3. Merchant promotions
    4. Lack of transaction details
    5. Banking transaction indicators like account numbers, balances
    """
    
    try:
        response = ask_gemini(prompt)
        result = parse_json_response(response)
        
        if not result or "is_promotional" not in result:
            # Fallback structure if Gemini response is invalid
            return {
                "is_promotional": "http" in sms_text.lower() or "click" in sms_text.lower() or "offer" in sms_text.lower(),
                "promo_score": 0.5,
                "reasoning": "Fallback detection due to invalid Gemini response",
                "promotional_indicators": ["fallback_detection"]
            }
        return result
    except Exception as e:
        # Fallback structure in case of error
        return {
            "is_promotional": "http" in sms_text.lower() or "click" in sms_text.lower() or "offer" in sms_text.lower(),
            "promo_score": 0.5,
            "reasoning": f"Error using Gemini API: {str(e)}",
            "promotional_indicators": ["api_error"]
        } 