#!/usr/bin/env python3

import argparse
import json
import sys
import pprint
import datetime
import os
from typing import Dict, Any, List
from enhanced_sms_parser import run_end_to_end
import db

def process_single_sms(sms_text: str, output_file: str = None) -> Dict[str, Any]:
    """
    Process a single SMS message
    
    Args:
        sms_text: The SMS text to process
        output_file: Optional file to save output
        
    Returns:
        The result dictionary
    """
    print(f"\nProcessing SMS: {sms_text}")
    print("-" * 50)
    
    try:
        # Run end-to-end processing
        result = run_end_to_end(sms_text)
        
        # Save to output file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nResults saved to {output_file}")
        
        return result
    
    except Exception as e:
        print(f"Error processing SMS: {e}")
        return {"error": str(e), "sms": sms_text}

def process_batch_file(file_path: str, output_file: str = None) -> List[Dict[str, Any]]:
    """
    Process multiple SMS messages from a file
    
    Args:
        file_path: Path to a text file with one SMS per line
        output_file: Optional file to save output
        
    Returns:
        List of result dictionaries
    """
    print(f"Processing SMS messages from file: {file_path}")
    results = []
    
    try:
        # Read SMS messages from file
        with open(file_path, 'r') as f:
            sms_messages = [line.strip() for line in f if line.strip()]
        
        total = len(sms_messages)
        print(f"Found {total} SMS messages in file.")
        
        # Process each SMS
        for i, sms in enumerate(sms_messages):
            print(f"\n[{i+1}/{total}] Processing SMS: {sms[:50]}{'...' if len(sms) > 50 else ''}")
            print("-" * 50)
            
            try:
                result = run_end_to_end(sms)
                results.append(result)
                
                # Print a brief summary
                print(f"Transaction: {result['transaction']['amount']} {result['transaction']['transaction_type']}")
                print(f"Category: {result['category']}")
                print(f"Archetype: {result['archetype']}")
            
            except Exception as e:
                print(f"Error processing SMS: {e}")
                results.append({"error": str(e), "sms": sms})
        
        # Save all results to output file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nAll results saved to {output_file}")
        
        return results
    
    except Exception as e:
        print(f"Error processing batch file: {e}")
        return [{"error": str(e), "file": file_path}]

def show_balances():
    """Show account balances"""
    try:
        balances = db.get_balances()
        
        if not balances:
            print("No account balances found.")
            return
        
        print("\n=== ACCOUNT BALANCES ===")
        total = 0
        for bal in balances:
            print(f"Account: {bal['account']}  |  Balance: ₹{bal['balance']:,.2f}  |  Last Updated: {bal['last_updated']}")
            total += bal['balance']
        
        print("-" * 60)
        print(f"Total Balance: ₹{total:,.2f}")
    except Exception as e:
        print(f"Error retrieving balances: {e}")

def show_subscriptions():
    """Show active subscriptions"""
    try:
        subscriptions = db.get_subscriptions()
        
        if not subscriptions:
            print("No active subscriptions found.")
            return
        
        print("\n=== ACTIVE SUBSCRIPTIONS ===")
        total = 0
        for sub in subscriptions:
            recurring = "✓ Recurring" if sub['recurring'] else "✗ Not recurring"
            print(f"Merchant: {sub['merchant']}")
            print(f"  Amount: ₹{sub['amount']:,.2f}")
            print(f"  Account: {sub['account']}")
            print(f"  Last Paid: {sub['last_paid']}  |  Next Due: {sub['next_due']}  |  {recurring}")
            print("-" * 60)
            total += sub['amount']
        
        print(f"Total Monthly Cost: ₹{total:,.2f}")
    except Exception as e:
        print(f"Error retrieving subscriptions: {e}")

def show_reminders(days: int = 3):
    """Show upcoming payment reminders"""
    try:
        reminders = db.get_upcoming_reminders(days)
        
        if not reminders:
            print(f"No payment reminders due in the next {days} days.")
            return
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n=== UPCOMING PAYMENTS (Next {days} days) ===")
        for reminder in reminders:
            recurring = "✓ Recurring" if reminder['recurring'] else "✗ One-time"
            due_date = reminder['due_date']
            
            # Check if due today
            if due_date == today:
                due_str = "DUE TODAY!"
            else:
                due_days = (datetime.datetime.strptime(due_date, "%Y-%m-%d") - 
                           datetime.datetime.strptime(today, "%Y-%m-%d")).days
                due_str = f"Due in {due_days} days"
            
            print(f"Merchant: {reminder['merchant']}  |  Amount: ₹{reminder['amount']:,.2f}  |  {due_str}")
            print(f"  Account: {reminder['account']}  |  {recurring}")
            print("-" * 60)
    except Exception as e:
        print(f"Error retrieving reminders: {e}")

def show_insights(month: str = None):
    """Show financial insights"""
    try:
        insights = db.get_insights(month)
        
        if not insights:
            print("No financial data available for insights.")
            return
        
        month_display = insights.get('month', 'All time')
        
        print(f"\n=== FINANCIAL INSIGHTS ({month_display}) ===")
        print(f"Monthly Income: ₹{insights['monthly_income']:,.2f}")
        print(f"Monthly Spend: ₹{insights['monthly_spend']:,.2f}")
        
        # Calculate net savings
        net_savings = insights['monthly_income'] - insights['monthly_spend']
        print(f"Net Savings: ₹{net_savings:,.2f}")
        
        # Savings rate as percentage
        savings_rate = insights['savings_rate'] * 100
        print(f"Savings Rate: {savings_rate:.1f}%")
        
        print(f"Average Transaction: ₹{insights['average_transaction']:,.2f}")
        print(f"Subscription Spend: ₹{insights['subscription_spend']:,.2f}")
        
        # Show category breakdown
        print("\n--- Category Breakdown ---")
        for category, amount in insights['category_spend'].items():
            percentage = (amount / insights['monthly_spend'] * 100) if insights['monthly_spend'] > 0 else 0
            print(f"{category}: ₹{amount:,.2f} ({percentage:.1f}%)")
        
        # Show day of week spending
        print("\n--- Day of Week Spending ---")
        for day, amount in insights['day_of_week_spend'].items():
            if amount > 0:
                percentage = (amount / insights['monthly_spend'] * 100) if insights['monthly_spend'] > 0 else 0
                print(f"{day}: ₹{amount:,.2f} ({percentage:.1f}%)")
    except Exception as e:
        print(f"Error retrieving insights: {e}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="SMS Transaction Parser CLI")
    
    # Create command groups
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--sms", help="Single SMS message to process")
    group.add_argument("-f", "--file", help="File containing SMS messages (one per line)")
    group.add_argument("-b", "--balances", action="store_true", help="Show account balances")
    group.add_argument("-sub", "--subscriptions", action="store_true", help="Show active subscriptions")
    group.add_argument("-r", "--reminders", action="store_true", help="Show upcoming payment reminders")
    group.add_argument("-i", "--insights", action="store_true", help="Show financial insights")
    group.add_argument("--init-db", action="store_true", help="Initialize or reset the database")
    
    # Output file option
    parser.add_argument("-o", "--output", help="Output file to save results (JSON)")
    
    # Additional arguments for specific commands
    parser.add_argument("--days", type=int, default=3, help="Days ahead for reminders (default: 3)")
    parser.add_argument("--month", help="Month for insights in YYYY-MM format (default: current month)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize database if requested or if it doesn't exist
    if args.init_db or not os.path.exists(db.DB_FILE):
        db.init_db()
    else:
        # Just print that the database is initialized
        print("Database initialized successfully")
    
    # Process based on command
    if args.sms:
        result = process_single_sms(args.sms, args.output)
        print("\nResult:")
        pprint.pprint(result)
    
    elif args.file:
        results = process_batch_file(args.file, args.output)
        print(f"\nProcessed {len(results)} SMS messages")
        print(f"Successful: {len([r for r in results if 'error' not in r])}")
        print(f"Failed: {len([r for r in results if 'error' in r])}")
    
    elif args.balances:
        show_balances()
    
    elif args.subscriptions:
        show_subscriptions()
    
    elif args.reminders:
        show_reminders(args.days)
    
    elif args.insights:
        show_insights(args.month)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 