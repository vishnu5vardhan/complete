#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
import json
import db
from enhanced_sms_parser import run_end_to_end, parse_sms_enhanced
import background_service  # Import the background service module

# Initialize FastAPI app
app = FastAPI(
    title="SMS Transaction Parser API",
    description="API for parsing and analyzing financial SMS messages",
    version="1.0.0",
)

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
    user_id: Optional[int] = 1

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
async def process_question(request: FinancialQuestion):
    """
    Process a financial question and return a personalized response
    based on the user's transaction history
    """
    try:
        # Use the run_end_to_end function to process the question
        result = run_end_to_end(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

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
        # Get financial summary from database
        financial_summary = db.get_financial_summary()
        
        # Get latest archetype
        conn = db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT archetype FROM archetypes
            ORDER BY created_at DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        
        archetype = result['archetype'] if result else "Unknown"
        
        return {
            "summary": financial_summary,
            "archetype": archetype,
            "total_transactions": db.get_transaction_count(),
            "total_spending": db.get_total_spending()
        }
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
        
        # Convert to list of dictionaries
        transactions = [dict(row) for row in cursor.fetchall()]
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