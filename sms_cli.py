#!/usr/bin/env python3

"""
SMS Parser CLI Tool
==================
A command-line interface for testing the SMS parser with various examples.
"""

import sys
import json
import argparse
import time
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional

# Try to import the SMS parser and examples
try:
    from sms_parser.tests.test_sms_examples import get_test_sms
except ImportError:
    print("Error: sms_parser.tests.test_sms_examples module not found.")
    print("Make sure you're running this script from the project root.")
    sys.exit(1)

try:
    from sms_parser.cli.main import process_sms
except ImportError:
    print("Error: sms_parser.cli.main module not found.")
    print("Make sure you're running this script from the project root.")
    sys.exit(1)

try:
    from sms_parser.core.logger import get_logger
except ImportError:
    print("Error: sms_parser.core.logger module not found.")
    print("Make sure you're running this script from the project root.")
    sys.exit(1)

# Colors for terminal output
COLORS = {
    "HEADER": "\033[95m",
    "BLUE": "\033[94m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m"
}

logger = get_logger(__name__)

def colorize(text: str, color: str) -> str:
    """Add color to text for terminal output"""
    if color in COLORS:
        return f"{COLORS[color]}{text}{COLORS['ENDC']}"
    return text

def parse_single_sms(sms_text: str, sender: str = None) -> Dict[str, Any]:
    """
    Parse a single SMS message and measure processing time
    
    Args:
        sms_text: The SMS text to parse
        sender: The sender ID (optional)
        
    Returns:
        A dictionary with parsing results and metadata
    """
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    
    # Record the start time
    start_time = time.time()
    
    # Parse the SMS
    try:
        result = process_sms(sms_text, sender)
    except Exception as e:
        result = {
            "error": str(e),
            "transaction": {},
            "fraud_detection": {"is_suspicious": False, "risk_level": "unknown"},
            "is_promotional": False,
            "metadata": {
                "raw_sms": sms_text,
                "sender": sender,
                "parsing_time": datetime.now().isoformat(),
                "parser_version": "2.1.0",
                "error": str(e)
            }
        }
    
    # Calculate processing time
    processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    # Add metadata to the result
    if result and isinstance(result, dict):
        if "metadata" not in result:
            result["metadata"] = {}
        result["metadata"]["request_id"] = request_id
        result["metadata"]["processing_time_ms"] = round(processing_time, 2)
    
    return result

def print_parsing_result(result: Dict[str, Any]) -> None:
    """
    Print the parsing result in a formatted way
    
    Args:
        result: The parsing result from parse_sms function
    """
    if not result:
        print(colorize("Error: No result returned from parser", "RED"))
        return
    
    # Check if there was an error
    if "error" in result and result["error"]:
        print(colorize(f"Error: {result['error']}", "RED"))
        return
    
    # Print transaction details if available
    transaction = result.get("transaction", {})
    if transaction:
        print(colorize("\n=== Transaction Details ===", "HEADER"))
        
        # Get transaction type and print with appropriate color
        txn_type = transaction.get("transaction_type", "unknown")
        if txn_type == "debit":
            txn_type_colored = colorize("DEBIT", "RED")
        elif txn_type == "credit":
            txn_type_colored = colorize("CREDIT", "GREEN")
        else:
            txn_type_colored = colorize(txn_type.upper(), "YELLOW")
        
        # Print amount with currency
        amount = transaction.get("amount", 0)
        currency = "INR"  # Default currency
        if "currency" in transaction:
            currency = transaction["currency"]
        
        print(f"Type: {txn_type_colored}")
        print(f"Amount: {colorize(f'{currency} {amount:,.2f}', 'BOLD')}")
        
        # Account info
        if "account_number" in transaction:
            print(f"Account: {transaction['account_number']}")
        
        # Merchant info
        if "merchant" in transaction and transaction["merchant"]:
            print(f"Merchant: {transaction['merchant']}")
        
        # Category
        if "category" in transaction and transaction["category"]:
            print(f"Category: {transaction['category']}")
        
        # Date
        if "date" in transaction and transaction["date"]:
            print(f"Date: {transaction['date']}")
        
        # Balance
        if "available_balance" in transaction:
            print(f"Available Balance: {currency} {transaction['available_balance']:,.2f}")
    
    # Print fraud detection results
    fraud_detection = result.get("fraud_detection", {})
    if fraud_detection:
        print(colorize("\n=== Fraud Detection ===", "HEADER"))
        
        # Is suspicious
        is_suspicious = fraud_detection.get("is_suspicious", False)
        if is_suspicious:
            print(f"Suspicious: {colorize('YES', 'RED')}")
            print(f"Risk Level: {colorize(fraud_detection.get('risk_level', 'unknown').upper(), 'RED')}")
            
            # Print indicators
            if "indicators" in fraud_detection and fraud_detection["indicators"]:
                print("Suspicious Indicators:")
                for indicator in fraud_detection["indicators"]:
                    print(f"  - {indicator}")
        else:
            print(f"Suspicious: {colorize('NO', 'GREEN')}")
    
    # Print promotional status
    is_promotional = result.get("is_promotional", False)
    print(colorize("\n=== Message Classification ===", "HEADER"))
    if is_promotional:
        print(f"Promotional: {colorize('YES', 'YELLOW')}")
        if "promotional_score" in result:
            print(f"Promotional Score: {result['promotional_score']}")
    else:
        print(f"Promotional: {colorize('NO', 'BLUE')}")
    
    # Print metadata
    metadata = result.get("metadata", {})
    if metadata:
        print(colorize("\n=== Metadata ===", "HEADER"))
        print(f"Request ID: {metadata.get('request_id', 'N/A')}")
        print(f"Processing Time: {metadata.get('processing_time_ms', 0)} ms")
        print(f"Parser Version: {metadata.get('parser_version', 'unknown')}")
        if "promotional_detection_method" in metadata:
            print(f"Promo Detection: {metadata['promotional_detection_method']}")

def list_categories() -> None:
    """List all available SMS example categories"""
    if not get_test_sms():
        print(colorize("Example categories not available.", "YELLOW"))
        return
    
    print(colorize("Available SMS Categories:", "HEADER"))
    for category, examples in get_test_sms().items():
        print(f"  - {category.replace('_', ' ').title()} ({len(examples)} examples)")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="SMS Parser CLI Tool")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse a single SMS")
    parse_parser.add_argument("--text", "-t", type=str, help="SMS text to parse")
    parse_parser.add_argument("--sender", "-s", type=str, help="Sender ID (optional)")
    parse_parser.add_argument("--file", "-f", type=str, help="File containing SMS messages (one per line)")
    
    # Example command
    example_parser = subparsers.add_parser("example", help="Parse an example SMS")
    example_parser.add_argument("--category", "-c", type=str, help="Example category")
    example_parser.add_argument("--random", "-r", action="store_true", help="Use a random example")
    example_parser.add_argument("--list", "-l", action="store_true", help="List available example categories")
    
    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Parse multiple examples")
    batch_parser.add_argument("--category", "-c", type=str, help="Example category")
    batch_parser.add_argument("--count", "-n", type=int, default=5, help="Number of examples to parse")
    
    return parser.parse_args()

def main() -> None:
    """Main entry point for the CLI tool"""
    args = parse_args()
    
    if not args.command:
        print(colorize("Error: No command specified. Use --help for usage information.", "RED"))
        return
    
    if args.command == "parse":
        if args.text:
            # Parse a single SMS from command line argument
            result = parse_single_sms(args.text, args.sender)
            print_parsing_result(result)
        elif args.file:
            # Parse multiple SMS messages from a file
            try:
                with open(args.file, "r") as f:
                    sms_list = [line.strip() for line in f.readlines() if line.strip()]
                
                if not sms_list:
                    print(colorize("Error: No SMS messages found in the file.", "RED"))
                    return
                
                print(colorize(f"Processing {len(sms_list)} SMS messages...", "BLUE"))
                
                for i, sms in enumerate(sms_list, 1):
                    print(colorize(f"\nSMS #{i}:", "BOLD"))
                    print(colorize(f"Text: {sms}", "BLUE"))
                    result = parse_single_sms(sms, args.sender)
                    print_parsing_result(result)
            except Exception as e:
                print(colorize(f"Error reading file: {str(e)}", "RED"))
        else:
            print(colorize("Error: No SMS text or file provided.", "RED"))
            print("Use --text to provide SMS text or --file to provide a file with SMS messages.")
    
    elif args.command == "example":
        if args.list:
            # List available example categories
            list_categories()
            return
        
        if args.random:
            # Parse a random example
            example = get_test_sms().get(None)
            if not example:
                print(colorize("Error: No examples available.", "RED"))
                return
            
            print(colorize("Random Example:", "HEADER"))
            print(f"Description: {example['description']}")
            print(f"Sender: {example['sender']}")
            print(colorize(f"SMS: {example['sms']}", "BLUE"))
            
            result = parse_single_sms(example['sms'], example['sender'])
            print_parsing_result(result)
        elif args.category:
            # Parse an example from a specific category
            example = get_test_sms().get(args.category)
            if not example:
                print(colorize(f"Error: No examples found for category '{args.category}'.", "RED"))
                return
            
            print(colorize(f"Example from {args.category.replace('_', ' ').title()}:", "HEADER"))
            print(f"Description: {example['description']}")
            print(f"Sender: {example['sender']}")
            print(colorize(f"SMS: {example['sms']}", "BLUE"))
            
            result = parse_single_sms(example['sms'], example['sender'])
            print_parsing_result(result)
        else:
            print(colorize("Error: No example options specified.", "RED"))
            print("Use --random for a random example or --category to specify a category.")
    
    elif args.command == "batch":
        if not args.category:
            print(colorize("Error: No category specified for batch processing.", "RED"))
            return
        
        # Get examples
        if args.category in get_test_sms():
            examples = get_test_sms()[args.category]
        else:
            examples = get_test_sms().get(None)
        
        if not examples:
            print(colorize(f"Error: No examples found for category '{args.category}'.", "RED"))
            return
        
        # Limit the number of examples
        count = min(args.count, len(examples))
        examples = examples[:count]
        
        print(colorize(f"Processing {count} examples from '{args.category}'...", "BLUE"))
        
        # Track success/failure stats
        stats = {
            "total": count,
            "success": 0,
            "promotional": 0,
            "fraud_detected": 0,
            "failed": 0,
            "avg_time_ms": 0
        }
        
        total_time = 0
        
        for i, example in enumerate(examples, 1):
            print(colorize(f"\nExample #{i}:", "BOLD"))
            print(f"Description: {example['description']}")
            print(f"Sender: {example['sender']}")
            print(colorize(f"SMS: {example['sms']}", "BLUE"))
            
            result = parse_single_sms(example['sms'], example['sender'])
            print_parsing_result(result)
            
            # Update stats
            metadata = result.get("metadata", {})
            if "error" in result and result["error"]:
                stats["failed"] += 1
            else:
                stats["success"] += 1
                
                if result.get("is_promotional", False):
                    stats["promotional"] += 1
                
                fraud_detection = result.get("fraud_detection", {})
                if fraud_detection and fraud_detection.get("is_suspicious", False):
                    stats["fraud_detected"] += 1
            
            processing_time = metadata.get("processing_time_ms", 0)
            total_time += processing_time
        
        # Calculate average processing time
        if stats["total"] > 0:
            stats["avg_time_ms"] = round(total_time / stats["total"], 2)
        
        # Print stats
        print(colorize("\n=== Batch Processing Statistics ===", "HEADER"))
        print(f"Total Processed: {stats['total']}")
        print(f"Successful: {stats['success']}")
        print(f"Failed: {stats['failed']}")
        print(f"Promotional: {stats['promotional']}")
        print(f"Fraud Detected: {stats['fraud_detected']}")
        print(f"Average Processing Time: {stats['avg_time_ms']} ms")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(colorize(f"Unexpected error: {str(e)}", "RED"))
        sys.exit(1) 