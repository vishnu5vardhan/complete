#!/usr/bin/env python3

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    
    def __str__(self) -> str:
        return self.value

@dataclass
class Transaction:
    """Class representing a financial transaction from an SMS"""
    amount: float
    transaction_type: str
    merchant_name: str = ""
    account_masked: str = ""
    date: str = ""
    available_balance: float = 0.0
    category: str = "Uncategorized"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary"""
        return {
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "merchant_name": self.merchant_name,
            "account_masked": self.account_masked,
            "date": self.date,
            "available_balance": self.available_balance,
            "category": self.category,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create Transaction from dictionary"""
        # Handle various field name formats
        amount = data.get('amount', data.get('transaction_amount', 0.0))
        transaction_type = data.get('transaction_type', '')
        merchant_name = data.get('merchant_name', data.get('merchant', ''))
        account_masked = data.get('account_masked', data.get('account_number', data.get('account', '')))
        date = data.get('date', data.get('transaction_date', datetime.now().strftime('%Y-%m-%d')))
        available_balance = data.get('available_balance', 0.0)
        category = data.get('category', 'Uncategorized')
        description = data.get('description', '')
        
        return cls(
            amount=amount,
            transaction_type=transaction_type,
            merchant_name=merchant_name,
            account_masked=account_masked,
            date=date,
            available_balance=available_balance,
            category=category,
            description=description
        )

@dataclass
class FraudDetectionResult:
    """Class representing the result of fraud detection"""
    is_fraud: bool
    risk_level: RiskLevel
    reasons: List[str]
    flagged_keywords: List[str] = None
    
    def __post_init__(self):
        if self.flagged_keywords is None:
            self.flagged_keywords = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "is_fraud": self.is_fraud,
            "risk_level": str(self.risk_level),
            "reasons": self.reasons,
            "flagged_keywords": self.flagged_keywords
        } 