#!/usr/bin/env python3

from flask import Flask, render_template, request, flash, redirect, url_for
from sms_parser.parsers.gemini_parser import parse_sms
from sms_parser.core.database import init_database, save_transaction, save_fraud_log, save_promotional_sms
from sms_parser.core.logger import get_logger

app = Flask(__name__, template_folder='../templates')
app.secret_key = 'your-secret-key-here'  # Change this in production
logger = get_logger(__name__)

# Initialize database
init_database()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse():
    sms_text = request.form.get('sms_text')
    sender = request.form.get('sender')

    if not sms_text:
        flash('Please enter an SMS message', 'error')
        return redirect(url_for('index'))

    try:
        result = parse_sms(sms_text, sender)
        
        # Save results based on type
        if result.get('type') == 'transaction':
            save_transaction(result)
        elif result.get('type') == 'fraud':
            save_fraud_log(result)
        elif result.get('type') == 'promotional':
            save_promotional_sms(result)

        return render_template('index.html', result=result, sms_text=sms_text)
    except Exception as e:
        logger.error(f"Error parsing SMS: {str(e)}")
        flash(f'Error parsing SMS: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 