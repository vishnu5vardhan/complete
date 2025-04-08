#!/usr/bin/env python3

import sqlite3
import json
import datetime
import os
from typing import Dict, Any, Optional, Tuple, List
from sms_parser.core.config import DATABASE_PATH
from sms_parser.core.logger import get_logger

# Get logger
logger = get_logger(__name__)

# Ensure the data directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

def init_database() -> bool:
    """
    Initialize the SQLite database with required tables if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
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

def save_transaction(sms_text: str, sender: str, transaction_data: Dict[str, Any], 
                    fraud_data: Dict[str, Any], processing_time: float) -> bool:
    """
    Save a banking transaction to the database.
    
    Args:
        sms_text: The original SMS text
        sender: The sender of the SMS
        transaction_data: Extracted transaction data
        fraud_data: Fraud detection results
        processing_time: Time taken to process this SMS
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
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

def save_fraud_log(sms_text: str, sender: str, fraud_data: Dict[str, Any], 
                  processing_time: float) -> bool:
    """
    Save a fraud detection entry to the database.
    
    Args:
        sms_text: The original SMS text
        sender: The sender of the SMS
        fraud_data: Fraud detection results
        processing_time: Time taken to process this SMS
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
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

def save_promotional_sms(sms_text: str, sender: str, promo_data: Dict[str, Any], 
                        processing_time: float) -> bool:
    """
    Save a promotional SMS to the database.
    
    Args:
        sms_text: The original SMS text
        sender: The sender of the SMS
        promo_data: Promotional SMS data
        processing_time: Time taken to process this SMS
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO promotional_sms (
            sender,
            raw_sms,
            promotion_type,
            parsed_data,
            processing_time,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            sender,
            sms_text,
            promo_data.get('promotion_type', 'unknown'),
            json.dumps(promo_data),
            processing_time,
            datetime.datetime.now().isoformat()
        ))
        
        conn.commit()
        logger.info(f"Promotional SMS saved to database, ID: {cursor.lastrowid}")
        return True
    except Exception as e:
        logger.error(f"Error saving promotional SMS to database: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def get_recent_transactions(limit: int = 10) -> list:
    """
    Get recent transactions from the database.
    
    Args:
        limit: Maximum number of transactions to return
        
    Returns:
        list: List of recent transactions
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM transactions 
        ORDER BY created_at DESC 
        LIMIT ?
        ''', (limit,))
        
        columns = [description[0] for description in cursor.description]
        transactions = []
        
        for row in cursor.fetchall():
            transaction = dict(zip(columns, row))
            transaction['parsed_data'] = json.loads(transaction['parsed_data'])
            transactions.append(transaction)
        
        return transactions
    except Exception as e:
        logger.error(f"Error getting recent transactions: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def get_recent_fraud_logs(limit: int = 10) -> list:
    """
    Get recent fraud logs from the database.
    
    Args:
        limit: Maximum number of logs to return
        
    Returns:
        list: List of recent fraud logs
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM fraud_logs 
        ORDER BY created_at DESC 
        LIMIT ?
        ''', (limit,))
        
        columns = [description[0] for description in cursor.description]
        logs = []
        
        for row in cursor.fetchall():
            log = dict(zip(columns, row))
            log['parsed_data'] = json.loads(log['parsed_data'])
            log['suspicious_indicators'] = json.loads(log['suspicious_indicators'])
            logs.append(log)
        
        return logs
    except Exception as e:
        logger.error(f"Error getting recent fraud logs: {str(e)}")
        return []
    finally:
        if conn:
            conn.close() 