#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseParser(ABC):
    """
    Abstract base class for SMS parsers.
    All parsers should inherit from this class and implement the parse method.
    """
    
    @abstractmethod
    def parse(self, sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse an SMS message and extract structured information.
        
        Args:
            sms_text: The text content of the SMS
            sender: The sender ID of the SMS (optional)
            
        Returns:
            Dict containing parsed information
        """
        pass
    
    def preprocess_sms(self, sms_text: str) -> str:
        """
        Preprocess SMS text by cleaning, normalizing, etc.
        
        Args:
            sms_text: Raw SMS text
            
        Returns:
            Preprocessed SMS text
        """
        if not sms_text:
            return ""
            
        # Remove extra whitespace
        text = " ".join(sms_text.split())
        
        # Basic normalization
        text = text.replace('Rs.', 'Rs ')
        text = text.replace('INR', 'Rs ')
        
        return text
    
    def postprocess_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process the parsing result to ensure consistency and add metadata.
        
        Args:
            result: The raw parsing result
            
        Returns:
            The post-processed result
        """
        # Ensure required fields exist
        if "is_banking_sms" not in result:
            result["is_banking_sms"] = False
            
        if "is_promotional" not in result:
            result["is_promotional"] = False
            
        # Set category to "Uncategorized" if not specified
        if "category" not in result:
            result["category"] = "Uncategorized"
            
        return result 