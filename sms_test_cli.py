#!/usr/bin/env python3

import argparse
import json
from enhanced_sms_parser import parse_sms
from typing import Optional

def parse_sms_cli(sms_text: str, sender: Optional[str] = None) -> dict:
    """
    Parse an SMS and return structured output
    
    Args:
        sms_text: The SMS text to parse
        sender: Optional sender ID
        
    Returns:
        Dictionary containing parsed information
    """
    result = parse_sms(sms_text, sender)
    
    # Format the output for CLI
    output = {
        "type": result.get("transaction", {}).get("transaction_type", "unknown"),
        "amount": result.get("transaction", {}).get("transaction_amount", 0.0),
        "merchant": result.get("transaction", {}).get("merchant", ""),
        "category": result.get("transaction", {}).get("category", "Uncategorized"),
        "is_promotional": result.get("is_promotional", False),
        "fraud_alert": result.get("fraud_detection", {}).get("is_suspicious", False),
        "fraud_risk_level": result.get("fraud_detection", {}).get("risk_level", "none")
    }
    
    return output

def main():
    parser = argparse.ArgumentParser(description='SMS Parser CLI Tool')
    parser.add_argument('-s', '--sms', required=True, help='SMS text to parse')
    parser.add_argument('-f', '--sender', help='Sender ID (optional)')
    parser.add_argument('-j', '--json', action='store_true', help='Output in JSON format')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    # Parse the SMS
    result = parse_sms_cli(args.sms, args.sender)
    
    # Output the result
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.verbose:
            print("\nSMS Analysis Results:")
            print("=" * 50)
            print(f"SMS: {args.sms}")
            if args.sender:
                print(f"Sender: {args.sender}")
            print("\nTransaction Details:")
            print(f"Type: {result['type']}")
            print(f"Amount: {result['amount']}")
            print(f"Merchant: {result['merchant']}")
            print(f"Category: {result['category']}")
            print("\nSecurity Analysis:")
            print(f"Promotional: {'Yes' if result['is_promotional'] else 'No'}")
            print(f"Fraud Alert: {'Yes' if result['fraud_alert'] else 'No'}")
            if result['fraud_alert']:
                print(f"Risk Level: {result['fraud_risk_level']}")
        else:
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 