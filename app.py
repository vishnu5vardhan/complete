from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import importlib.util
import os
import sys
import logging
import datetime
from dotenv import load_dotenv
import re

# Load environment variables - make sure this is at the top
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if enhanced_sms_parser.py is available and import it
if os.path.exists('enhanced_sms_parser.py'):
    spec = importlib.util.spec_from_file_location("enhanced_sms_parser", "enhanced_sms_parser.py")
    enhanced_sms_parser = importlib.util.module_from_spec(spec)
    sys.modules["enhanced_sms_parser"] = enhanced_sms_parser
    spec.loader.exec_module(enhanced_sms_parser)
    parse_sms = enhanced_sms_parser.parse_sms
    logger.info("Imported parse_sms from enhanced_sms_parser.py")
else:
    # Fallback import method
    try:
        from enhanced_sms_parser import parse_sms
        logger.info("Imported parse_sms using standard import")
    except ImportError:
        logger.error("Cannot import parse_sms function!")
        def parse_sms(sms_text, sender=None):
            return {"error": "SMS parsing module not available"}

# File to save high-risk SMS messages
HIGH_RISK_SMS_FILE = "high_risk_sms.txt"

app = Flask(__name__)

# Add CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def save_high_risk_sms(sms_text, sender, risk_level, indicators):
    """Save high-risk SMS to a file with timestamp and indicators."""
    if risk_level != "high":
        return
        
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(HIGH_RISK_SMS_FILE, "a") as f:
        f.write(f"[{timestamp}] RISK LEVEL: {risk_level}\n")
        f.write(f"SENDER: {sender or 'Unknown'}\n")
        f.write(f"INDICATORS: {', '.join(indicators)}\n")
        f.write(f"SMS: {sms_text}\n")
        f.write("-" * 80 + "\n")
    
    logger.info(f"High-risk SMS saved to {HIGH_RISK_SMS_FILE}")

@app.route('/')
def index():
    logger.debug("Serving index page")
    return render_template('index.html')

@app.route('/frontend/<path:path>')
def serve_frontend(path):
    logger.debug(f"Serving frontend file: {path}")
    return send_from_directory('frontend', path)

@app.route('/parse_sms', methods=['POST', 'OPTIONS'])
def analyze_sms():
    # Handle preflight request
    if request.method == 'OPTIONS':
        return _build_cors_preflight_response()
        
    try:
        # Get SMS text from form data or JSON
        data = request.get_json() if request.is_json else request.form
        
        if not data or 'sms_text' not in data:
            return jsonify({'error': 'No SMS text provided'}), 400
            
        sms_text = data['sms_text']
        sender = data.get('sender', None)
        
        logger.debug(f"SMS Text: {sms_text}")
        logger.debug(f"Sender: {sender}")
        logger.debug(f"Calling parse_sms function")
        
        # Parse SMS
        result = parse_sms(sms_text, sender)
        
        # Direct pattern matching to improve message type detection
        sms_lower = sms_text.lower()
        
        # Distinguish between legitimate bank messages and security alerts
        # Specific security alert patterns (not just customer service info)
        actual_security_alerts = [
            'not you?',
            'block upi',
            'suspicious transaction',
            'unauthorized transaction',
            'fraud alert',
            'suspicious activity',
            'unrecognized transaction'
        ]
        
        has_security_alert = any(pattern in sms_lower for pattern in actual_security_alerts)
        
        # Standard customer service patterns in legitimate bank messages
        customer_service_patterns = [
            'call .* for queries',
            'call .* for details',
            'call .* to report issue',
            'for support call',
            'customer care',
            'call toll free'
        ]
        
        # Don't mark as security alert if it's just a regular transaction with customer service info
        is_just_customer_service = (
            any(re.search(pattern, sms_lower) for pattern in customer_service_patterns) and
            not has_security_alert
        )
        
        # Only mark as security alert if it has an actual alert pattern
        if has_security_alert:
            # Mark as security alert
            result['message_type'] = 'security_alert'
            result['is_suspicious'] = True
            
            # But preserve transaction type if it's a mixed message
            if 'transaction_amount' in result and result['transaction_amount'] > 0:
                if 'sent' in sms_lower or 'debited' in sms_lower or 'paid' in sms_lower:
                    result['transaction_type'] = 'debit'
                elif 'received' in sms_lower or 'credited' in sms_lower:
                    result['transaction_type'] = 'credit'
                elif 'upi' in sms_lower:
                    result['transaction_type'] = 'upi'
                
                # Explicitly check for multi-line format with "To" line
                if '\n' in sms_text:
                    lines = sms_text.split('\n')
                    for line in lines:
                        if line.lower().startswith('to '):
                            merchant_name = line[3:].strip()
                            # Ensure we're not using a phone number as a merchant
                            if not re.match(r'^[\d\s\+\-]+$', merchant_name):
                                result['merchant'] = merchant_name
                                result['merchant_name'] = merchant_name
                                break
        elif is_just_customer_service and result.get('message_type') == 'security_alert':
            # Override incorrect security alert classification for regular bank messages
            result['message_type'] = 'transaction'
            result['is_suspicious'] = False
            if 'suspicious_indicators' in result:
                result['suspicious_indicators'] = []
            result['risk_level'] = 'none'
        
        # Direct balance update detection
        balance_patterns = [
            r'balance[^0-9]*(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)',
            r'bal[^0-9]*(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)',
            r'balance is (?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)',
            r'(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)[^0-9]*balance',
            r'(?:rs\.?|inr|₹)[\s]*(\d+(?:[,.]\d+)?)[^0-9]*bal',
            r'balance as of',
            r'current balance',
            r'available balance'
        ]
        balance_indicators = [
            "balance update", "current balance", "available balance", "a/c balance", 
            "avl bal", "available bal", "bal:", "balance is", "statement", "ministatement",
            "balance as of", "bal is", "balance:", "closing balance"
        ]
        
        is_balance_update = (
            any(re.search(pattern, sms_lower) for pattern in balance_patterns) or
            any(indicator in sms_lower for indicator in balance_indicators)
        )
        transaction_indicators = ["debited", "credited", "payment", "spent", "purchase", "transaction"]
        is_transaction = any(indicator in sms_lower for indicator in transaction_indicators)
        
        if is_balance_update and not is_transaction:
            # Override the message type
            result["message_type"] = "balance_update"
            
            # Extract amount if not present
            if "amount" not in result and "available_balance" not in result:
                for pattern in balance_patterns:
                    amount_match = re.search(pattern, sms_lower)
                    if amount_match and len(amount_match.groups()) > 0:
                        try:
                            amount = float(amount_match.group(1).replace(',', ''))
                            result["available_balance"] = amount
                            break
                        except (ValueError, IndexError):
                            pass
        
        # Ensure the response has a consistent structure with all required fields
        standardized_result = {
            'transaction': {
                'type': result.get('transaction_type', result.get('message_type', 'N/A')),
                'amount': result.get('amount', result.get('transaction_amount', 0.0)),
                'merchant': result.get('merchant_name', result.get('merchant', 'N/A')),
                'account': result.get('account_masked', result.get('account_number', 'N/A')),
                'date': result.get('date', 'N/A'),
                'balance': result.get('available_balance', 0.0),
                'category': result.get('category', 'Uncategorized')
            },
            'fraud_detection': {
                'risk_level': result.get('risk_level', 'none'),
                'is_suspicious': result.get('is_suspicious', False),
                'suspicious_indicators': result.get('suspicious_indicators', [])
            },
            'metadata': {
                'parsed_at': datetime.datetime.now().isoformat(),
                'message_type': result.get('message_type', 'other')
            }
        }
        
        # Check for promotional detection in a more comprehensive way
        is_promotional = (
            result.get('message_type') == 'promotional' or 
            result.get('is_promotional', False) or 
            (result.get('promotional_details', {}) and result.get('promotional_details', {}).get('is_promotional', False))
        )
        
        # Handle promotional messages
        if is_promotional:
            standardized_result['metadata']['message_type'] = 'promotional'
            standardized_result['transaction']['type'] = 'promotional'
            
            # Add promotional details if available
            if result.get('promotional_details'):
                standardized_result['promotional_details'] = result.get('promotional_details')
        
        # Special handling for security alerts
        elif 'message_type' in result and result['message_type'] == 'security_alert':
            standardized_result['metadata']['message_type'] = 'security_alert'
            standardized_result['fraud_detection']['risk_level'] = 'medium'
            
            if 'suspicious_indicators' not in standardized_result['fraud_detection'] or not standardized_result['fraud_detection']['suspicious_indicators']:
                standardized_result['fraud_detection']['suspicious_indicators'] = ['security_alert', 'action_required']
        
        # Special handling for balance updates
        elif 'message_type' in result and result['message_type'] == 'balance_update':
            standardized_result['metadata']['message_type'] = 'balance_update'
            standardized_result['transaction']['type'] = 'balance_update'
            
            # Remove suspicious indicators for balance updates
            standardized_result['fraud_detection']['is_suspicious'] = False
            standardized_result['fraud_detection']['risk_level'] = 'none'
            standardized_result['fraud_detection']['suspicious_indicators'] = []
        
        # Special handling for KYC scams and other phishing attempts
        if 'kyc' in sms_text.lower() and ('update' in sms_text.lower() or 'expire' in sms_text.lower()):
            standardized_result['metadata']['message_type'] = 'suspicious'
            standardized_result['fraud_detection']['is_suspicious'] = True
            standardized_result['fraud_detection']['risk_level'] = 'high'
            
            if 'suspicious_indicators' not in standardized_result['fraud_detection'] or not standardized_result['fraud_detection']['suspicious_indicators']:
                standardized_result['fraud_detection']['suspicious_indicators'] = ['kyc_scam', 'phishing_attempt']
            else:
                standardized_result['fraud_detection']['suspicious_indicators'].append('kyc_scam')
                standardized_result['fraud_detection']['suspicious_indicators'].append('phishing_attempt')
        
        # Check for suspicious URLs in the message
        if 'bit.ly' in sms_text or 'goo.gl' in sms_text or 'tinyurl' in sms_text:
            standardized_result['fraud_detection']['is_suspicious'] = True
            
            # Increase risk level if not already high
            if standardized_result['fraud_detection']['risk_level'] != 'high':
                standardized_result['fraud_detection']['risk_level'] = 'medium'
                
            # Add suspicious indicator if not already present
            if 'suspicious_indicators' not in standardized_result['fraud_detection'] or not standardized_result['fraud_detection']['suspicious_indicators']:
                standardized_result['fraud_detection']['suspicious_indicators'] = ['shortened_url']
            elif 'shortened_url' not in standardized_result['fraud_detection']['suspicious_indicators']:
                standardized_result['fraud_detection']['suspicious_indicators'].append('shortened_url')
        
        # Check if the SMS is high-risk and save it
        risk_level = standardized_result['fraud_detection']['risk_level']
        indicators = standardized_result['fraud_detection']['suspicious_indicators']
        
        # Save high-risk SMS to file
        if risk_level == 'high':
            save_high_risk_sms(sms_text, sender, risk_level, indicators)
        
        # Include original result for debugging purposes
        standardized_result['raw_response'] = result
        
        return jsonify(standardized_result)
    except Exception as e:
        logger.exception(f"Error in analyze_sms: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/high-risk-sms', methods=['GET'])
def get_high_risk_sms():
    """API endpoint to retrieve high-risk SMS messages."""
    try:
        if not os.path.exists(HIGH_RISK_SMS_FILE):
            return jsonify({"messages": [], "count": 0})
            
        with open(HIGH_RISK_SMS_FILE, "r") as f:
            content = f.read()
            
        # Split the content by the separator line
        messages_raw = content.split("-" * 80)
        messages = []
        
        for msg_raw in messages_raw:
            if not msg_raw.strip():
                continue
                
            lines = msg_raw.strip().split("\n")
            if len(lines) >= 4:
                timestamp = lines[0].strip()
                sender = lines[1].replace("SENDER:", "").strip()
                indicators = lines[2].replace("INDICATORS:", "").strip()
                sms = lines[3].replace("SMS:", "").strip()
                
                messages.append({
                    "timestamp": timestamp,
                    "sender": sender,
                    "indicators": indicators,
                    "sms": sms
                })
        
        return jsonify({
            "messages": messages,
            "count": len(messages)
        })
    except Exception as e:
        logger.exception(f"Error retrieving high-risk SMS: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Check API key configuration
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        exit(1)
        
    # Print environment for debugging
    logger.debug(f"GEMINI_API_KEY set: {bool(api_key)}")
    logger.debug(f"USE_MOCK_DATA: {os.getenv('USE_MOCK_DATA')}")
    logger.debug(f"ENABLE_MOCK_MODE: {os.getenv('ENABLE_MOCK_MODE')}")
    
    logger.info("Starting Flask app on port 5001")
    # Create the high-risk SMS file if it doesn't exist
    if not os.path.exists(HIGH_RISK_SMS_FILE):
        with open(HIGH_RISK_SMS_FILE, "w") as f:
            f.write(f"# High-Risk SMS Messages - Created on {datetime.datetime.now()}\n\n")
    
    app.run(debug=True, port=5001)
