import sqlite3
import json
from typing import Dict, Any, List, Optional
import os
import datetime

# Database file path
DB_FILE = "transactions.db"

def get_db_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = 1")
    # Return dictionary for rows
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with necessary tables if they don't exist"""
    # First, remove the existing database file if it exists
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        
    conn = get_db_connection()
    try:
        # Create transactions table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sms_text TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            merchant_name TEXT,
            category TEXT NOT NULL DEFAULT 'Uncategorized',
            account_masked TEXT,
            date TEXT,
            confidence_score REAL DEFAULT 1.0,
            is_subscription INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create archetypes table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS archetypes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            archetype TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create recommendations click log table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS recommendation_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            user_id INTEGER DEFAULT 1,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create balances table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            account_masked TEXT NOT NULL,
            current_balance REAL DEFAULT 0.0,
            last_updated TEXT,
            UNIQUE(user_id, account_masked)
        )
        ''')
        
        # Create subscriptions table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            merchant TEXT NOT NULL,
            amount REAL,
            account_masked TEXT,
            last_paid TEXT,
            next_due TEXT,
            is_recurring INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, merchant, account_masked)
        )
        ''')
        
        # Create known subscription merchants table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS subscription_merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_name TEXT NOT NULL UNIQUE
        )
        ''')
        
        # Create user_goals table for storing financial goals
        conn.execute('''
        CREATE TABLE IF NOT EXISTS user_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            goal_type TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            target_date TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create reminders table for recurring expenses
        conn.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            reminder_type TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            account_masked TEXT,
            due_date TEXT NOT NULL,
            is_paid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Insert some known subscription merchants if the table is empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM subscription_merchants")
        count = cursor.fetchone()[0]
        
        if count == 0:
            known_merchants = [
                "Netflix", "Hotstar", "Amazon Prime", "Spotify", "YouTube Premium", 
                "PhonePe Recharge", "Airtel Recharge", "Jio Recharge", "Tata Play", 
                "Zee5", "SonyLIV", "Apple Music", "iCloud+", "Google One", 
                "Microsoft 365", "Adobe Creative Cloud", "Disney+", "Audible",
                "LinkedIn Premium", "Coursera", "Udemy", "Gym Membership"
            ]
            
            for merchant in known_merchants:
                conn.execute(
                    "INSERT INTO subscription_merchants (merchant_name) VALUES (?)",
                    (merchant,)
                )
        
        conn.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        conn.close()

def insert_transaction(transaction: Dict[str, Any], sms_text: str) -> int:
    """
    Insert a transaction into the database
    
    Args:
        transaction: The transaction dictionary
        sms_text: The original SMS text
        
    Returns:
        The ID of the inserted transaction
    """
    conn = get_db_connection()
    try:
        # Check if this is a subscription transaction
        is_subscription = check_if_subscription(transaction.get('merchant_name', ''))
        
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO transactions 
        (sms_text, amount, transaction_type, merchant_name, category, account_masked, date, confidence_score, is_subscription)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sms_text,
            transaction.get('amount', 0),
            transaction.get('transaction_type', 'unknown'),
            transaction.get('merchant_name', ''),
            transaction.get('category', 'Uncategorized'),
            transaction.get('account_masked', ''),
            transaction.get('date', ''),
            transaction.get('confidence_score', 1.0),
            1 if is_subscription else 0
        ))
        transaction_id = cursor.lastrowid
        conn.commit()
        
        # Update balance
        update_balance(
            transaction.get('account_masked', ''),
            transaction.get('amount', 0),
            transaction.get('transaction_type', ''),
            extract_balance_from_sms(sms_text)
        )
        
        # If it's a subscription, add/update subscription record
        if is_subscription:
            save_subscription(
                transaction.get('merchant_name', ''),
                transaction.get('amount', 0),
                transaction.get('account_masked', ''),
                transaction.get('date', '')
            )
        
        # Check for recurring transactions
        detect_recurring_transactions(
            transaction.get('merchant_name', ''),
            transaction.get('amount', 0),
            transaction.get('account_masked', ''),
            transaction.get('date', ''),
            transaction.get('user_id', 1)
        )
        
        return transaction_id
    except Exception as e:
        print(f"Error inserting transaction: {e}")
        conn.rollback()
        return -1
    finally:
        conn.close()

def check_if_subscription(merchant_name: str) -> bool:
    """
    Check if a merchant is a known subscription service
    
    Args:
        merchant_name: Name of the merchant
        
    Returns:
        True if merchant is a subscription service, False otherwise
    """
    if not merchant_name:
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM subscription_merchants WHERE merchant_name LIKE ?",
            (f"%{merchant_name.strip()}%",)
        )
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        print(f"Error checking if subscription: {e}")
        return False
    finally:
        conn.close()

def extract_balance_from_sms(sms_text: str) -> Optional[float]:
    """
    Extract account balance from SMS text using regex
    
    Args:
        sms_text: The SMS text
        
    Returns:
        Balance amount if found, None otherwise
    """
    import re
    
    # Look for patterns like "Available balance: Rs.45000" or "Updated balance: Rs.35000"
    balance_patterns = [
        r"[Aa]vailable\s+[Bb]alance\s*(?:is|:)?\s*(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)",
        r"[Uu]pdated\s+[Bb]alance\s*(?:is|:)?\s*(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)",
        r"[Cc]losing\s+[Bb]alance\s*(?:is|:)?\s*(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)",
        r"[Bb]alance\s*(?:is|:)?\s*(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]+)?)"
    ]
    
    for pattern in balance_patterns:
        match = re.search(pattern, sms_text)
        if match:
            balance_str = match.group(1).replace(',', '')
            try:
                return float(balance_str)
            except ValueError:
                continue
    
    return None

def update_balance(account_masked: str, amount: float, transaction_type: str, explicit_balance: Optional[float] = None):
    """
    Update account balance based on transaction or explicit balance from SMS
    
    Args:
        account_masked: The masked account number
        amount: Transaction amount
        transaction_type: Type of transaction (credit/debit)
        explicit_balance: Explicit balance mentioned in SMS (if any)
    """
    if not account_masked:
        return
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get current balance for this account
        cursor.execute(
            "SELECT current_balance FROM balances WHERE account_masked = ?",
            (account_masked,)
        )
        result = cursor.fetchone()
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if explicit_balance is not None:
            # If explicit balance is provided, use it
            if result:
                cursor.execute(
                    "UPDATE balances SET current_balance = ?, last_updated = ? WHERE account_masked = ?",
                    (explicit_balance, now, account_masked)
                )
            else:
                cursor.execute(
                    "INSERT INTO balances (account_masked, current_balance, last_updated) VALUES (?, ?, ?)",
                    (account_masked, explicit_balance, now)
                )
        else:
            # Calculate new balance based on transaction
            if result:
                # Convert sqlite3.Row to dict to avoid mutation issues
                result_dict = dict(result)
                current_balance = result_dict['current_balance']
                new_balance = current_balance
                
                if transaction_type.lower() == 'credit':
                    new_balance += amount
                elif transaction_type.lower() == 'debit':
                    new_balance -= amount
                
                cursor.execute(
                    "UPDATE balances SET current_balance = ?, last_updated = ? WHERE account_masked = ?",
                    (new_balance, now, account_masked)
                )
            else:
                # Initialize with transaction amount
                initial_balance = amount if transaction_type.lower() == 'credit' else -amount
                cursor.execute(
                    "INSERT INTO balances (account_masked, current_balance, last_updated) VALUES (?, ?, ?)",
                    (account_masked, initial_balance, now)
                )
        
        conn.commit()
    except Exception as e:
        print(f"Error updating balance: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_balances(user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Get all account balances for a user
    
    Args:
        user_id: User ID (default: 1)
        
    Returns:
        List of dictionaries with account details and balances
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT account_masked, current_balance, last_updated FROM balances WHERE user_id = ? ORDER BY account_masked",
            (user_id,)
        )
        
        balances = []
        for row in cursor:
            # Convert sqlite3.Row to dict before accessing
            row_dict = dict(row)
            balances.append({
                "account": row_dict['account_masked'],
                "balance": row_dict['current_balance'],
                "last_updated": row_dict['last_updated']
            })
        
        return balances
    except Exception as e:
        print(f"Error getting balances: {e}")
        return []
    finally:
        conn.close()

def save_subscription(merchant: str, amount: float, account_masked: str, transaction_date: str):
    """
    Save or update a subscription record
    
    Args:
        merchant: Merchant name
        amount: Subscription amount
        account_masked: Masked account number
        transaction_date: Date of transaction
    """
    if not merchant or not account_masked:
        return
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Calculate next due date (30 days from transaction date)
        next_due = calculate_next_due_date(transaction_date)
        
        # Check if subscription already exists
        cursor.execute(
            "SELECT id FROM subscriptions WHERE merchant = ? AND account_masked = ?",
            (merchant, account_masked)
        )
        result = cursor.fetchone()
        
        if result:
            # Update existing subscription
            cursor.execute('''
            UPDATE subscriptions 
            SET amount = ?, last_paid = ?, next_due = ?
            WHERE id = ?
            ''', (amount, transaction_date, next_due, result[0]))
        else:
            # Create new subscription
            cursor.execute('''
            INSERT INTO subscriptions 
            (merchant, amount, account_masked, last_paid, next_due)
            VALUES (?, ?, ?, ?, ?)
            ''', (merchant, amount, account_masked, transaction_date, next_due))
        
        conn.commit()
    except Exception as e:
        print(f"Error saving subscription: {e}")
        conn.rollback()
    finally:
        conn.close()

def calculate_next_due_date(date_str: str) -> str:
    """
    Calculate the next due date for a subscription (30 days from given date)
    
    Args:
        date_str: Date string in YYYY-MM-DD format
        
    Returns:
        Next due date in YYYY-MM-DD format
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        next_due = date_obj + datetime.timedelta(days=30)
        return next_due.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error calculating next due date: {e}")
        # Return date 30 days from today if error
        return (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")

def detect_recurring_transactions(merchant: str, amount: float, account_masked: str, 
                                 transaction_date: str, user_id: int = 1) -> bool:
    """
    Detect if a transaction is recurring based on past transactions
    
    Args:
        merchant: Merchant name
        amount: Transaction amount
        account_masked: Account number (masked)
        transaction_date: Transaction date
        user_id: User ID (default: 1)
        
    Returns:
        True if recurring pattern detected, False otherwise
    """
    conn = get_db_connection()
    try:
        # Get previous transactions with the same merchant and similar amount
        amount_margin = amount * 0.05  # 5% margin for amount variations
        
        cursor = conn.execute('''
        SELECT date FROM transactions
        WHERE user_id = ? AND merchant_name = ? AND 
              ABS(amount - ?) <= ? AND
              account_masked = ?
        ORDER BY date DESC
        LIMIT 3
        ''', (user_id, merchant, amount, amount_margin, account_masked))
        
        dates = []
        for row in cursor:
            if row['date']:
                try:
                    dates.append(datetime.datetime.strptime(row['date'], "%Y-%m-%d"))
                except Exception:
                    pass
        
        # Need at least 2 previous transactions to detect a pattern
        if len(dates) < 2:
            return False
            
        # Calculate average interval
        intervals = []
        for i in range(len(dates) - 1):
            interval = abs((dates[i] - dates[i+1]).days)
            if interval > 0:
                intervals.append(interval)
                
        if not intervals:
            return False
            
        avg_interval = sum(intervals) / len(intervals)
        
        # Check if intervals are consistent (within 20% of each other)
        if len(intervals) >= 2:
            variation = max(intervals) - min(intervals)
            if variation / avg_interval > 0.2:
                return False
        
        # Consider it recurring if average interval is between 25 and 35 days (monthly)
        # or between 6 and 8 days (weekly)
        is_recurring = (25 <= avg_interval <= 35) or (6 <= avg_interval <= 8)
        
        if is_recurring:
            # Calculate next due date
            next_due_date = (datetime.datetime.strptime(transaction_date, "%Y-%m-%d") + 
                           datetime.timedelta(days=round(avg_interval))).strftime("%Y-%m-%d")
            
            # Add reminder
            add_reminder({
                'reminder_type': 'subscription' if avg_interval < 32 else 'bill',
                'merchant': merchant,
                'amount': amount,
                'account_masked': account_masked,
                'due_date': next_due_date
            }, user_id)
            
        return is_recurring
    except Exception as e:
        print(f"Error detecting recurring transactions: {e}")
        return False
    finally:
        conn.close()

def add_reminder(reminder_data: Dict[str, Any], user_id: int = 1) -> int:
    """
    Add a payment reminder
    
    Args:
        reminder_data: Dictionary with reminder details
            - reminder_type: Type of reminder (bill, subscription, emi)
            - merchant: Merchant name
            - amount: Payment amount
            - due_date: Due date
            - account_masked: Account number (masked)
        user_id: User ID (default: 1)
        
    Returns:
        ID of the created reminder
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO reminders 
        (user_id, reminder_type, merchant, amount, account_masked, due_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            reminder_data.get('reminder_type', 'bill'),
            reminder_data.get('merchant', ''),
            reminder_data.get('amount', 0),
            reminder_data.get('account_masked', ''),
            reminder_data.get('due_date', '')
        ))
        reminder_id = cursor.lastrowid
        conn.commit()
        return reminder_id
    except Exception as e:
        print(f"Error adding reminder: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def get_upcoming_reminders(days_ahead: int = 3, user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Get upcoming payment reminders
    
    Args:
        days_ahead: Number of days to look ahead (default: 3)
        user_id: User ID (default: 1)
        
    Returns:
        List of reminder dictionaries
    """
    conn = get_db_connection()
    reminders = []
    try:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        future_date = (datetime.datetime.now() + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        cursor = conn.execute('''
        SELECT id, reminder_type, merchant, amount, account_masked, due_date, is_paid
        FROM reminders
        WHERE user_id = ? AND is_paid = 0 AND due_date BETWEEN ? AND ?
        ORDER BY due_date ASC
        ''', (user_id, today, future_date))
        
        for row in cursor:
            reminders.append(dict(row))
            
        return reminders
    except Exception as e:
        print(f"Error getting upcoming reminders: {e}")
        return []
    finally:
        conn.close()

def mark_reminder_paid(reminder_id: int, user_id: int = 1) -> bool:
    """
    Mark a reminder as paid
    
    Args:
        reminder_id: Reminder ID
        user_id: User ID (default: 1)
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    try:
        conn.execute('''
        UPDATE reminders
        SET is_paid = 1, modified_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        ''', (reminder_id, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error marking reminder as paid: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_subscriptions() -> List[Dict[str, Any]]:
    """
    Get all subscriptions
    
    Returns:
        List of subscriptions
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT merchant, amount, account_masked, last_paid, next_due, is_recurring
        FROM subscriptions
        ORDER BY next_due
        ''')
        
        subscriptions = []
        for row in cursor:
            subscriptions.append({
                "merchant": row['merchant'],
                "amount": row['amount'],
                "account": row['account_masked'],
                "last_paid": row['last_paid'],
                "next_due": row['next_due'],
                "recurring": bool(row['is_recurring'])
            })
        
        return subscriptions
    except Exception as e:
        print(f"Error getting subscriptions: {e}")
        return []
    finally:
        conn.close()

def get_financial_summary() -> Dict[str, float]:
    """
    Get a summary of spending by category
    
    Returns:
        A dictionary with category as key and total amount as value
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Only sum up debit transactions (money spent)
        cursor.execute('''
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE transaction_type = 'debit'
        GROUP BY category
        ORDER BY total DESC
        ''')
        
        summary = {}
        for row in cursor:
            # Convert sqlite3.Row to dict before accessing
            row_dict = dict(row)
            summary[row_dict['category']] = row_dict['total']
        
        return summary
    except Exception as e:
        print(f"Error getting financial summary: {e}")
        return {}
    finally:
        conn.close()

def get_insights(month: Optional[str] = None) -> Dict[str, Any]:
    """
    Get financial insights for the user
    
    Args:
        month: Month in YYYY-MM format (optional)
        
    Returns:
        Dictionary with financial insights
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Date filter condition
        date_condition = ""
        params = []
        
        if month:
            date_condition = "WHERE strftime('%Y-%m', date) = ?"
            params.append(month)
        
        # Monthly spend (debits)
        cursor.execute(f'''
        SELECT SUM(amount) as total
        FROM transactions
        {date_condition + " AND" if date_condition else "WHERE"} transaction_type = 'debit'
        ''', params)
        monthly_spend = cursor.fetchone()['total'] or 0
        
        # Monthly income (credits)
        credits_params = params.copy()
        cursor.execute(f'''
        SELECT SUM(amount) as total
        FROM transactions
        {date_condition + " AND" if date_condition else "WHERE"} transaction_type = 'credit'
        ''', credits_params)
        monthly_income = cursor.fetchone()['total'] or 0
        
        # Category-wise spend
        category_params = params.copy()
        cursor.execute(f'''
        SELECT category, SUM(amount) as total
        FROM transactions
        {date_condition + " AND" if date_condition else "WHERE"} transaction_type = 'debit'
        GROUP BY category
        ORDER BY total DESC
        ''', category_params)
        
        category_spend = {}
        for row in cursor:
            category_spend[row['category']] = row['total']
        
        # Average transaction
        avg_params = params.copy()
        cursor.execute(f'''
        SELECT AVG(amount) as avg_amount
        FROM transactions
        {date_condition + " AND" if date_condition else "WHERE"} transaction_type = 'debit'
        ''', avg_params)
        avg_transaction = cursor.fetchone()['avg_amount'] or 0
        
        # Subscription spend
        sub_params = params.copy()
        cursor.execute(f'''
        SELECT SUM(amount) as total
        FROM transactions
        {date_condition + " AND" if date_condition else "WHERE"} is_subscription = 1 AND transaction_type = 'debit'
        ''', sub_params)
        subscription_spend = cursor.fetchone()['total'] or 0
        
        # Calculate savings rate
        savings_rate = 0
        if monthly_income > 0:
            savings_rate = (monthly_income - monthly_spend) / monthly_income
        
        # Transactions by day of week
        dow_params = params.copy()
        cursor.execute(f'''
        SELECT strftime('%w', date) as day_of_week, SUM(amount) as total
        FROM transactions
        {date_condition + " AND" if date_condition else "WHERE"} transaction_type = 'debit'
        GROUP BY day_of_week
        ORDER BY day_of_week
        ''', dow_params)
        
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day_spend = {day: 0 for day in days}
        
        for row in cursor:
            day_index = int(row['day_of_week'])
            day_spend[days[day_index]] = row['total']
        
        return {
            "monthly_spend": monthly_spend,
            "monthly_income": monthly_income,
            "category_spend": category_spend,
            "average_transaction": avg_transaction,
            "subscription_spend": subscription_spend,
            "savings_rate": savings_rate,
            "day_of_week_spend": day_spend,
            "month": month if month else datetime.datetime.now().strftime("%Y-%m")
        }
    except Exception as e:
        print(f"Error getting insights: {e}")
        return {}
    finally:
        conn.close()

def save_archetype(archetype: str, user_id: int = 1):
    """
    Save a user's financial archetype
    
    Args:
        archetype: The archetype classification
        user_id: The user ID (default: 1)
    """
    conn = get_db_connection()
    try:
        conn.execute('''
        INSERT INTO archetypes (user_id, archetype)
        VALUES (?, ?)
        ''', (user_id, archetype))
        conn.commit()
    except Exception as e:
        print(f"Error saving archetype: {e}")
        conn.rollback()
    finally:
        conn.close()

def log_recommendation_click(product_name: str, user_id: int = 1):
    """
    Log when a user clicks on a product recommendation
    
    Args:
        product_name: The name of the product
        user_id: The user ID (default: 1)
    """
    conn = get_db_connection()
    try:
        conn.execute('''
        INSERT INTO recommendation_clicks (product_name, user_id)
        VALUES (?, ?)
        ''', (product_name, user_id))
        conn.commit()
    except Exception as e:
        print(f"Error logging recommendation click: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_analytics_data() -> Dict[str, Any]:
    """
    Get analytics data for the dashboard
    
    Returns:
        Dictionary with analytics data
    """
    conn = get_db_connection()
    try:
        # Get archetype distribution
        archetype_cursor = conn.execute('''
        SELECT archetype, COUNT(*) as count
        FROM archetypes
        GROUP BY archetype
        ORDER BY count DESC
        ''')
        
        archetypes = {}
        for row in archetype_cursor:
            archetypes[row['archetype']] = row['count']
        
        # Get category spending totals
        category_cursor = conn.execute('''
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE transaction_type = 'debit'
        GROUP BY category
        ORDER BY total DESC
        ''')
        
        categories = {}
        for row in category_cursor:
            categories[row['category']] = row['total']
        
        # Get top clicked recommendations
        recommendation_cursor = conn.execute('''
        SELECT product_name, COUNT(*) as clicks
        FROM recommendation_clicks
        GROUP BY product_name
        ORDER BY clicks DESC
        LIMIT 5
        ''')
        
        recommendations = {}
        for row in recommendation_cursor:
            recommendations[row['product_name']] = row['clicks']
        
        # Get subscription stats
        subscription_cursor = conn.execute('''
        SELECT COUNT(*) as count, SUM(amount) as total
        FROM subscriptions
        ''')
        
        sub_row = subscription_cursor.fetchone()
        subscription_stats = {
            "count": sub_row['count'],
            "total": sub_row['total'] if sub_row['total'] else 0
        }
        
        # Get balance stats
        balance_cursor = conn.execute('''
        SELECT COUNT(*) as count, SUM(current_balance) as total
        FROM balances
        ''')
        
        bal_row = balance_cursor.fetchone()
        balance_stats = {
            "count": bal_row['count'],
            "total": bal_row['total'] if bal_row['total'] else 0
        }
        
        return {
            "archetype_distribution": archetypes,
            "category_spending": categories,
            "top_recommendations": recommendations,
            "subscription_stats": subscription_stats,
            "balance_stats": balance_stats,
            "total_transactions": get_transaction_count(),
            "total_spending": get_total_spending()
        }
    except Exception as e:
        print(f"Error getting analytics data: {e}")
        return {}
    finally:
        conn.close()

def get_transaction_count() -> int:
    """Get the total number of transactions"""
    conn = get_db_connection()
    try:
        cursor = conn.execute('SELECT COUNT(*) as count FROM transactions')
        return cursor.fetchone()['count']
    except Exception as e:
        print(f"Error getting transaction count: {e}")
        return 0
    finally:
        conn.close()

def get_total_spending() -> float:
    """Get the total amount spent (debit transactions)"""
    conn = get_db_connection()
    try:
        cursor = conn.execute('''
        SELECT SUM(amount) as total
        FROM transactions
        WHERE transaction_type = 'debit'
        ''')
        result = cursor.fetchone()
        return result['total'] if result['total'] else 0
    except Exception as e:
        print(f"Error getting total spending: {e}")
        return 0
    finally:
        conn.close()

def set_user_goal(goal_data: Dict[str, Any], user_id: int = 1) -> int:
    """
    Set a financial goal for a user
    
    Args:
        goal_data: Dictionary with goal details
            - goal_type: Type of goal (e.g., trip, emergency fund)
            - target_amount: Target amount to save
            - target_date: Target date to achieve the goal
        user_id: User ID (default: 1)
        
    Returns:
        ID of the created goal
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO user_goals 
        (user_id, goal_type, target_amount, target_date, status, current_amount)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            goal_data.get('goal_type', 'Savings'),
            goal_data.get('target_amount', 0),
            goal_data.get('target_date', ''),
            'active',
            goal_data.get('current_amount', 0)
        ))
        goal_id = cursor.lastrowid
        conn.commit()
        return goal_id
    except Exception as e:
        print(f"Error setting user goal: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def get_user_goals(user_id: int = 1, include_achieved: bool = False) -> List[Dict[str, Any]]:
    """
    Get all financial goals for a user
    
    Args:
        user_id: User ID (default: 1)
        include_achieved: Whether to include achieved goals (default: False)
        
    Returns:
        List of goals as dictionaries
    """
    conn = get_db_connection()
    goals = []
    try:
        status_filter = "" if include_achieved else "AND status = 'active'"
        
        cursor = conn.execute(f'''
        SELECT id, goal_type, target_amount, current_amount, target_date, status, created_at
        FROM user_goals
        WHERE user_id = ? {status_filter}
        ORDER BY created_at DESC
        ''', (user_id,))
        
        for row in cursor:
            goal = dict(row)
            
            # Calculate progress percentage
            if goal['target_amount'] > 0:
                goal['progress'] = (goal['current_amount'] / goal['target_amount']) * 100
            else:
                goal['progress'] = 0
                
            # Calculate days remaining if target_date exists
            if goal['target_date']:
                try:
                    target_date = datetime.datetime.strptime(goal['target_date'], "%Y-%m-%d")
                    today = datetime.datetime.now()
                    days_remaining = (target_date - today).days
                    goal['days_remaining'] = max(0, days_remaining)
                except Exception:
                    goal['days_remaining'] = None
            
            goals.append(goal)
            
        return goals
    except Exception as e:
        print(f"Error getting user goals: {e}")
        return []
    finally:
        conn.close()

def update_goal_progress(goal_id: int, amount_added: float, user_id: int = 1) -> bool:
    """
    Update progress for a financial goal
    
    Args:
        goal_id: Goal ID
        amount_added: Amount to add to current progress
        user_id: User ID (default: 1)
        
    Returns:
        True if successful, False otherwise
    """
    conn = get_db_connection()
    try:
        # Get current amount
        cursor = conn.execute('''
        SELECT current_amount, target_amount FROM user_goals
        WHERE id = ? AND user_id = ?
        ''', (goal_id, user_id))
        
        result = cursor.fetchone()
        if not result:
            print(f"Goal not found: {goal_id}")
            return False
            
        current_amount = result['current_amount'] + amount_added
        target_amount = result['target_amount']
        
        # Update status if target reached
        status = 'achieved' if current_amount >= target_amount else 'active'
        
        # Update goal
        conn.execute('''
        UPDATE user_goals 
        SET current_amount = ?, status = ?, modified_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        ''', (current_amount, status, goal_id, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating goal progress: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_total_income(month: Optional[str] = None) -> float:
    """
    Get total income (credits) for a user
    
    Args:
        month: Month in YYYY-MM format (optional)
        
    Returns:
        Total income amount
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Date filter condition
        date_condition = ""
        params = []
        
        if month:
            date_condition = "AND strftime('%Y-%m', date) = ?"
            params.append(month)
        
        # Get total credits
        cursor.execute(f'''
        SELECT SUM(amount) as total
        FROM transactions
        WHERE transaction_type = 'credit' {date_condition}
        ''', params)
        
        result = cursor.fetchone()
        return result['total'] or 0
    except Exception as e:
        print(f"Error getting total income: {e}")
        return 0
    finally:
        conn.close()

# Initialize database when the module is imported
if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
    init_db() 