#!/usr/bin/env python3
"""
SMS Parser Web Interface
=======================
A simple web interface for testing the SMS parser with various examples.
"""

import os
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import (
    Flask, 
    render_template, 
    request, 
    jsonify, 
    redirect, 
    url_for, 
    session, 
    flash
)

from sms_parser.tests.test_sms_examples import get_test_sms
from sms_parser.cli.main import process_sms
from sms_parser.core.logger import get_logger
from sms_parser.parsers.gemini_parser import parse_sms
from sms_parser.tests.test_sms_examples import (
    ALL_EXAMPLES, 
    get_random_example, 
    get_example_by_category,
    get_examples_by_type
)

logger = get_logger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_sms_parser')
app.config['SESSION_TYPE'] = 'filesystem'

# Store recent SMS analysis results
RECENT_RESULTS = []
MAX_RECENT_RESULTS = 10

# List of example categories for the UI
EXAMPLE_CATEGORIES = list(ALL_EXAMPLES.keys()) if ALL_EXAMPLES else [
    "banking",
    "credit_card_offers",
    "promotional",
    "wallet",
    "fraudulent",
    "otp",
    "upi",
    "account_updates",
    "edge_cases"
]

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
        result = parse_sms(sms_text, sender)
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

def store_recent_result(sms_text: str, sender: str, result: Dict[str, Any]) -> None:
    """Store a recent SMS analysis result"""
    global RECENT_RESULTS
    
    # Create a summary result
    is_promotional = result.get("is_promotional", False)
    is_suspicious = result.get("fraud_detection", {}).get("is_suspicious", False)
    risk_level = result.get("fraud_detection", {}).get("risk_level", "none")
    
    transaction = result.get("transaction", {})
    amount = transaction.get("amount", 0)
    txn_type = transaction.get("transaction_type", "unknown")
    merchant = transaction.get("merchant", None)
    
    summary = {
        "id": result.get("metadata", {}).get("request_id", str(uuid.uuid4())),
        "timestamp": datetime.now().isoformat(),
        "sms_text": sms_text[:100] + "..." if len(sms_text) > 100 else sms_text,
        "sender": sender,
        "is_promotional": is_promotional,
        "is_suspicious": is_suspicious,
        "risk_level": risk_level,
        "transaction_type": txn_type,
        "amount": amount,
        "merchant": merchant,
        "processing_time": result.get("metadata", {}).get("processing_time_ms", 0)
    }
    
    # Add to recent results
    RECENT_RESULTS.insert(0, summary)
    
    # Limit the size of recent results
    if len(RECENT_RESULTS) > MAX_RECENT_RESULTS:
        RECENT_RESULTS = RECENT_RESULTS[:MAX_RECENT_RESULTS]

@app.route('/')
def index():
    """Render the main page"""
    return render_template(
        'index.html', 
        categories=EXAMPLE_CATEGORIES,
        recent_results=RECENT_RESULTS
    )

@app.route('/parse', methods=['POST'])
def parse_sms_route():
    """Parse an SMS message from form submission"""
    sms_text = request.form.get('sms_text', '')
    sender = request.form.get('sender', '')
    
    if not sms_text:
        flash('Please enter an SMS message to parse.', 'error')
        return redirect(url_for('index'))
    
    # Parse the SMS
    result = parse_single_sms(sms_text, sender)
    
    # Store in recent results
    store_recent_result(sms_text, sender, result)
    
    # Store in session for result page
    session['last_result'] = result
    session['last_sms'] = sms_text
    session['last_sender'] = sender
    
    return redirect(url_for('result'))

@app.route('/example/<category>')
def load_example(category):
    """Load a random example from a category"""
    example = get_example_by_category(category)
    
    if not example:
        flash(f'No examples found for category: {category}', 'error')
        return redirect(url_for('index'))
    
    # Parse the SMS
    result = parse_single_sms(example['sms'], example['sender'])
    
    # Store in recent results
    store_recent_result(example['sms'], example['sender'], result)
    
    # Store in session for result page
    session['last_result'] = result
    session['last_sms'] = example['sms']
    session['last_sender'] = example['sender']
    session['example_description'] = example.get('description', '')
    
    return redirect(url_for('result'))

@app.route('/random')
def load_random_example():
    """Load a random example"""
    example = get_random_example()
    
    if not example:
        flash('No examples available.', 'error')
        return redirect(url_for('index'))
    
    # Parse the SMS
    result = parse_single_sms(example['sms'], example['sender'])
    
    # Store in recent results
    store_recent_result(example['sms'], example['sender'], result)
    
    # Store in session for result page
    session['last_result'] = result
    session['last_sms'] = example['sms']
    session['last_sender'] = example['sender']
    session['example_description'] = example.get('description', '')
    
    return redirect(url_for('result'))

@app.route('/result')
def result():
    """Show the result of a parsed SMS"""
    result = session.get('last_result')
    sms = session.get('last_sms')
    sender = session.get('last_sender')
    description = session.get('example_description')
    
    if not result or not sms:
        flash('No parsing result found. Please parse an SMS first.', 'error')
        return redirect(url_for('index'))
    
    return render_template(
        'result.html',
        result=result,
        sms=sms,
        sender=sender,
        description=description,
        categories=EXAMPLE_CATEGORIES
    )

@app.route('/api/parse', methods=['POST'])
def api_parse():
    """API endpoint for parsing SMS messages"""
    data = request.json
    
    if not data or 'sms' not in data:
        return jsonify({
            'error': 'Missing required field: sms',
            'status': 'error'
        }), 400
    
    sms_text = data['sms']
    sender = data.get('sender', None)
    
    # Parse the SMS
    result = parse_single_sms(sms_text, sender)
    
    # Store in recent results
    store_recent_result(sms_text, sender, result)
    
    return jsonify({
        'status': 'success',
        'result': result
    })

@app.route('/api/examples', methods=['GET'])
def api_examples():
    """API endpoint to get available examples"""
    category = request.args.get('category', None)
    
    if category:
        examples = get_example_by_category(category)
        if not examples:
            return jsonify({
                'error': f'No examples found for category: {category}',
                'status': 'error'
            }), 404
        return jsonify({
            'status': 'success',
            'examples': examples
        })
    
    return jsonify({
        'status': 'success',
        'categories': EXAMPLE_CATEGORIES,
        'all_examples': ALL_EXAMPLES
    })

@app.route('/clear-recent', methods=['POST'])
def clear_recent():
    """Clear recent results"""
    global RECENT_RESULTS
    RECENT_RESULTS = []
    flash('Recent results cleared.', 'success')
    return redirect(url_for('index'))

# Create templates directory and essential templates
def create_templates():
    """Create Flask templates if they don't exist"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create base template
    base_template = os.path.join(templates_dir, 'base.html')
    if not os.path.exists(base_template):
        with open(base_template, 'w') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}SMS Parser{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            padding-top: 20px;
            padding-bottom: 20px;
            background-color: #f8f9fa;
        }
        .card {
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .navbar {
            margin-bottom: 20px;
            background-color: #343a40;
        }
        .navbar-brand {
            font-weight: bold;
            color: white !important;
        }
        .result-header {
            padding: 10px;
            font-weight: bold;
        }
        .promotional {
            background-color: #fff3cd;
        }
        .suspicious {
            background-color: #f8d7da;
        }
        .transaction {
            background-color: #d1e7dd;
        }
        .json-viewer {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0.25rem;
            padding: 15px;
            max-height: 500px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9em;
        }
        pre {
            white-space: pre-wrap;
        }
        .badge-debit {
            background-color: #dc3545;
            color: white;
        }
        .badge-credit {
            background-color: #198754;
            color: white;
        }
        .badge-promotional {
            background-color: #ffc107;
            color: #000;
        }
        .badge-suspicious {
            background-color: #dc3545;
            color: white;
        }
        .sms-text {
            font-family: monospace;
            background-color: #e9ecef;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .recent-item {
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .recent-item:hover {
            background-color: #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark rounded">
            <div class="container-fluid">
                <a class="navbar-brand" href="/">SMS Parser</a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarNav">
                    <ul class="navbar-nav">
                        <li class="nav-item">
                            <a class="nav-link" href="/">Home</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/random">Random Example</a>
                        </li>
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                Examples
                            </a>
                            <ul class="dropdown-menu" aria-labelledby="navbarDropdown">
                                {% for category in categories %}
                                <li><a class="dropdown-item" href="/example/{{ category }}">{{ category|replace('_', ' ')|title }}</a></li>
                                {% endfor %}
                            </ul>
                        </li>
                    </ul>
                </div>
            </div>
        </nav>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }}" role="alert">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function syntaxHighlight(json) {
            if (typeof json != 'string') {
                json = JSON.stringify(json, undefined, 2);
            }
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                var cls = 'number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'key';
                    } else {
                        cls = 'string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'boolean';
                } else if (/null/.test(match)) {
                    cls = 'null';
                }
                return '<span class="' + cls + '">' + match + '</span>';
            });
        }

        document.addEventListener('DOMContentLoaded', function() {
            const jsonElements = document.querySelectorAll('.json-data');
            jsonElements.forEach(function(element) {
                try {
                    const jsonData = JSON.parse(element.textContent);
                    element.innerHTML = syntaxHighlight(jsonData);
                } catch (e) {
                    console.error('Error parsing JSON:', e);
                }
            });
        });
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>""")
    
    # Create index template
    index_template = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(index_template):
        with open(index_template, 'w') as f:
            f.write("""{% extends 'base.html' %}

{% block title %}SMS Parser - Home{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title">Parse SMS</h5>
            </div>
            <div class="card-body">
                <form action="/parse" method="post">
                    <div class="mb-3">
                        <label for="sms_text" class="form-label">SMS Text</label>
                        <textarea class="form-control" id="sms_text" name="sms_text" rows="4" required></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="sender" class="form-label">Sender (optional)</label>
                        <input type="text" class="form-control" id="sender" name="sender" placeholder="e.g. HDFCBK, TX-NOTIFY">
                    </div>
                    <button type="submit" class="btn btn-primary">Parse SMS</button>
                </form>
            </div>
            <div class="card-footer">
                <div class="btn-group" role="group" aria-label="Example buttons">
                    <a href="/random" class="btn btn-outline-secondary btn-sm">Random Example</a>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                            Examples
                        </button>
                        <ul class="dropdown-menu">
                            {% for category in categories %}
                            <li><a class="dropdown-item" href="/example/{{ category }}">{{ category|replace('_', ' ')|title }}</a></li>
                            {% endfor %}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-6">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">Recent Results</h5>
                {% if recent_results %}
                <form action="/clear-recent" method="post" class="m-0">
                    <button type="submit" class="btn btn-sm btn-outline-danger">Clear</button>
                </form>
                {% endif %}
            </div>
            <div class="card-body p-0">
                {% if recent_results %}
                <div class="list-group list-group-flush">
                    {% for item in recent_results %}
                    <a href="#" class="list-group-item list-group-item-action recent-item">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">
                                {% if item.is_promotional %}
                                <span class="badge badge-promotional">Promotional</span>
                                {% elif item.is_suspicious %}
                                <span class="badge badge-suspicious">Suspicious ({{ item.risk_level|upper }})</span>
                                {% else %}
                                <span class="badge badge-{{ item.transaction_type }}">{{ item.transaction_type|upper }}</span>
                                {% endif %}
                                
                                {% if item.merchant %}
                                {{ item.merchant }}
                                {% else %}
                                {{ item.sender }}
                                {% endif %}
                            </h6>
                            <small>{{ item.processing_time }} ms</small>
                        </div>
                        <small class="text-muted">{{ item.sms_text }}</small>
                    </a>
                    {% endfor %}
                </div>
                {% else %}
                <div class="p-3 text-center text-muted">
                    <p>No recent results</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}""")
    
    # Create result template
    result_template = os.path.join(templates_dir, 'result.html')
    if not os.path.exists(result_template):
        with open(result_template, 'w') as f:
            f.write("""{% extends 'base.html' %}

{% block title %}SMS Parser - Result{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">
                    SMS Analysis
                    {% if description %}
                    <small class="text-muted">({{ description }})</small>
                    {% endif %}
                </h5>
                <a href="/" class="btn btn-sm btn-outline-secondary">Parse New SMS</a>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-12 mb-3">
                        <label class="form-label fw-bold">SMS Text:</label>
                        <div class="sms-text">{{ sms }}</div>
                        <div class="d-flex justify-content-between">
                            <span class="text-muted">Sender: {{ sender if sender else 'Not specified' }}</span>
                            <span class="text-muted">Processing Time: {{ result.metadata.processing_time_ms }} ms</span>
                        </div>
                    </div>
                </div>

                <div class="row">
                    {% set transaction = result.transaction %}
                    {% set fraud = result.fraud_detection %}
                    
                    <div class="col-md-6">
                        <!-- Classification Summary -->
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">Classification</h6>
                            </div>
                            <div class="card-body">
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Promotional:</span>
                                    <span class="badge {% if result.is_promotional %}bg-warning{% else %}bg-secondary{% endif %}">
                                        {{ "Yes" if result.is_promotional else "No" }}
                                    </span>
                                </div>
                                
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Suspicious:</span>
                                    <span class="badge {% if fraud.is_suspicious %}bg-danger{% else %}bg-success{% endif %}">
                                        {{ "Yes" if fraud.is_suspicious else "No" }}
                                    </span>
                                </div>
                                
                                {% if fraud.is_suspicious %}
                                <div class="d-flex justify-content-between">
                                    <span>Risk Level:</span>
                                    <span class="badge bg-danger">{{ fraud.risk_level|upper }}</span>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                        
                        {% if transaction %}
                        <!-- Transaction Details -->
                        <div class="card mt-3">
                            <div class="card-header">
                                <h6 class="mb-0">Transaction Details</h6>
                            </div>
                            <div class="card-body">
                                {% if transaction.amount %}
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Amount:</span>
                                    <span class="fw-bold">
                                        {{ transaction.currency|default('INR') }} {{ transaction.amount|float|round(2) }}
                                    </span>
                                </div>
                                {% endif %}
                                
                                {% if transaction.transaction_type %}
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Type:</span>
                                    <span class="badge {% if transaction.transaction_type == 'debit' %}bg-danger{% elif transaction.transaction_type == 'credit' %}bg-success{% else %}bg-secondary{% endif %}">
                                        {{ transaction.transaction_type|upper }}
                                    </span>
                                </div>
                                {% endif %}
                                
                                {% if transaction.account_number %}
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Account:</span>
                                    <span>{{ transaction.account_number }}</span>
                                </div>
                                {% endif %}
                                
                                {% if transaction.merchant %}
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Merchant:</span>
                                    <span>{{ transaction.merchant }}</span>
                                </div>
                                {% endif %}
                                
                                {% if transaction.category %}
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Category:</span>
                                    <span>{{ transaction.category }}</span>
                                </div>
                                {% endif %}
                                
                                {% if transaction.date %}
                                <div class="d-flex justify-content-between mb-3">
                                    <span>Date:</span>
                                    <span>{{ transaction.date }}</span>
                                </div>
                                {% endif %}
                                
                                {% if transaction.available_balance is defined %}
                                <div class="d-flex justify-content-between">
                                    <span>Available Balance:</span>
                                    <span>{{ transaction.currency|default('INR') }} {{ transaction.available_balance|float|round(2) }}</span>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                        {% endif %}
                    </div>
                    
                    <div class="col-md-6">
                        {% if fraud.is_suspicious and fraud.indicators %}
                        <!-- Fraud Indicators -->
                        <div class="card">
                            <div class="card-header bg-danger text-white">
                                <h6 class="mb-0">Suspicious Indicators</h6>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    {% for indicator in fraud.indicators %}
                                    <li class="list-group-item">{{ indicator }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                        </div>
                        {% endif %}
                        
                        <!-- Raw JSON Output -->
                        <div class="card mt-3">
                            <div class="card-header">
                                <h6 class="mb-0">Raw JSON Output</h6>
                            </div>
                            <div class="card-body p-0">
                                <div class="json-viewer">
                                    <pre class="json-data">{{ result|tojson(indent=2) }}</pre>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")

def main():
    """Main function to run the app"""
    # Create template files
    create_templates()
    
    # Set Flask environment variables
    os.environ['FLASK_APP'] = 'sms_web.py'
    os.environ['FLASK_ENV'] = 'development'
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main() 