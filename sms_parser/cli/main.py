#!/usr/bin/env python3

import argparse
import time
import json
from typing import Dict, Any, Optional

# Import from the package
from sms_parser.parsers import light_filter, parse_sms, parse_sms_fallback
from sms_parser.detectors import FraudDetector
from sms_parser.core import (
    init_database, 
    save_transaction, 
    save_fraud_log, 
    save_promotional_sms,
    get_logger
)

# Get logger
logger = get_logger(__name__)

def process_sms(sms_text: str, sender: Optional[str] = None) -> Dict[str, Any]:
    """
    Process an SMS message through the entire pipeline:
    1. Apply light filter
    2. Send to Gemini for parsing
    3. Validate the parsed data
    4. Save to appropriate storage based on type
    
    Args:
        sms_text: The SMS text to analyze
        sender: Optional sender ID
        
    Returns:
        Dict containing the processing results
    """
    start_time = time.time()
    
    # Initialize result with metadata
    result = {
        "raw_sms": sms_text,
        "sender": sender,
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "processing_time_ms": 0,
        "is_processed": False,
        "is_banking_sms": False,
        "is_promotional": False,
        "is_fraud": False,
        "status": "unknown",
        "error": None
    }
    
    try:
        # Step 1: Apply light filter
        if not light_filter(sms_text):
            result["status"] = "filtered_out"
            result["is_processed"] = True
            return result
        
        # Step 2: Try Gemini parsing
        try:
            parsed_data = parse_sms(sms_text, sender)
        except Exception as e:
            # If Gemini fails, use fallback parser
            parsed_data = parse_sms_fallback(sms_text, sender)
            result["parsing_method"] = "fallback"
            result["error"] = str(e)
        else:
            result["parsing_method"] = "gemini"
        
        # Step 3: Fraud detection
        fraud_detector = FraudDetector()
        fraud_result = fraud_detector.detect_fraud(sms_text, sender)
        
        # Step 4: Save to appropriate storage
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if fraud_result.is_fraud:
            save_fraud_log(sms_text, sender, {
                "risk_level": fraud_result.risk_level,
                "suspicious_indicators": fraud_result.reasons,
                "flagged_keywords": fraud_result.flagged_keywords
            }, processing_time)
            result["is_fraud"] = True
        elif parsed_data.get("is_promotional", False):
            save_promotional_sms(sms_text, sender, parsed_data, processing_time)
            result["is_promotional"] = True
        else:
            save_transaction(sms_text, sender, parsed_data, {
                "risk_level": fraud_result.risk_level,
                "suspicious_indicators": fraud_result.reasons
            }, processing_time)
            result["is_banking_sms"] = True
        
        result["is_processed"] = True
        result["status"] = "success"
        result["processing_time_ms"] = processing_time
        result["parsed_data"] = parsed_data
        result["fraud_detection"] = {
            "is_suspicious": fraud_result.is_fraud,
            "risk_level": fraud_result.risk_level,
            "suspicious_indicators": fraud_result.reasons,
            "flagged_keywords": fraud_result.flagged_keywords
        }
        
        return result
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result

def main():
    # Initialize database
    init_database()
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="SMS Parser CLI")
    parser.add_argument("-s", "--sms", required=True, help="SMS text to parse")
    parser.add_argument("-f", "--sender", help="Sender ID")
    parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Process the SMS
    result = process_sms(args.sms, args.sender)
    
    # Output the result
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.verbose:
            print("\nProcessing Details:")
            print(f"Status: {result['status']}")
            print(f"Processing Time: {result['processing_time_ms']:.2f}ms")
            print(f"Method: {result.get('parsing_method', 'unknown')}")
            
            if result.get('error'):
                print(f"Error: {result['error']}")
            
            if result.get('parsed_data'):
                print("\nParsed Data:")
                for key, value in result['parsed_data'].items():
                    print(f"{key}: {value}")
            
            if result.get('fraud_detection'):
                print("\nFraud Detection:")
                for key, value in result['fraud_detection'].items():
                    print(f"{key}: {value}")
        else:
            if result['status'] == 'filtered_out':
                print("SMS filtered out (not a financial SMS)")
            elif result['status'] == 'error':
                print(f"Error: {result['error']}")
            else:
                if result['is_fraud']:
                    print("Fraudulent SMS detected!")
                elif result['is_promotional']:
                    print("Promotional SMS detected")
                else:
                    print("Transaction SMS processed successfully")

if __name__ == "__main__":
    main() 