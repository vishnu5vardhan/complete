#!/usr/bin/env python3

import os
import pandas as pd
from typing import Dict

def load_merchant_map(file_path="data/merchant.csv") -> Dict[str, str]:
    """
    Loads and returns the merchant map dictionary
    
    Args:
        file_path: Path to the merchant.csv file
        
    Returns:
        Dictionary mapping merchant names to categories
    """
    if not os.path.exists(file_path):
        print(f"Warning: Merchant file not found at {file_path}")
        return {}
    
    # Load the merchant CSV
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error loading merchant file: {e}")
        return {}
    
    # Create the merchant map dictionary
    merchant_map = {}
    
    # Process each row in the dataframe
    for _, row in df.iterrows():
        # Get the main merchant name and category
        merchant_name = str(row['merchant_name']).lower().strip()
        category = str(row['category']).strip()
        
        # Add the main merchant name to the map
        if merchant_name and merchant_name != "nan":
            merchant_map[merchant_name] = category
        
        # Process alternate names if they exist
        alternate_names = str(row.get('alternate_names', ''))
        if alternate_names and alternate_names != "nan":
            # Split alternate names by pipe character
            for alt_name in alternate_names.split('|'):
                alt_name = alt_name.lower().strip()
                if alt_name:
                    merchant_map[alt_name] = category
    
    print(f"Loaded {len(merchant_map)} merchant names for {len(df)} unique merchants")
    return merchant_map

def get_category(merchant_name: str, merchant_map: Dict[str, str]) -> str:
    """
    Return category if found, else 'Uncategorized'
    
    Args:
        merchant_name: The merchant name to look up
        merchant_map: Dictionary mapping merchant names to categories
        
    Returns:
        Category string or 'Uncategorized' if not found
    """
    if not merchant_name:
        return "Uncategorized"
    
    # Normalize the merchant name
    normalized_name = merchant_name.lower().strip()
    
    # Direct lookup
    if normalized_name in merchant_map:
        return merchant_map[normalized_name]
    
    # Try partial matching for common cases
    for name, category in merchant_map.items():
        if name in normalized_name or normalized_name in name:
            return category
    
    # No match found
    return "Uncategorized"

def main():
    """Test the merchant mapping functionality"""
    merchant_map = load_merchant_map()
    
    # Test cases
    test_merchants = [
        "Swiggy",
        "flipkart.com", 
        "AMAZON",
        "zomato",
        "Uber",
        "UnknownMerchant"
    ]
    
    print("\nTesting merchant category lookup:")
    print("-" * 50)
    for merchant in test_merchants:
        category = get_category(merchant, merchant_map)
        print(f"{merchant:20} -> {category}")
    print("-" * 50)

if __name__ == "__main__":
    main() 