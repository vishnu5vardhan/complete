#!/usr/bin/env python3

import os
import json
import time
import datetime
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
import logging
from logging.handlers import RotatingFileHandler

# Import modules from existing codebase
from enhanced_sms_parser import light_filter, parse_sms
from llm_parser import call_gemini_api
from validate_sms_json import validate_sms_json, is_banking_sms

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler("sms_parser.log", maxBytes=1048576, backupCount=10),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main_parser")

# Database path
DB_PATH = 'sms_data.db'

def init_database():
    """Initialize the SQLite database with required tables if they don't exist."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create transactions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            raw_sms TEXT,
            transaction_amount REAL,
            transaction_type TEXT,
            merchant TEXT,
            category TEXT,
            account_number TEXT,
            transaction_date TEXT,
            available_balance REAL,
            parsed_data TEXT,
            processing_time REAL,
            created_at TEXT
        )
        ''')
        
        # Create fraud_logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fraud_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            raw_sms TEXT,
            fraud_risk_level TEXT,
            suspicious_indicators TEXT,
            parsed_data TEXT,
            processing_time REAL,
            created_at TEXT
        )
        ''')
        
        # Create promotional_sms table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS promotional_sms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            raw_sms TEXT,
            promotion_type TEXT,
            parsed_data TEXT,
            processing_time REAL,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        return False
    finally:
        if conn:
            conn.close()

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
        "processed_at": datetime.datetime.now().isoformat(),
        "processing_time_ms": 0,
        "is_processed": False,
        "is_banking_sms": False,
        "is_promotional": False,
        "is_fraud": False,
        "status": "unknown",
        "error": None
    }
    
    try:
        # Step 1: Apply light filter to quickly reject irrelevant SMS
        logger.info(f"Processing SMS: {sms_text[:50]}{'...' if len(sms_text) > 50 else ''}")
        
        if not light_filter(sms_text):
            result["status"] = "filtered_out"
            result["is_processed"] = True
            logger.info("SMS filtered out by light filter (not a financial SMS)")
            return result
        
        # Step 2: Send to Gemini API for parsing
        logger.info("SMS passed light filter, sending to Gemini API")
        parsed_response = parse_sms(sms_text, sender)
        
        if not parsed_response:
            result["status"] = "parsing_failed"
            logger.error("Failed to parse SMS with Gemini API")
            return result
        
        # Extract the different components from the parsed response
        transaction_data = parsed_response.get('transaction', {})
        fraud_data = parsed_response.get('fraud_detection', {})
        metadata = parsed_response.get('metadata', {})
        
        # Set the flags based on the parsed response
        result["is_promotional"] = parsed_response.get('is_promotional', False)
        result["is_fraud"] = fraud_data.get('is_suspicious', False) and fraud_data.get('risk_level') in ['medium', 'high']
        result["is_banking_sms"] = bool(transaction_data.get('transaction_amount', 0) and transaction_data.get('transaction_type'))
        
        # Store the parsed data
        result["parsed_data"] = transaction_data
        
        # Save to appropriate storage based on type
        if result["is_banking_sms"]:
            logger.info("Banking SMS detected, saving to transactions database")
            save_transaction(sms_text, sender, transaction_data, fraud_data, time.time() - start_time)
            result["status"] = "banking_transaction_saved"
        elif result["is_fraud"]:
            logger.warning("Fraud SMS detected, saving to fraud log")
            save_fraud_log(sms_text, sender, fraud_data, time.time() - start_time)
            result["status"] = "fraud_detected"
        elif result["is_promotional"]:
            logger.info("Promotional SMS detected, tagged and skipped")
            result["status"] = "promotional_skipped"
        else:
            logger.info("Non-banking SMS that passed light filter, skipped")
            result["status"] = "non_banking_skipped"
        
        result["is_processed"] = True
        
    except Exception as e:
        logger.error(f"Error processing SMS: {str(e)}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
    
    # Calculate processing time
    end_time = time.time()
    result["processing_time_ms"] = round((end_time - start_time) * 1000, 2)
    
    return result

def save_transaction(sms_text, sender, transaction_data, fraud_data, processing_time):
    """
    Save a banking transaction to the database.
    
    Args:
        sms_text (str): The original SMS text
        sender (str): The sender of the SMS
        transaction_data (dict): Extracted transaction data
        fraud_data (dict): Fraud detection results
        processing_time (float): Time taken to process this SMS
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO transactions (
            sender,
            raw_sms,
            transaction_amount,
            transaction_type,
            merchant,
            category,
            account_number,
            transaction_date,
            available_balance,
            parsed_data,
            processing_time,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sender,
            sms_text,
            transaction_data.get('transaction_amount', transaction_data.get('amount', 0.0)),
            transaction_data.get('transaction_type', ''),
            transaction_data.get('merchant', transaction_data.get('merchant_name', '')),
            transaction_data.get('category', 'Uncategorized'),
            transaction_data.get('account_number', transaction_data.get('account_masked', transaction_data.get('account', ''))),
            transaction_data.get('date', transaction_data.get('transaction_date', datetime.datetime.now().strftime('%Y-%m-%d'))),
            transaction_data.get('available_balance', 0.0),
            json.dumps(transaction_data),
            processing_time,
            datetime.datetime.now().isoformat()
        ))
        
        conn.commit()
        logger.info(f"Transaction saved to database, ID: {cursor.lastrowid}")
        return True
    except Exception as e:
        logger.error(f"Error saving transaction to database: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def save_fraud_log(sms_text, sender, fraud_data, processing_time):
    """
    Save a fraud detection entry to the database.
    
    Args:
        sms_text (str): The original SMS text
        sender (str): The sender of the SMS
        fraud_data (dict): Fraud detection results
        processing_time (float): Time taken to process this SMS
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO fraud_logs (
            sender,
            raw_sms,
            fraud_risk_level,
            suspicious_indicators,
            parsed_data,
            processing_time,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            sender,
            sms_text,
            fraud_data.get('risk_level', 'unknown'),
            json.dumps(fraud_data.get('suspicious_indicators', [])),
            json.dumps(fraud_data),
            processing_time,
            datetime.datetime.now().isoformat()
        ))
        
        conn.commit()
        logger.info(f"Fraud log saved to database, ID: {cursor.lastrowid}")
        return True
    except Exception as e:
        logger.error(f"Error saving fraud log to database: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def process_batch(sms_list: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Process a batch of SMS messages
    
    Args:
        sms_list: List of dictionaries with 'sms' and 'sender' keys
        
    Returns:
        List of processing results
    """
    results = []
    for item in sms_list:
        result = process_sms(item.get("sms", ""), item.get("sender", None))
        results.append(result)
    return results

if __name__ == "__main__":
    # Initialize the database
    if not init_database():
        logger.error("Failed to initialize database. Exiting.")
        exit(1)
    
    # Example SMS messages
    test_sms_list = [
        {
            "sms": "INR 689.00 spent using your HDFC Bank Credit Card XX1823 on 03-Apr-25 at MCDONALD'S. Avl Limit: INR 12,310.00",
            "sender": "HDFCBK"
        },
        {
            "sms": "Your OTP for transaction 123456 is 987654. Valid for 10 minutes.",
            "sender": "OTPSMS"
        },
        {
            "sms": "URGENT: Your account will be blocked. Update KYC immediately to avoid service disruption. Click here: bit.ly/upd8kyc",
            "sender": "TX-KYCSMS"
        },
        {
            "sms": "ARROW End of Season Sale is HERE, Buy 2 Get 2 FREE on Formals, Occasion Wear, & Casuals. Hurry, the best styles will not last! Visit an exclusive store now.",
            "sender": "VK-ARROW"
        }
    ]
    
    # Process test SMS batch
    results = process_batch(test_sms_list)
    
    # Print results summary
    print("\nProcessing Results Summary:")
    print("=========================\n")
    
    # Counters for summary
    counters = {
        'banking_transaction_saved': 0,
        'fraud_detected': 0,
        'promotional': 0,
        'filtered_out': 0,
        'error': 0
    }
    
    # Print details for each SMS
    for i, result in enumerate(results, 1):
        print(f"{i}. SMS: {result['raw_sms'][:50]}...")
        print(f"   Sender: {result['sender']}")
        print(f"   Status: {result['status']}")
        print(f"   Processing Time: {result['processing_time_ms']:.2f}ms")
        
        if result['status'] == 'banking_transaction_saved':
            transaction = result['parsed_data']
            print(f"   -> BANKING TRANSACTION: {transaction.get('transaction_type')} {transaction.get('transaction_amount', transaction.get('amount'))} at {transaction.get('merchant', transaction.get('merchant_name', ''))}")
            counters['banking_transaction_saved'] += 1
        elif result['status'] == 'fraud_detected':
            print(f"   -> FRAUD DETECTED: {result.get('parsed_data', {}).get('risk_level', 'unknown')} risk")
            counters['fraud_detected'] += 1
        elif result['status'] == 'promotional':
            counters['promotional'] += 1
        elif result['status'] == 'filtered_out':
            counters['filtered_out'] += 1
        elif result['status'] == 'error':
            counters['error'] += 1
            
        print()
    
    # Print summary counts
    print("Summary Counts:")
    print(f"Banking Transactions: {counters['banking_transaction_saved']}")
    print(f"Fraud Detected: {counters['fraud_detected']}")
    print(f"Promotional: {counters['promotional']}")
    print(f"Filtered Out: {counters['filtered_out']}")
    print(f"Errors: {counters['error']}") 