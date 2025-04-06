#!/usr/bin/env python3

import db

def test_balance_extraction():
    """Test extracting balance from SMS messages"""
    print("=== TESTING BALANCE EXTRACTION ===")
    
    test_messages = [
        "Your card ending with 1234 has been debited for Rs.2500 at Swiggy on 05-04-2023. Available balance is Rs.45000.",
        "Rs.5000 credited to your account xxxx5678. Updated balance: Rs.50000.",
        "A payment of INR 1299 was made from your card ending 4321. Closing balance Rs.25,500.45",
        "Transaction Alert: INR 799 debited from account XXXX9876 at Amazon. Balance is Rs 15250."
    ]
    
    for msg in test_messages:
        balance = db.extract_balance_from_sms(msg)
        print(f"Message: {msg}")
        print(f"Extracted balance: {balance}")
        print("-" * 50)

def test_balance_updates():
    """Test updating balances in the database"""
    print("\n=== TESTING BALANCE UPDATES ===")
    
    # Initialize the database
    db.init_db()
    print("Database initialized.")
    
    # Test updating with explicit balance
    print("\nTest 1: Updating with explicit balance")
    db.update_balance("xxxx1234", 2500, "debit", explicit_balance=45000)
    
    # Test updating with transaction calculation
    print("\nTest 2: Updating with transaction calculation")
    db.update_balance("xxxx5678", 5000, "credit")
    
    # Test another debit transaction
    print("\nTest 3: Additional debit transaction")
    db.update_balance("xxxx1234", 1500, "debit")
    
    # Show all balances
    balances = db.get_balances()
    print("\nCurrent balances in database:")
    for bal in balances:
        print(f"Account: {bal['account']}  |  Balance: {bal['balance']}  |  Last Updated: {bal['last_updated']}")

def main():
    """Run all tests"""
    test_balance_extraction()
    test_balance_updates()

if __name__ == "__main__":
    main() 