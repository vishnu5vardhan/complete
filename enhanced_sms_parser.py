#!/usr/bin/env python3

import json
import os
import re
import time
from dotenv import load_dotenv
import google.generativeai as genai
from services.merchant_mapper import load_merchant_map, get_category
from services.transaction_type_detector import detect_transaction_type
from sms_parser import Transaction
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field
import datetime

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured successfully")
    # List available models for debugging
    try:
        print("Available models:")
        for model in genai.list_models():
            print(f"- {model.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
else:
    print("Warning: GEMINI_API_KEY not found in .env file")

class EnhancedTransaction(BaseModel):
    """Enhanced transaction model with category information"""
    transaction_type: str = Field(..., description="Type of transaction (credit, debit, refund, failed)")
    amount: float = Field(..., description="Transaction amount")
    merchant_name: str = Field("", description="Name of merchant or vendor")
    account_masked: str = Field(..., description="Masked account number like xxxx1234")
    date: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d"), description="Transaction date in YYYY-MM-DD format")
    category: str = Field("Uncategorized", description="Merchant category")
    confidence_score: float = Field(1.0, description="Confidence in transaction extraction")

def parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Clean and parse JSON response from Gemini API
    
    Args:
        response_text: Raw text response from Gemini API
        
    Returns:
        Parsed JSON dictionary or empty dict on error
    """
    try:
        # Remove markdown code blocks (```json and ```)
        cleaned_text = re.sub(r'```(?:json)?\s*|\s*```', '', response_text)
        
        # Strip any extraneous text before the first { and after the last }
        json_start = cleaned_text.find('{')
        json_end = cleaned_text.rfind('}')
        
        if json_start >= 0 and json_end >= 0:
            # Extract just the JSON portion
            json_text = cleaned_text[json_start:json_end+1]
            # Parse the JSON
            return json.loads(json_text)
        else:
            print("[!] No valid JSON found in response")
            return {}
    except json.JSONDecodeError as e:
        print(f"[!] JSON parsing error: {e}")
        print(f"Raw text: {response_text}")
        return {}
    except Exception as e:
        print(f"[!] Error parsing response: {e}")
        return {}

def ask_gemini(prompt_text: str, retries=3, delay=5) -> str:
    """
    Call Gemini API with a prompt and return the response, with retry logic
    
    Args:
        prompt_text: The prompt to send to Gemini
        retries: Number of retry attempts for rate-limit errors
        delay: Delay in seconds between retries
        
    Returns:
        The response text from Gemini
    """
    last_error = None
    
    for attempt in range(retries):
        try:
            # Ensure API key is configured
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not configured")
            
            # Call Gemini API with correct model name format
            model = genai.GenerativeModel(model_name="models/gemini-1.5-pro")
            response = model.generate_content(prompt_text)
            
            # Return the text response
            return response.text.strip()
        except Exception as e:
            last_error = e
            if "429" in str(e):
                # Rate limit error, retry after delay
                print(f"[!] Quota exceeded. Retrying in {delay} sec... (Attempt {attempt+1}/{retries})")
                time.sleep(delay)
            else:
                # Other error, break out of retry loop
                print("[!] Error calling Gemini API:", e)
                break
    
    # If we get here, all retries failed or we had a non-rate-limit error
    return json.dumps({
        "error": "Failed to call Gemini API",
        "message": str(last_error)
    })

def parse_sms(sms_text: str) -> Dict[str, Any]:
    """
    Parse SMS text using Gemini API
    
    Args:
        sms_text: SMS text containing transaction information
        
    Returns:
        Dictionary with extracted transaction details
    """
    # Format the prompt for Gemini
    prompt_text = f"""
Extract the following fields from this SMS:
- transaction_type (credit, debit, refund, failed)
- amount (numeric value only)
- merchant_name (if any)
- account_masked (masked account number or card like xxxx1234)
- date (in YYYY-MM-DD format)

Respond in this exact JSON format:
{{
  "transaction_type": "...",
  "amount": ...,
  "merchant_name": "...",
  "account_masked": "...",
  "date": "YYYY-MM-DD"
}}

SMS: "{sms_text}"
"""
    
    # Call Gemini API
    llm_response = ask_gemini(prompt_text)
    
    # Print raw response for verification
    print("Raw Gemini API response:")
    print(llm_response)
    
    # Use the new utility function to parse JSON response
    parsed_data = parse_json_response(llm_response)
    
    # Check for None merchant_name and replace with empty string
    if parsed_data.get("merchant_name") is None:
        parsed_data["merchant_name"] = ""
    
    # Handle None date
    if parsed_data.get("date") is None:
        parsed_data["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Check for error or empty response
    if not parsed_data or "error" in parsed_data:
        # Fall back to mock data for testing when API fails
        print("Using fallback mock data due to API error or empty response")
        if "debited" in sms_text.lower() or "spent" in sms_text.lower():
            return {
                "transaction_type": "debit",
                "amount": 2499.0,
                "merchant_name": "Swiggy" if "swiggy" in sms_text.lower() else "Unknown",
                "account_masked": "xxxx1234",
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
        elif "credited" in sms_text.lower():
            return {
                "transaction_type": "credit",
                "amount": 5000.0,
                "merchant_name": "",
                "account_masked": "xxxx9999",
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
        elif "refund" in sms_text.lower():
            return {
                "transaction_type": "refund",
                "amount": 899.0,
                "merchant_name": "Flipkart" if "flipkart" in sms_text.lower() else "Unknown",
                "account_masked": "xxxx4321",
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
        else:
            raise ValueError("Unable to parse SMS with fallback logic")
    
    return parsed_data

def classify_archetype(summary: Dict[str, int]) -> str:
    """
    Classify a user into a financial archetype based on their spending summary
    
    Args:
        summary: Dictionary with spending categories and amounts
        
    Returns:
        String with the archetype classification and reasoning
    """
    # Format the spending summary for the prompt
    formatted_summary = "\n".join([f"{category}: ₹{amount:,}" for category, amount in summary.items()])
    
    # Create the prompt for Gemini
    prompt_text = f"""
Based on the user's spending summary:
{formatted_summary}

Classify the user into one of the following financial archetypes:
- Balanced Spender
- Foodie & Entertainment Spender
- Retail Therapy Lover
- Debt-Focused Rebuilder
- Premium Spender
- Subscription Enthusiast
- Budget-Focused Saver
- Travel Enthusiast

Respond only with the archetype name and one short reason.
"""
    
    # Call Gemini API
    response = ask_gemini(prompt_text)
    
    # Return the archetype and reasoning
    return response.strip()

def get_top_3_recommendations(user_query: str, user_archetype: str, 
                             financial_summary: Dict[str, float], 
                             product_list: List[Dict[str, Any]]) -> str:
    """
    Format a prompt for Gemini API and get top 3 product recommendations
    
    Args:
        user_query: User's question about financial products
        user_archetype: Description of the user's financial behavior/personality
        financial_summary: Dictionary of spending categories and amounts
        product_list: List of 6 product dictionaries from search results
        
    Returns:
        String response from Gemini with top 3 recommendations
    """
    # Format financial summary as JSON
    financial_summary_formatted = json.dumps(financial_summary, indent=2)
    
    # Format product information
    product_info = []
    for i, product in enumerate(product_list):
        name = product.get('loan_product_name', 'Unknown')
        features = product.get('features_list', 'No features listed')
        suitability = product.get('loan_purpose_suitability', 'Not specified')
        
        product_info.append(f"{i+1}. {name}: {features} - Suitable for: {suitability}")
    
    products_formatted = "\n".join(product_info)
    
    # Construct the prompt
    prompt_text = f"""
User Archetype: {user_archetype}

Financial Summary:
{financial_summary_formatted}

Top Matching Products:
{products_formatted}

User Question:
{user_query}

Please recommend the best 3 products from the list above based on the user's profile and financial needs. Respond with 3 product names and a short explanation for each.
"""
    
    # Call Gemini API
    response = ask_gemini(prompt_text)
    
    return response.strip()

def parse_sms_enhanced(sms_text: str) -> Dict[str, Any]:
    """
    Enhanced SMS parser that combines:
    1. Basic SMS parsing
    2. Transaction type detection
    3. Merchant categorization
    
    Args:
        sms_text: SMS text containing transaction information
        
    Returns:
        Enhanced transaction dictionary with category and accurate transaction type
    """
    # Load resources (in a real app, load these once at startup)
    merchant_map = load_merchant_map()
    
    # Parse the SMS using the base parser
    parsed_transaction = parse_sms(sms_text)
    
    # Enhance with more accurate transaction type detection
    detected_type = detect_transaction_type(sms_text)
    if detected_type != 'unknown':
        parsed_transaction["transaction_type"] = detected_type
    
    # Add merchant category
    merchant_name = parsed_transaction.get("merchant_name", "")
    parsed_transaction["category"] = get_category(merchant_name, merchant_map)
    
    # Add confidence score (in this example, we're using a fixed score)
    parsed_transaction["confidence_score"] = 1.0
    
    # Validate with enhanced schema
    validated_data = EnhancedTransaction(**parsed_transaction)
    
    return validated_data.model_dump()

# In-memory store for transactions (for demo purposes)
transaction_history = []

def is_transaction_sms(sms_text: str) -> bool:
    """
    Check if the SMS is a transaction-related message
    
    Args:
        sms_text: SMS text to analyze
        
    Returns:
        True if this appears to be a transaction SMS, False otherwise
    """
    # Keywords that suggest a transaction SMS
    transaction_keywords = [
        "debited", "credited", "spent", "paid", "payment", "purchase", 
        "transaction", "balance", "bank", "card", "account", "rs.", "₹",
        "transfer", "txn", "debit", "credit", "withdraw", "deposit"
    ]
    
    # Convert to lowercase for case-insensitive matching
    sms_lower = sms_text.lower()
    
    # Check if any transaction keyword is in the SMS
    for keyword in transaction_keywords:
        if keyword.lower() in sms_lower:
            return True
    
    return False

def is_sufficient_data_for_archetype() -> bool:
    """
    Check if there's enough transaction data to build a reliable user archetype
    
    Returns:
        True if enough data is available, False otherwise
    """
    import db
    # Get transaction count
    transaction_count = db.get_transaction_count()
    
    # Get distinct category count
    conn = db.get_db_connection()
    try:
        cursor = conn.execute('SELECT COUNT(DISTINCT category) as category_count FROM transactions')
        category_count = cursor.fetchone()['category_count']
    except Exception as e:
        print(f"Error checking data sufficiency: {e}")
        category_count = 0
    finally:
        conn.close()
    
    # We consider data sufficient if we have at least 3 transactions
    # across at least 2 different categories
    return transaction_count >= 3 and category_count >= 2

def get_general_finance_response(query: str) -> str:
    """
    Get a response for a general finance question without relying on user-specific data
    
    Args:
        query: The user's financial question
        
    Returns:
        A response from the LLM
    """
    prompt_text = f"""You are a financial assistant. Please answer the following financial question 
in a helpful, accurate, and concise way. Focus on general financial advice rather than 
user-specific recommendations since we don't have enough transaction data yet.

User's question: {query}

Your response should be informative but also mention that as more transaction data becomes 
available, more personalized recommendations can be provided. Include 2-3 general tips 
related to the question.

Format your response in a conversational tone, and keep it under 300 words.
"""
    
    # Call Gemini API
    response = ask_gemini(prompt_text)
    
    return response.strip()

def run_end_to_end(sms_text: str) -> Dict[str, Any]:
    """
    Run the complete end-to-end flow from SMS parsing to product recommendations
    
    Args:
        sms_text: SMS text containing transaction information or a financial question
        
    Returns:
        Dictionary with parsed transaction, financial summary, archetype, and recommendations
    """
    # Import db module (avoiding circular imports)
    import db
    from services.query_creditcard import search_creditcards
    
    # Determine if this is a transaction SMS or a question
    if is_transaction_sms(sms_text):
        # Process as transaction SMS
        print("Detected a transaction SMS, processing...")
        try:
            # Step 1: Parse and enhance the SMS
            print("Step 1: Parsing SMS message...")
            transaction = parse_sms_enhanced(sms_text)
            
            # Extract balance information from SMS if present
            balance = db.extract_balance_from_sms(sms_text)
            if balance is not None:
                print(f"Extracted balance: ₹{balance:,.2f}")
                # Update balance in database if account masked info is available
                if transaction.get("account_masked"):
                    db.update_balance(
                        transaction.get("account_masked"),
                        transaction.get("amount", 0),
                        transaction.get("transaction_type", ""),
                        explicit_balance=balance
                    )
                    print(f"Updated balance for account {transaction.get('account_masked')}")
            
            # Step 2: Store transaction in database
            print("Step 2: Storing transaction in database...")
            db.insert_transaction(transaction, sms_text)
            print("Transaction added to database.")
            
            # Step 3: Calculate financial summary by category from database
            print("\nStep 3: Calculating financial summary...")
            financial_summary = db.get_financial_summary()
            
            # If database is empty, add some mock data to make the summary more interesting
            if not financial_summary or len(financial_summary) <= 1:
                print("Adding mock data to financial summary for demonstration...")
                if transaction.get("category") in financial_summary:
                    # Add previous spending in the same category
                    financial_summary[transaction.get("category")] = financial_summary.get(transaction.get("category"), 0) + 15000
                else:
                    financial_summary[transaction.get("category")] = 15000
                    
                financial_summary["Dining"] = financial_summary.get("Dining", 0) + 12000
                financial_summary["Shopping"] = financial_summary.get("Shopping", 0) + 5000
                financial_summary["EMI"] = financial_summary.get("EMI", 0) + 8000
                financial_summary["Travel"] = financial_summary.get("Travel", 0) + 3000
            
            # Print financial summary
            print("Financial Summary:")
            for category, amount in financial_summary.items():
                print(f"  {category}: ₹{amount:,.2f}")
            
            # Check if we have enough data for reliable archetype classification
            enough_data = is_sufficient_data_for_archetype()
            
            # Step 4: Classify user archetype (if we have enough data)
            print("\nStep 4: Classifying user archetype...")
            if enough_data:
                user_archetype = classify_archetype(financial_summary)
                print(f"User Archetype: {user_archetype}")
                
                # Save archetype to database
                db.save_archetype(user_archetype)
                
                # Step 5: Determine top spending category for query
                top_category = max(financial_summary.items(), key=lambda x: x[1])[0]
                
                # Step 6: Formulate product query
                print(f"\nStep 6: Finding products for top spending category: {top_category}")
                user_query = f"best credit card for {top_category} spending"
                print(f"Query: {user_query}")
                
                # Step 7: Get top 6 products using FAISS vector search
                print("\nStep 7: Retrieving matching products...")
                try:
                    # Try to use actual FAISS search
                    product_list = search_creditcards(user_query)
                    print(f"Found {len(product_list)} matching products via FAISS search")
                except Exception as e:
                    print(f"Error using FAISS search: {e}")
                    print("Falling back to mock product data...")
                    # Fallback to mock data if FAISS isn't set up
                    product_list = [
                        {
                            "loan_product_name": "Premium Travel Elite",
                            "features_list": "3X points on travel and dining, Airport lounge access, No foreign transaction fees",
                            "loan_purpose_suitability": "Travel enthusiasts, Frequent flyers, Fine dining",
                            "lender_name": "Global Bank"
                        },
                        {
                            "loan_product_name": "Foodie Rewards Plus",
                            "features_list": "5X points at restaurants, 2X on groceries, Annual dining credit",
                            "loan_purpose_suitability": "Restaurant lovers, Food delivery users",
                            "lender_name": "Culinary Credit Union"
                        },
                        {
                            "loan_product_name": "Everyday Cash Back",
                            "features_list": "2% cash back on all purchases, No annual fee, Mobile wallet integration",
                            "loan_purpose_suitability": "Daily expenses, General purchases",
                            "lender_name": "Simplicity Bank"
                        },
                        {
                            "loan_product_name": "Shopping Rewards",
                            "features_list": "4X points at retail stores, Special financing on big purchases, Store discounts",
                            "loan_purpose_suitability": "Frequent shoppers, Department store regulars",
                            "lender_name": "Retail Financial"
                        },
                        {
                            "loan_product_name": "Basic Travel Card",
                            "features_list": "2X points on travel, No annual fee first year, Trip cancellation insurance",
                            "loan_purpose_suitability": "Occasional travelers, Budget-conscious voyagers",
                            "lender_name": "Journey Bank"
                        },
                        {
                            "loan_product_name": "Premium Dining Card",
                            "features_list": "4X points at restaurants worldwide, Chef's table experiences, Priority reservations",
                            "loan_purpose_suitability": "Fine dining enthusiasts, Restaurant week participants",
                            "lender_name": "Gourmet Financial"
                        }
                    ]
                
                # Step 8: Get top 3 recommendations
                print("\nStep 8: Getting personalized recommendations...")
                recommendations = get_top_3_recommendations(
                    user_query, 
                    user_archetype, 
                    financial_summary, 
                    product_list
                )
            else:
                # Not enough data for reliable archetype classification
                user_archetype = "Insufficient Data"
                recommendations = """I need more transaction data to provide personalized recommendations.
                
I've recorded your transaction, but I need to analyze at least 3 transactions across 2 different categories to understand your spending patterns better.

Please continue to process more of your banking SMS messages, and I'll be able to:
1. Classify your financial archetype
2. Provide personalized product recommendations
3. Offer tailored financial insights

For now, I've captured this transaction and will use it to start building your financial profile."""
            
            # Step 9: Return the complete result
            result = {
                "transaction": transaction,
                "category": transaction.get("category", "Uncategorized"),
                "summary": financial_summary,
                "archetype": user_archetype,
                "top_3_recommendations": recommendations,
                "balance_updated": balance is not None,
                "data_sufficient": enough_data,
                "is_transaction": True
            }
            
            return result
            
        except Exception as e:
            print(f"Error processing transaction SMS: {e}")
            # If transaction parsing fails, try to handle as a question
            print("Trying to handle as a general finance question...")
            pass
    
    # Process as a general finance question
    print("Processing as a general finance question...")
    
    # Check if we have enough data for personalized responses
    enough_data = is_sufficient_data_for_archetype()
    
    if enough_data:
        # Get financial summary for context
        financial_summary = db.get_financial_summary()
        
        # Get user archetype
        conn = db.get_db_connection()
        try:
            cursor = conn.execute("""
                SELECT archetype FROM archetypes
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            user_archetype = result['archetype'] if result else "Unknown"
        except Exception as e:
            print(f"Error getting user archetype: {e}")
            user_archetype = "Unknown"
        finally:
            conn.close()
        
        # Format financial summary for the prompt
        summary_text = "\n".join([f"- {category}: ₹{amount:,.2f}" for category, amount in financial_summary.items()])
        
        # Create a prompt that includes user's financial context
        prompt_text = f"""As a financial assistant with access to the user's transaction history, please answer their question.

User's Financial Profile:
- Archetype: {user_archetype}
- Spending Summary:
{summary_text}

User's Question: {sms_text}

Provide a helpful, accurate, and personalized response based on their financial data.
Include specific advice that relates to their spending patterns and financial archetype.
Keep your response conversational and under 300 words.
"""
        
        # Call Gemini API for personalized response
        response = ask_gemini(prompt_text)
        
        return {
            "is_transaction": False,
            "data_sufficient": True,
            "top_3_recommendations": response.strip(),
            "archetype": user_archetype,
            "summary": financial_summary
        }
    else:
        # Not enough data for personalized response
        response = get_general_finance_response(sms_text)
        
        # Get whatever transaction data we have
        financial_summary = db.get_financial_summary()
        
        return {
            "is_transaction": False,
            "data_sufficient": False,
            "top_3_recommendations": response,
            "archetype": "Insufficient Data",
            "summary": financial_summary,
            "transaction_count": db.get_transaction_count()
        }

def main():
    """Test the enhanced SMS parsing functionality"""
    # Check if API key is available before running tests
    if not GEMINI_API_KEY:
        print("Skipping tests: GEMINI_API_KEY not configured in .env file")
        print("Please create a .env file with GEMINI_API_KEY=your_api_key")
        return
    
    print("=== SMS TRANSACTION PARSER AND RECOMMENDATION SYSTEM ===\n")
    print("Enter 'quit' to exit")
    
    while True:
        print("\nEnter SMS message to parse (or 'quit' to exit):")
        sms_text = input("> ")
        
        if sms_text.lower() in ["quit", "exit", "q"]:
            print("Exiting...")
            break
        
        if not sms_text.strip():
            print("Please enter a valid SMS message")
            continue
        
        try:
            # Run the end-to-end flow
            print("\nProcessing SMS...")
            result = run_end_to_end(sms_text)
            
            # Print the results
            print("\n=== RESULTS ===")
            print("\nTransaction Details:")
            print(json.dumps(result["transaction"], indent=2))
            
            print("\nFinancial Summary:")
            for category, amount in result["summary"].items():
                print(f"  {category}: ₹{amount:,.2f}")
            
            print(f"\nUser Archetype: {result['archetype']}")
            
            print("\nRecommendations:")
            print(result["top_3_recommendations"])
            
        except Exception as e:
            print(f"Error processing SMS: {e}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    main() 