#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
import json
import db
from enhanced_sms_parser import run_end_to_end, parse_sms_enhanced, handle_financial_question, is_sufficient_data_for_archetype
import background_service  # Import the background service module

# Initialize FastAPI app
app = FastAPI(
    title="SMS Transaction Parser API",
    description="API for parsing and analyzing financial SMS messages",
    version="1.0.0",
)

# Mount static files directory
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Pydantic Models
class SMSRequest(BaseModel):
    sms_text: str = None
    sms: str = None

class RecommendationClick(BaseModel):
    product_name: str
    user_id: Optional[int] = 1

class FinancialQuestion(BaseModel):
    question: str
    user_id: int = 1

class UserGoal(BaseModel):
    goal_type: str
    target_amount: float
    target_date: Optional[str] = None
    user_id: int = 1

# API endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to the SMS Transaction Parser API"}

@app.post("/sms")
async def process_sms(request: SMSRequest):
    """
    Process an SMS message and return the parsed transaction, 
    financial summary, archetype, and product recommendations
    """
    try:
        # Use either sms_text or sms parameter
        message = request.sms_text or request.sms
        if not message:
            raise HTTPException(status_code=400, detail="No SMS text provided")
            
        # Run the end-to-end processing on the SMS
        result = run_end_to_end(message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing SMS: {str(e)}")

@app.post("/question")
async def handle_question(req: FinancialQuestion):
    """
    Handle a financial question
    """
    try:
        # Process the question
        result = handle_financial_question(req.question, req.user_id)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.post("/goals")
async def set_goal(goal: UserGoal):
    """
    Set a financial goal
    """
    try:
        # Set the goal in the database
        goal_id = db.set_user_goal(goal.dict(), goal.user_id)
        
        if goal_id:
            return {"success": True, "goal_id": goal_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to set goal")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting goal: {str(e)}")

@app.get("/goals")
async def get_goals(user_id: int = 1, include_achieved: bool = False):
    """
    Get all financial goals for a user
    """
    try:
        # Get goals from the database
        goals = db.get_user_goals(user_id, include_achieved)
        
        return {"success": True, "goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting goals: {str(e)}")

@app.put("/goals/{goal_id}")
async def update_goal_progress(
    goal_id: int, 
    amount_added: float, 
    user_id: int = 1
):
    """
    Update progress for a financial goal
    """
    try:
        # Update the goal progress in the database
        success = db.update_goal_progress(goal_id, amount_added, user_id)
        
        if success:
            # Get updated goal
            goals = db.get_user_goals(user_id)
            updated_goal = next((g for g in goals if g["id"] == goal_id), None)
            
            return {"success": True, "goal": updated_goal}
        else:
            raise HTTPException(status_code=404, detail="Goal not found or update failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating goal: {str(e)}")

@app.get("/persona")
async def get_persona(user_id: int = 1):
    """
    Get a user's financial persona summary
    """
    try:
        # Check if we have enough data
        enough_data = is_sufficient_data_for_archetype()
        transaction_count = db.get_transaction_count()
        
        if not enough_data:
            return {
                "success": True,
                "data_sufficient": False,
                "message": (
                    "I need at least one month of transactions to understand your profile. "
                    f"Currently, I have {transaction_count} transactions. For now, feel free to ask me "
                    "about general finance or credit card options."
                ),
                "transaction_count": transaction_count,
                "data_threshold": {
                    "min_transactions": 20,
                    "min_days": 30,
                    "current_transactions": transaction_count
                }
            }
            
        # Get the latest archetype
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT archetype FROM archetypes
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Convert sqlite3.Row to dict before accessing
            result_dict = dict(result)
            archetype = result_dict['archetype']
        else:
            archetype = None
        
        # Get financial summary
        financial_summary = db.get_financial_summary()
        
        # Get active goals
        goals = db.get_user_goals(user_id)
        
        # Calculate savings rate (income - expenses) / income
        savings_rate = 0
        total_income = db.get_total_income()
        total_spending = db.get_total_spending()
        
        if total_income > 0:
            savings_rate = (total_income - total_spending) / total_income * 100
            
        # Get top spending categories
        top_categories = sorted(financial_summary.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "success": True,
            "data_sufficient": True,
            "archetype": archetype,
            "spending_summary": financial_summary,
            "goals": goals,
            "savings_rate": savings_rate,
            "top_categories": [{"category": cat, "amount": amt} for cat, amt in top_categories]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting persona summary: {str(e)}")

@app.post("/background/enqueue")
async def enqueue_sms(request: SMSRequest):
    """
    Add an SMS to the background processing queue
    """
    try:
        # Use either sms_text or sms parameter
        message = request.sms_text or request.sms
        if not message:
            raise HTTPException(status_code=400, detail="No SMS text provided")
            
        # Add to queue
        enqueued = background_service.enqueue_sms(message)
        
        return {
            "status": "success" if enqueued else "duplicate",
            "message": "SMS added to processing queue" if enqueued else "SMS already processed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enqueuing SMS: {str(e)}")

@app.get("/background/status")
async def get_background_status():
    """
    Get the status of the background SMS processing service
    """
    try:
        return background_service.get_queue_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting background status: {str(e)}")

@app.post("/background/start")
async def start_background_service():
    """
    Start the background SMS processing service
    """
    try:
        background_service.start_background_service()
        return {"status": "success", "message": "Background service started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting background service: {str(e)}")

@app.post("/background/stop")
async def stop_background_service():
    """
    Stop the background SMS processing service
    """
    try:
        background_service.stop_background_service()
        return {"status": "success", "message": "Background service stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping background service: {str(e)}")

@app.post("/background/simulate")
async def simulate_random_sms():
    """
    Simulate receiving a random SMS
    """
    try:
        simulated = background_service.simulate_real_time_monitor()
        return {
            "status": "success" if simulated else "duplicate",
            "message": "Random SMS simulated" if simulated else "Duplicate SMS detected"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error simulating SMS: {str(e)}")

@app.get("/summary")
async def get_summary():
    """
    Get the current category-wise financial summary and user archetype
    """
    try:
        # Check if we have enough data for archetype
        enough_data = is_sufficient_data_for_archetype()
        transaction_count = db.get_transaction_count()
        
        # Get financial summary from database
        financial_summary = db.get_financial_summary()
        
        response = {
            "summary": financial_summary,
            "total_transactions": transaction_count,
            "total_spending": db.get_total_spending(),
            "data_sufficient": enough_data
        }
        
        if enough_data:
            # Get latest archetype only if we have sufficient data
            conn = db.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT archetype FROM archetypes
                ORDER BY created_at DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Convert sqlite3.Row to dict before accessing
                result_dict = dict(result)
                archetype = result_dict['archetype']
                response["archetype"] = archetype
            else:
                response["archetype"] = None
        else:
            # Include data threshold information in response
            response["archetype"] = None
            response["message"] = (
                "I need at least one month of transactions to understand your profile. "
                f"Currently, I have {transaction_count} transactions. For now, feel free to ask me "
                "about general finance or credit card options."
            )
            response["data_threshold"] = {
                "min_transactions": 20,
                "min_days": 30,
                "current_transactions": transaction_count
            }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting summary: {str(e)}")

@app.get("/transactions")
async def get_transactions(limit: int = 10):
    """
    Get the most recent transactions
    """
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM transactions
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        # Convert each sqlite3.Row to a regular dictionary to avoid mutation issues
        transactions = []
        for row in cursor.fetchall():
            transactions.append(dict(row))
        
        conn.close()
        
        return {"transactions": transactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting transactions: {str(e)}")

@app.get("/recommendations")
async def get_recommendations(category: Optional[str] = None):
    """
    Get product recommendations for a specific category or based on top spending
    """
    try:
        # Import here to avoid circular imports
        from services.query_creditcard import search_creditcards
        
        # If category is not specified, get the top spending category
        if not category:
            financial_summary = db.get_financial_summary()
            if not financial_summary:
                category = "Dining"  # Default if no transaction history
            else:
                category = max(financial_summary.items(), key=lambda x: x[1])[0]
        
        # Formulate query
        user_query = f"best credit card for {category} spending"
        
        # Try to get recommendations using FAISS
        try:
            products = search_creditcards(user_query)
        except Exception as e:
            # Fallback to mock data if FAISS search fails
            products = [
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
                }
            ]
        
        # Return top 3 products
        return {"category": category, "products": products[:3]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")

@app.get("/balance")
async def get_balance(account: Optional[str] = None):
    """
    Get current balance for all accounts or a specific account
    """
    try:
        balances = db.get_balances()
        
        if account:
            # Return balance for specific account if requested
            account_balance = next((b for b in balances if b["account"] == account), None)
            if not account_balance:
                raise HTTPException(status_code=404, detail=f"Account {account} not found")
            return account_balance
        
        # Calculate total balance across all accounts
        total_balance = sum(b["balance"] for b in balances)
        
        return {
            "accounts": balances,
            "total_balance": total_balance,
            "count": len(balances)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting balances: {str(e)}")

@app.get("/subscriptions")
async def get_subscriptions():
    """
    Get all active subscriptions
    """
    try:
        subscriptions = db.get_subscriptions()
        
        # Calculate total monthly subscription cost
        total_cost = sum(sub["amount"] for sub in subscriptions)
        
        return {
            "subscriptions": subscriptions,
            "total_monthly_cost": total_cost,
            "count": len(subscriptions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting subscriptions: {str(e)}")

@app.get("/reminders")
async def get_reminders(days: int = 3):
    """
    Get upcoming subscription reminders
    """
    try:
        reminders = db.get_upcoming_reminders(days)
        
        return {
            "reminders": reminders,
            "days_ahead": days,
            "count": len(reminders)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting reminders: {str(e)}")

@app.get("/insights")
async def get_insights(month: Optional[str] = None):
    """
    Get financial insights
    """
    try:
        insights = db.get_insights(month)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting insights: {str(e)}")

@app.post("/track-recommendation-click")
async def track_recommendation_click(click: RecommendationClick):
    """
    Track when a user clicks on a product recommendation
    """
    try:
        db.log_recommendation_click(click.product_name, click.user_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking recommendation click: {str(e)}")

@app.get("/analytics")
async def get_analytics():
    """
    Get analytics data for dashboard
    """
    try:
        analytics_data = db.get_analytics_data()
        return analytics_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting analytics data: {str(e)}")

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": f"An unexpected error occurred: {str(exc)}"},
    )

# Start background service when API starts
@app.on_event("startup")
async def startup_event():
    """
    Start the background service when the API starts
    """
    background_service.start_background_service()
    print("[INFO] Background SMS processing service started")

# Stop background service when API stops
@app.on_event("shutdown")
async def shutdown_event():
    """
    Stop the background service when the API stops
    """
    background_service.stop_background_service()
    print("[INFO] Background SMS processing service stopped")

if __name__ == "__main__":
    # Initialize database
    db.init_db()
    
    # Run server
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 