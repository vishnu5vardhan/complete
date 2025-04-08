import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import defaultdict

class RiskLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

@dataclass
class Transaction:
    amount: float
    timestamp: datetime
    account: str
    transaction_type: str  # 'credit' or 'debit'
    merchant: Optional[str] = None

@dataclass
class FraudDetectionResult:
    is_fraud: bool
    risk_level: RiskLevel
    reasons: List[str]
    account_match: bool
    flagged_keywords: List[str]
    raw_sms: str

class FraudDetector:
    def __init__(self):
        # Primary Layer: Fraud Keywords
        self.fraud_keywords = [
            r"click here",
            r"verify now",
            r"you have received \d+,\d+",
            r"loan approved",
            r"your card is blocked",
            r"update your KYC",
            r"urgent notice",
            r"win",
            r"cashback approved",
            r"act now",
            r"Amazon gift card",
            r"dear customer your account will be suspended",
            r"get ₹\d+ lakh instantly",
            r"bit\.ly",
            r"tinyurl\.com",
            r"kmbl\.in",
            r"short\.ly",
            r"goo\.gl",
            r"t\.co",
            r"ow\.ly",
            r"is\.gd",
            r"clk\.sh",
            r"yfrog\.com",
            r"migre\.me",
            r"ff\.im",
            r"tiny\.cc",
            r"url4\.eu",
            r"tr\.im",
            r"twit\.ac",
            r"su\.pr",
            r"twurl\.nl",
            r"snipurl\.com",
            r"short\.to",
            r"Buddy\.ly",
            r"ping\.fm",
            r"post\.ly",
            r"Just\.as",
            r"bkite\.com",
            r"snipr\.com",
            r"fic\.kr",
            r"loopt\.us",
            r"doiop\.com",
            r"twitthis\.com",
            r"ht\.ly",
            r"alturl\.com",
            r"tiny\.pl",
            r"kl\.am",
            r"wp\.me",
            r"rubyurl\.com",
            r"om\.ly",
            r"to\.ly",
            r"bit\.do",
            r"t\.co",
            r"lnkd\.in",
            r"db\.tt",
            r"qr\.ae",
            r"adf\.ly",
            r"goo\.gl",
            r"bitly\.com",
            r"cur\.lv",
            r"tinyurl\.com",
            r"ow\.ly",
            r"bit\.ly",
            r"ad\.cr",
            r"ity\.im",
            r"q\.gs",
            r"is\.gd",
            r"po\.st",
            r"bc\.vc",
            r"twitthis\.com",
            r"u\.to",
            r"j\.mp",
            r"buzurl\.com",
            r"cutt\.us",
            r"u\.bb",
            r"yourls\.org",
            r"x\.co",
            r"prettylinkpro\.com",
            r"scrnch\.me",
            r"filoops\.info",
            r"vzturl\.com",
            r"qr\.net",
            r"1url\.com",
            r"tweez\.me",
            r"v\.gd",
            r"tr\.im",
            r"link\.zip\.net"
        ]
        
        # Secondary Layer: Known Account Patterns
        self.known_account_patterns = [
            r"X{2,4}\d{4}",  # XX1234, XXXX1234
            r"ending with \d{4}",
            r"a/c \d{4}",
            r"account \d{4}",
            r"card \d{4}"
        ]
        
        # Tertiary Layer: Trusted Sender Prefixes
        self.trusted_sender_prefixes = [
            r"VK-ICICIBK",
            r"VK-HDFCBK",
            r"VK-SBIBK",
            r"VK-AXISBK",
            r"VK-KOTAK",
            r"VK-INDUS",
            r"VK-YESBANK",
            r"VK-PNBBK",
            r"VK-CANBNK",
            r"VK-BOIBK",
            r"VK-UBIBK",
            r"VK-IDBIBK",
            r"VK-BARB",
            r"VK-SBICRD",
            r"VK-HDFCCRD",
            r"VK-ICICICRD",
            r"VK-AXISCRD",
            r"VK-KOTAKCRD",
            r"VK-INDUSCRD",
            r"VK-YESCRD",
            r"VK-PNBCRD",
            r"VK-CANCRD",
            r"VK-BOICRD",
            r"VK-UBICRD",
            r"VK-IDBICRD",
            r"VK-BARBCRD"
        ]
        
        # Compile regex patterns for better performance
        self.fraud_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.fraud_keywords]
        self.account_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.known_account_patterns]
        self.sender_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.trusted_sender_prefixes]
        
        # Initialize user account management
        self.known_user_accounts: Set[str] = set()
        
        # Initialize transaction history for pattern detection
        self.transaction_history: List[Transaction] = []
        self.transaction_thresholds = {
            'max_amount': 100000.0,  # Maximum normal transaction amount
            'max_daily_transactions': 10,  # Maximum number of transactions per day
            'max_daily_amount': 200000.0,  # Maximum total amount per day
            'unusual_hour_start': 23,  # Start of unusual hours (11 PM)
            'unusual_hour_end': 5,  # End of unusual hours (5 AM)
        }
        
        # Initialize bank sender mapping
        self.bank_sender_map = {
            'ICICI': ['VK-ICICIBK', 'VK-ICICICRD'],
            'HDFC': ['VK-HDFCBK', 'VK-HDFCCRD'],
            'SBI': ['VK-SBIBK', 'VK-SBICRD'],
            'AXIS': ['VK-AXISBK', 'VK-AXISCRD'],
            'KOTAK': ['VK-KOTAK', 'VK-KOTAKCRD'],
            'YES': ['VK-YESBANK', 'VK-YESCRD'],
            'PNB': ['VK-PNBBK', 'VK-PNBCRD'],
            'CANARA': ['VK-CANBNK', 'VK-CANCRD'],
            'BOI': ['VK-BOIBK', 'VK-BOICRD'],
            'UNION': ['VK-UBIBK', 'VK-UBICRD'],
            'IDBI': ['VK-IDBIBK', 'VK-IDBICRD'],
            'BARODA': ['VK-BARB', 'VK-BARBCRD']
        }

    def add_known_account(self, account_number: str) -> None:
        """Add a verified account number to the known accounts list"""
        self.known_user_accounts.add(account_number)

    def is_known_account(self, account_number: str) -> bool:
        """Check if an account number is in the known accounts list"""
        return account_number in self.known_user_accounts

    def add_transaction(self, transaction: Transaction) -> None:
        """Add a transaction to the history for pattern analysis"""
        self.transaction_history.append(transaction)
        # Keep only last 30 days of transactions
        cutoff_date = datetime.now() - timedelta(days=30)
        self.transaction_history = [t for t in self.transaction_history if t.timestamp > cutoff_date]

    def get_daily_transactions(self, date: datetime) -> List[Transaction]:
        """Get all transactions for a specific date"""
        return [t for t in self.transaction_history 
                if t.timestamp.date() == date.date()]

    def is_unusual_transaction_pattern(self, transaction: Transaction) -> tuple[bool, List[str]]:
        """
        Check for unusual transaction patterns
        Returns: (is_unusual: bool, reasons: List[str])
        """
        reasons = []
        
        # Check transaction amount
        if transaction.amount > self.transaction_thresholds['max_amount']:
            reasons.append("unusually_large_amount")
        
        # Check transaction timing
        hour = transaction.timestamp.hour
        if self.transaction_thresholds['unusual_hour_start'] <= hour or hour < self.transaction_thresholds['unusual_hour_end']:
            reasons.append("unusual_hour")
        
        # Check daily transaction count and amount
        daily_transactions = self.get_daily_transactions(transaction.timestamp)
        if len(daily_transactions) > self.transaction_thresholds['max_daily_transactions']:
            reasons.append("excessive_daily_transactions")
        
        daily_amount = sum(t.amount for t in daily_transactions) + transaction.amount
        if daily_amount > self.transaction_thresholds['max_daily_amount']:
            reasons.append("excessive_daily_amount")
        
        return bool(reasons), reasons

    def validate_bank_sender(self, sender: str, bank_name: Optional[str] = None) -> bool:
        """
        Validate that a sender ID matches the expected format for a bank
        If bank_name is provided, check specifically against that bank's known senders
        """
        if not sender:
            return False
            
        # If bank name is provided, check against that bank's senders
        if bank_name and bank_name.upper() in self.bank_sender_map:
            return sender in self.bank_sender_map[bank_name.upper()]
        
        # Otherwise check against all known bank senders
        return any(sender in senders for senders in self.bank_sender_map.values())

    def detect_fraud(self, sms_text: str, sender: Optional[str] = None) -> FraudDetectionResult:
        """
        Analyze an SMS message for potential fraud using multiple detection layers.
        
        Args:
            sms_text: The raw SMS text to analyze
            sender: Optional sender identifier (e.g., "VK-ICICIBK")
            
        Returns:
            FraudDetectionResult containing analysis results
        """
        reasons = []
        flagged_keywords = []
        account_match = True
        risk_level = RiskLevel.LOW
        
        # Primary Layer: Fraud Keyword Detection
        for pattern in self.fraud_patterns:
            if pattern.search(sms_text):
                flagged_keywords.append(pattern.pattern)
                reasons.append("keyword_match")
                risk_level = RiskLevel.HIGH if len(flagged_keywords) > 1 else RiskLevel.MEDIUM
        
        # Secondary Layer: Account Number Consistency
        account_numbers = []
        for pattern in self.account_patterns:
            matches = pattern.finditer(sms_text)
            for match in matches:
                account_number = match.group()
                account_numbers.append(account_number)
                
        if account_numbers:
            # Check if any of the found account numbers are known
            if not any(self.is_known_account(acc) for acc in account_numbers):
                reasons.append("unknown_account")
                account_match = False
                risk_level = max(risk_level, RiskLevel.MEDIUM)
        else:
            # If the message appears to be from a bank but has no account number
            if any(bank in sms_text.lower() for bank in ["bank", "account", "card", "transaction"]):
                reasons.append("account_mismatch")
                account_match = False
                risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # Tertiary Layer: Sender Identity Verification
        if sender:
            if not any(pattern.match(sender) for pattern in self.sender_patterns):
                reasons.append("unknown_sender")
                risk_level = max(risk_level, RiskLevel.MEDIUM)
                
            # Additional check: validate sender against bank name if present
            for bank_name in self.bank_sender_map.keys():
                if bank_name.lower() in sms_text.lower():
                    if not self.validate_bank_sender(sender, bank_name):
                        reasons.append("mismatched_bank_sender")
                        risk_level = max(risk_level, RiskLevel.HIGH)
        else:
            reasons.append("missing_sender")
            risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # Pattern Analysis Layer
        try:
            # Try to extract transaction details
            amount_match = re.search(r"(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)", sms_text)
            if amount_match:
                amount = float(amount_match.group(1).replace(',', ''))
                transaction = Transaction(
                    amount=amount,
                    timestamp=datetime.now(),
                    account=account_numbers[0] if account_numbers else "unknown",
                    transaction_type="debit" if "debited" in sms_text.lower() else "credit",
                    merchant=None  # Could be extracted if needed
                )
                
                is_unusual, unusual_reasons = self.is_unusual_transaction_pattern(transaction)
                if is_unusual:
                    reasons.extend(unusual_reasons)
                    risk_level = max(risk_level, RiskLevel.MEDIUM)
                
                # Add transaction to history if it seems legitimate
                if risk_level == RiskLevel.LOW:
                    self.add_transaction(transaction)
        except Exception as e:
            print(f"Error analyzing transaction pattern: {e}")
        
        # Determine final fraud status
        is_fraud = risk_level != RiskLevel.LOW
        
        return FraudDetectionResult(
            is_fraud=is_fraud,
            risk_level=risk_level,
            reasons=reasons,
            account_match=account_match,
            flagged_keywords=flagged_keywords,
            raw_sms=sms_text
        ) 