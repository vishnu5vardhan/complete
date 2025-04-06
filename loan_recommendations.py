#!/usr/bin/env python3

import json
from typing import Dict, List, Any

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
    
    # In a real implementation, you would use the Gemini API:
    """
    import google.generativeai as genai
    genai.configure(api_key="your-api-key")  # Replace with actual API key
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt_text)
    return response.text
    """
    
    # For demonstration, return a mock response
    mock_response = f"""
Based on the user's profile as {user_archetype} and their financial summary, here are my top 3 recommendations:

1. {product_list[0]['loan_product_name']}: This product aligns well with the user's needs based on their spending patterns and question.

2. {product_list[5]['loan_product_name']}: This is suitable due to the specific features that match the user's financial behavior.

3. {product_list[1]['loan_product_name']}: This provides excellent benefits for the user's most frequent spending categories.
"""
    return mock_response

def main():
    # Test the function with dummy data
    dummy_query = "What is the best credit card for dining and travel?"
    dummy_archetype = "Foodie & Frequent Traveler"
    
    dummy_financial_summary = {
        "Dining": 3500,
        "Travel": 4200,
        "Shopping": 1800,
        "EMI": 2000,
        "Groceries": 1200
    }
    
    # Mock product list with 6 products
    dummy_product_list = [
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
    
    print("Generating recommendations...\n")
    
    # Display the formatted prompt
    print("====== FORMATTED PROMPT ======")
    financial_summary_formatted = json.dumps(dummy_financial_summary, indent=2)
    product_info = []
    for i, product in enumerate(dummy_product_list):
        name = product.get('loan_product_name', 'Unknown')
        features = product.get('features_list', 'No features listed')
        suitability = product.get('loan_purpose_suitability', 'Not specified')
        product_info.append(f"{i+1}. {name}: {features} - Suitable for: {suitability}")
    products_formatted = "\n".join(product_info)
    
    prompt_text = f"""
User Archetype: {dummy_archetype}

Financial Summary:
{financial_summary_formatted}

Top Matching Products:
{products_formatted}

User Question:
{dummy_query}

Please recommend the best 3 products from the list above based on the user's profile and financial needs. Respond with 3 product names and a short explanation for each.
"""
    print(prompt_text)
    print("==============================\n")
    
    # Get recommendations using our function
    recommendations = get_top_3_recommendations(dummy_query, dummy_archetype, 
                                               dummy_financial_summary, dummy_product_list)
    
    # Display the mock Gemini response
    print("====== GEMINI RESPONSE ======")
    print(recommendations)
    print("=============================")
    
    # Real implementation note
    print("\nNote: In a real implementation, you would need to:")
    print("1. Install the Google Generative AI package: pip install google-generativeai")
    print("2. Get an API key from Google AI Studio")
    print("3. Uncomment and update the Gemini API code in the get_top_3_recommendations function")

if __name__ == "__main__":
    main() 