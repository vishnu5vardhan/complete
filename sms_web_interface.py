#!/usr/bin/env python3

import json
import time
import datetime
import sqlite3
from flask import Flask, request, render_template, jsonify
from typing import Dict, Any, Optional
from enhanced_sms_parser import parse_sms

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Initialize database
DB_PATH = 'sms_data.db'

def setup_database():
    """Initialize the SQLite database if it doesn't exist"""
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
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
        return False
    finally:
        if conn:
            conn.close()
    return True

def save_to_database(parsed_result: Dict[str, Any], sms_text: str, sender: Optional[str] = None):
    """Save the parsing result to the database"""
    # Extract components
    transaction_data = parsed_result.get('transaction', {})
    fraud_detection = parsed_result.get('fraud_detection', {})
    is_promotional = parsed_result.get('is_promotional', False)
    is_suspicious = fraud_detection.get('is_suspicious', False)
    risk_level = fraud_detection.get('risk_level', 'none')
    
    # Determine if it's a fraud or transaction
    is_fraud = is_suspicious and risk_level != 'none'
    is_transaction = bool(transaction_data.get('transaction_amount', 0) or transaction_data.get('amount', 0))
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Record processing time
        processing_time = 0
        
        if is_fraud:
            # Save to fraud_logs
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
                risk_level,
                json.dumps(fraud_detection.get('suspicious_indicators', [])),
                json.dumps(fraud_detection),
                processing_time,
                datetime.datetime.now().isoformat()
            ))
            result_id = cursor.lastrowid
            result_type = "fraud"
        
        elif is_transaction and not is_promotional:
            # Save to transactions
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
            result_id = cursor.lastrowid
            result_type = "transaction"
        else:
            result_id = None
            result_type = None
        
        conn.commit()
        return result_id, result_type
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None, None
    finally:
        if conn:
            conn.close()

def process_sms(sms_text: str, sender: Optional[str] = None, save: bool = False) -> Dict[str, Any]:
    """Process an SMS message and return the results"""
    start_time = time.time()
    
    # Parse the SMS using the enhanced parser
    parsed_result = parse_sms(sms_text, sender)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    # Add processing time to the result
    parsed_result['metadata'] = parsed_result.get('metadata', {})
    parsed_result['metadata']['processing_time_ms'] = processing_time * 1000
    
    # Save to database if requested
    if save:
        result_id, result_type = save_to_database(parsed_result, sms_text, sender)
        if result_id and result_type:
            parsed_result['metadata']['saved'] = True
            parsed_result['metadata']['saved_as'] = result_type
            parsed_result['metadata']['record_id'] = result_id
    
    return parsed_result

@app.route('/')
def home():
    """Render the home page"""
    return render_template('index.html')

@app.route('/api/parse', methods=['POST'])
def parse_sms_api():
    """API endpoint for parsing SMS messages"""
    data = request.json
    
    if not data or 'sms_text' not in data:
        return jsonify({
            'error': 'Missing SMS text',
            'status': 'error'
        }), 400
    
    sms_text = data['sms_text']
    sender = data.get('sender')
    save = data.get('save', False)
    
    try:
        result = process_sms(sms_text, sender, save)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/recent-transactions', methods=['GET'])
def get_recent_transactions():
    """Get recent transactions from the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            id, 
            sender, 
            raw_sms, 
            transaction_amount, 
            transaction_type, 
            merchant, 
            category, 
            transaction_date,
            created_at
        FROM transactions 
        ORDER BY id DESC 
        LIMIT 10
        ''')
        
        transactions = cursor.fetchall()
        
        return jsonify([{
            'id': t[0],
            'sender': t[1],
            'raw_sms': t[2],
            'amount': t[3],
            'type': t[4],
            'merchant': t[5],
            'category': t[6],
            'date': t[7],
            'created_at': t[8]
        } for t in transactions])
    except sqlite3.Error as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/recent-fraud', methods=['GET'])
def get_recent_fraud():
    """Get recent fraud logs from the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            id, 
            sender, 
            raw_sms, 
            fraud_risk_level, 
            suspicious_indicators,
            created_at
        FROM fraud_logs 
        ORDER BY id DESC 
        LIMIT 10
        ''')
        
        fraud_logs = cursor.fetchall()
        
        return jsonify([{
            'id': f[0],
            'sender': f[1],
            'raw_sms': f[2],
            'risk_level': f[3],
            'suspicious_indicators': json.loads(f[4]) if f[4] else [],
            'created_at': f[5]
        } for f in fraud_logs])
    except sqlite3.Error as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500
    finally:
        if conn:
            conn.close()

# Create templates folder and index.html
def create_templates():
    """Create the templates folder and index.html if they don't exist"""
    import os
    
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    index_path = os.path.join(templates_dir, 'index.html')
    
    if not os.path.exists(index_path):
        with open(index_path, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMS Analyzer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding-top: 20px;
            background-color: #f8f9fa;
        }
        .result-box {
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            padding: 20px;
        }
        .tab-content {
            padding: 20px;
            background-color: #fff;
            border: 1px solid #dee2e6;
            border-top: 0;
            border-radius: 0 0 5px 5px;
        }
        .transaction-label {
            font-weight: bold;
            min-width: 150px;
            display: inline-block;
        }
        .promotional {
            background-color: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 15px;
        }
        .fraudulent {
            background-color: #f8d7da;
            border-left: 5px solid #dc3545;
            padding: 15px;
        }
        .transaction {
            background-color: #d1e7dd;
            border-left: 5px solid #198754;
            padding: 15px;
        }
        .generic {
            background-color: #cff4fc;
            border-left: 5px solid #0dcaf0;
            padding: 15px;
        }
        .indicator {
            display: inline-block;
            padding: 3px 8px;
            background-color: #dc3545;
            color: white;
            border-radius: 15px;
            font-size: 0.8rem;
            margin: 2px;
        }
        .sms-history-item {
            padding: 10px;
            border-bottom: 1px solid #dee2e6;
        }
        .sms-history-item:last-child {
            border-bottom: none;
        }
        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4 text-center">SMS Analyzer</h1>
        
        <div class="row mb-4">
            <div class="col-md-8 offset-md-2">
                <div class="card">
                    <div class="card-header">
                        <h5>Analyze SMS Message</h5>
                    </div>
                    <div class="card-body">
                        <form id="smsForm">
                            <div class="mb-3">
                                <label for="smsText" class="form-label">SMS Text</label>
                                <textarea class="form-control" id="smsText" rows="4" placeholder="Enter the SMS message to analyze" required></textarea>
                            </div>
                            <div class="mb-3">
                                <label for="smsSender" class="form-label">Sender (optional)</label>
                                <input type="text" class="form-control" id="smsSender" placeholder="e.g. HDFCBK, TX-ABCDE">
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="saveDatabase">
                                <label class="form-check-label" for="saveDatabase">Save results to database</label>
                            </div>
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary">Analyze</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4" id="resultsSection" style="display: none;">
            <div class="col-md-10 offset-md-1">
                <div class="card">
                    <div class="card-header">
                        <h5>Analysis Results</h5>
                    </div>
                    <div class="card-body">
                        <div id="loadingIndicator" class="text-center">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p>Analyzing SMS...</p>
                        </div>
                        
                        <div id="resultsContent" style="display: none;">
                            <div id="messageType" class="mb-3"></div>
                            
                            <ul class="nav nav-tabs" id="resultsTabs" role="tablist">
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link active" id="summary-tab" data-bs-toggle="tab" data-bs-target="#summary" type="button" role="tab" aria-controls="summary" aria-selected="true">Summary</button>
                                </li>
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link" id="transaction-tab" data-bs-toggle="tab" data-bs-target="#transaction" type="button" role="tab" aria-controls="transaction" aria-selected="false">Transaction</button>
                                </li>
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link" id="fraud-tab" data-bs-toggle="tab" data-bs-target="#fraud" type="button" role="tab" aria-controls="fraud" aria-selected="false">Fraud Analysis</button>
                                </li>
                                <li class="nav-item" role="presentation">
                                    <button class="nav-link" id="json-tab" data-bs-toggle="tab" data-bs-target="#json" type="button" role="tab" aria-controls="json" aria-selected="false">JSON</button>
                                </li>
                            </ul>
                            
                            <div class="tab-content" id="resultsTabContent">
                                <div class="tab-pane fade show active" id="summary" role="tabpanel" aria-labelledby="summary-tab">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <h5>Input</h5>
                                            <div class="mb-2">
                                                <span class="transaction-label">SMS Text:</span> 
                                                <span id="summaryText"></span>
                                            </div>
                                            <div class="mb-2">
                                                <span class="transaction-label">Sender:</span> 
                                                <span id="summarySender"></span>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <h5>Results</h5>
                                            <div class="mb-2">
                                                <span class="transaction-label">Type:</span> 
                                                <span id="summaryType"></span>
                                            </div>
                                            <div class="mb-2">
                                                <span class="transaction-label">Processing Time:</span> 
                                                <span id="summaryTime"></span>
                                            </div>
                                            <div class="mb-2" id="summarySavedDiv" style="display: none;">
                                                <span class="transaction-label">Saved:</span> 
                                                <span id="summarySaved"></span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="tab-pane fade" id="transaction" role="tabpanel" aria-labelledby="transaction-tab">
                                    <div id="transactionDetails"></div>
                                </div>
                                
                                <div class="tab-pane fade" id="fraud" role="tabpanel" aria-labelledby="fraud-tab">
                                    <div id="fraudDetails"></div>
                                </div>
                                
                                <div class="tab-pane fade" id="json" role="tabpanel" aria-labelledby="json-tab">
                                    <pre id="jsonDisplay"></pre>
                                </div>
                            </div>
                        </div>
                        
                        <div id="errorMessage" class="alert alert-danger mt-3" style="display: none;"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-5">
            <div class="col-md-12">
                <ul class="nav nav-tabs" id="historyTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="transactions-tab" data-bs-toggle="tab" data-bs-target="#transactions" type="button" role="tab" aria-controls="transactions" aria-selected="true">Recent Transactions</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="frauds-tab" data-bs-toggle="tab" data-bs-target="#frauds" type="button" role="tab" aria-controls="frauds" aria-selected="false">Recent Fraud</button>
                    </li>
                </ul>
                
                <div class="tab-content" id="historyTabContent">
                    <div class="tab-pane fade show active" id="transactions" role="tabpanel" aria-labelledby="transactions-tab">
                        <div id="transactionsLoading" class="text-center py-3">
                            <div class="spinner-border spinner-border-sm text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <span>Loading transactions...</span>
                        </div>
                        <div id="transactionsContent"></div>
                        <div id="noTransactions" class="text-center py-3" style="display: none;">
                            <p>No transactions found</p>
                        </div>
                    </div>
                    
                    <div class="tab-pane fade" id="frauds" role="tabpanel" aria-labelledby="frauds-tab">
                        <div id="fraudsLoading" class="text-center py-3">
                            <div class="spinner-border spinner-border-sm text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <span>Loading fraud logs...</span>
                        </div>
                        <div id="fraudsContent"></div>
                        <div id="noFrauds" class="text-center py-3" style="display: none;">
                            <p>No fraud logs found</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const smsForm = document.getElementById('smsForm');
            const resultsSection = document.getElementById('resultsSection');
            const loadingIndicator = document.getElementById('loadingIndicator');
            const resultsContent = document.getElementById('resultsContent');
            const errorMessage = document.getElementById('errorMessage');
            
            // Load recent transactions and fraud logs
            loadRecentTransactions();
            loadRecentFraud();
            
            // Toggle tabs on first click
            document.querySelectorAll('#historyTabs button').forEach(tab => {
                tab.addEventListener('shown.bs.tab', function(e) {
                    if (e.target.id === 'transactions-tab') {
                        loadRecentTransactions();
                    } else if (e.target.id === 'frauds-tab') {
                        loadRecentFraud();
                    }
                });
            });
            
            smsForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const smsText = document.getElementById('smsText').value;
                const smsSender = document.getElementById('smsSender').value;
                const saveDatabase = document.getElementById('saveDatabase').checked;
                
                if (!smsText.trim()) {
                    showError('Please enter an SMS message to analyze');
                    return;
                }
                
                // Show loading and reset error state
                resultsSection.style.display = 'block';
                loadingIndicator.style.display = 'block';
                resultsContent.style.display = 'none';
                errorMessage.style.display = 'none';
                
                // Scroll to results
                resultsSection.scrollIntoView({ behavior: 'smooth' });
                
                // Call API to parse SMS
                fetch('/api/parse', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        sms_text: smsText,
                        sender: smsSender || null,
                        save: saveDatabase
                    }),
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Hide loading
                    loadingIndicator.style.display = 'none';
                    resultsContent.style.display = 'block';
                    
                    // Display results
                    displayResults(data, smsText, smsSender);
                    
                    // Reload history if data was saved
                    if (saveDatabase) {
                        setTimeout(() => {
                            loadRecentTransactions();
                            loadRecentFraud();
                        }, 500);
                    }
                })
                .catch(error => {
                    loadingIndicator.style.display = 'none';
                    showError('Error analyzing SMS: ' + error.message);
                });
            });
            
            function displayResults(data, smsText, sender) {
                // Format JSON display
                document.getElementById('jsonDisplay').textContent = JSON.stringify(data, null, 2);
                
                // Fill summary tab
                document.getElementById('summaryText').textContent = smsText;
                document.getElementById('summarySender').textContent = sender || '(Not specified)';
                
                // Processing time
                const processingTime = data.metadata?.processing_time_ms || 0;
                document.getElementById('summaryTime').textContent = `${processingTime.toFixed(2)} ms`;
                
                // Saved status
                if (data.metadata?.saved) {
                    document.getElementById('summarySavedDiv').style.display = 'block';
                    document.getElementById('summarySaved').textContent = 
                        `Yes (as ${data.metadata.saved_as}, ID: ${data.metadata.record_id})`;
                } else {
                    document.getElementById('summarySavedDiv').style.display = 'none';
                }
                
                // Determine type of message
                const isPromotional = data.is_promotional || false;
                const transaction = data.transaction || {};
                const fraudDetection = data.fraud_detection || {};
                const isSuspicious = fraudDetection.is_suspicious || false;
                const riskLevel = fraudDetection.risk_level || 'none';
                const hasTransaction = transaction.transaction_amount || transaction.amount;
                
                let messageTypeHTML = '';
                let messageType = '';
                
                if (isPromotional) {
                    messageTypeHTML = '<div class="promotional p-3 mb-3"><h4>PROMOTIONAL SMS</h4></div>';
                    messageType = 'Promotional';
                } else if (isSuspicious && riskLevel !== 'none') {
                    messageTypeHTML = `<div class="fraudulent p-3 mb-3"><h4>FRAUDULENT SMS - ${riskLevel.toUpperCase()} RISK</h4></div>`;
                    messageType = 'Fraudulent';
                } else if (hasTransaction) {
                    messageTypeHTML = '<div class="transaction p-3 mb-3"><h4>BANKING TRANSACTION</h4></div>';
                    messageType = 'Banking Transaction';
                } else {
                    messageTypeHTML = '<div class="generic p-3 mb-3"><h4>GENERIC SMS</h4></div>';
                    messageType = 'Generic';
                }
                
                document.getElementById('messageType').innerHTML = messageTypeHTML;
                document.getElementById('summaryType').textContent = messageType;
                
                // Transaction details
                if (hasTransaction) {
                    const transactionHTML = `
                        <div class="mb-3">
                            <div class="mb-2"><span class="transaction-label">Amount:</span> ₹${(transaction.transaction_amount || transaction.amount || 0).toFixed(2)}</div>
                            <div class="mb-2"><span class="transaction-label">Type:</span> ${(transaction.transaction_type || 'unknown').toUpperCase()}</div>
                            ${transaction.merchant || transaction.merchant_name ? `<div class="mb-2"><span class="transaction-label">Merchant:</span> ${transaction.merchant || transaction.merchant_name}</div>` : ''}
                            ${transaction.category ? `<div class="mb-2"><span class="transaction-label">Category:</span> ${transaction.category}</div>` : ''}
                            ${transaction.account_number || transaction.account_masked || transaction.account ? `<div class="mb-2"><span class="transaction-label">Account:</span> ${transaction.account_number || transaction.account_masked || transaction.account}</div>` : ''}
                            ${transaction.available_balance ? `<div class="mb-2"><span class="transaction-label">Available Balance:</span> ₹${transaction.available_balance.toFixed(2)}</div>` : ''}
                            ${transaction.date || transaction.transaction_date ? `<div class="mb-2"><span class="transaction-label">Date:</span> ${transaction.date || transaction.transaction_date}</div>` : ''}
                        </div>
                    `;
                    document.getElementById('transactionDetails').innerHTML = transactionHTML;
                } else {
                    document.getElementById('transactionDetails').innerHTML = '<p>No transaction details available</p>';
                }
                
                // Fraud details
                let fraudHTML = `
                    <div class="mb-3">
                        <div class="mb-2"><span class="transaction-label">Suspicious:</span> ${isSuspicious}</div>
                        <div class="mb-2"><span class="transaction-label">Risk Level:</span> ${riskLevel.toUpperCase()}</div>
                `;
                
                if (fraudDetection.suspicious_indicators && fraudDetection.suspicious_indicators.length > 0) {
                    fraudHTML += `<div class="mb-2"><span class="transaction-label">Suspicious Indicators:</span>`;
                    fraudDetection.suspicious_indicators.forEach(indicator => {
                        fraudHTML += `<span class="indicator">${indicator}</span> `;
                    });
                    fraudHTML += `</div>`;
                }
                
                fraudHTML += `</div>`;
                document.getElementById('fraudDetails').innerHTML = fraudHTML;
            }
            
            function showError(message) {
                resultsSection.style.display = 'block';
                loadingIndicator.style.display = 'none';
                resultsContent.style.display = 'none';
                errorMessage.style.display = 'block';
                errorMessage.textContent = message;
            }
            
            function loadRecentTransactions() {
                document.getElementById('transactionsLoading').style.display = 'block';
                document.getElementById('transactionsContent').style.display = 'none';
                document.getElementById('noTransactions').style.display = 'none';
                
                fetch('/api/recent-transactions')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('transactionsLoading').style.display = 'none';
                        
                        if (data.length === 0) {
                            document.getElementById('noTransactions').style.display = 'block';
                            return;
                        }
                        
                        let html = '';
                        data.forEach(transaction => {
                            html += `
                                <div class="sms-history-item">
                                    <div><strong>SMS:</strong> ${transaction.raw_sms}</div>
                                    <div class="mt-2">
                                        <span class="badge bg-primary">${transaction.type}</span>
                                        <span class="badge bg-success">₹${transaction.amount}</span>
                                        ${transaction.merchant ? `<span class="badge bg-info">${transaction.merchant}</span>` : ''}
                                        ${transaction.category ? `<span class="badge bg-secondary">${transaction.category}</span>` : ''}
                                    </div>
                                    <div class="mt-1 text-muted small">
                                        <span>ID: ${transaction.id}</span> • 
                                        <span>Sender: ${transaction.sender || 'unknown'}</span> • 
                                        <span>Date: ${transaction.date || 'unknown'}</span>
                                    </div>
                                </div>
                            `;
                        });
                        
                        document.getElementById('transactionsContent').innerHTML = html;
                        document.getElementById('transactionsContent').style.display = 'block';
                    })
                    .catch(error => {
                        document.getElementById('transactionsLoading').style.display = 'none';
                        document.getElementById('transactionsContent').innerHTML = `
                            <div class="alert alert-danger">Error loading transactions: ${error.message}</div>
                        `;
                        document.getElementById('transactionsContent').style.display = 'block';
                    });
            }
            
            function loadRecentFraud() {
                document.getElementById('fraudsLoading').style.display = 'block';
                document.getElementById('fraudsContent').style.display = 'none';
                document.getElementById('noFrauds').style.display = 'none';
                
                fetch('/api/recent-fraud')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('fraudsLoading').style.display = 'none';
                        
                        if (data.length === 0) {
                            document.getElementById('noFrauds').style.display = 'block';
                            return;
                        }
                        
                        let html = '';
                        data.forEach(fraud => {
                            const riskClass = fraud.risk_level === 'high' ? 'bg-danger' : 
                                             (fraud.risk_level === 'medium' ? 'bg-warning text-dark' : 'bg-info text-dark');
                            
                            html += `
                                <div class="sms-history-item">
                                    <div><strong>SMS:</strong> ${fraud.raw_sms}</div>
                                    <div class="mt-2">
                                        <span class="badge ${riskClass}">${fraud.risk_level.toUpperCase()} RISK</span>
                                    </div>
                                    <div class="mt-2">
                                        <strong>Indicators:</strong> 
                                        ${fraud.suspicious_indicators.map(i => `<span class="indicator">${i}</span>`).join(' ')}
                                    </div>
                                    <div class="mt-1 text-muted small">
                                        <span>ID: ${fraud.id}</span> • 
                                        <span>Sender: ${fraud.sender || 'unknown'}</span>
                                    </div>
                                </div>
                            `;
                        });
                        
                        document.getElementById('fraudsContent').innerHTML = html;
                        document.getElementById('fraudsContent').style.display = 'block';
                    })
                    .catch(error => {
                        document.getElementById('fraudsLoading').style.display = 'none';
                        document.getElementById('fraudsContent').innerHTML = `
                            <div class="alert alert-danger">Error loading fraud logs: ${error.message}</div>
                        `;
                        document.getElementById('fraudsContent').style.display = 'block';
                    });
            }
        });
    </script>
</body>
</html>''')
    
    return True

if __name__ == '__main__':
    # Initialize database
    setup_database()
    
    # Create templates directory and files
    create_templates()
    
    # Start the Flask app
    print("Starting SMS Analyzer Web Interface on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 