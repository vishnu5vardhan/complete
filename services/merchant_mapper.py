#!/usr/bin/env python3

import os
import csv
from typing import Dict, Optional, List, Set, Tuple
import re

# Global variables to store merchant data
merchant_map = {}
merchant_names = set()
merchant_categories = {}
transaction_indicators = set()

def load_merchant_map(refresh: bool = False) -> Dict[str, str]:
    """
    Load merchant data from CSV files
    
    Args:
        refresh: Whether to force reload the data
        
    Returns:
        Dictionary mapping merchant names to categories
    """
    global merchant_map, merchant_names, merchant_categories, transaction_indicators
    
    # If already loaded and not forced to refresh, return the cached map
    if merchant_map and not refresh:
        return merchant_map
    
    # Paths to merchant data files
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    merchant_file = os.path.join(base_path, "data", "merchant.csv")
    merchant_short_file = os.path.join(base_path, "data", "merchant_short.csv")
    indicator_file = os.path.join(base_path, "data", "transaction_indicator_keywords.csv")
    
    # Load transaction indicator keywords
    try:
        if os.path.exists(indicator_file):
            with open(indicator_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        transaction_indicators.add(row[0].strip().lower())
            print(f"Loaded {len(transaction_indicators)} transaction indicators")
        else:
            print(f"Warning: Transaction indicator file not found at {indicator_file}")
    except Exception as e:
        print(f"Error loading transaction indicators: {e}")
    
    # Load merchant data from the main merchant CSV
    try:
        if os.path.exists(merchant_file):
            with open(merchant_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'merchant_name' in row and 'category' in row:
                        merchant_name = row['merchant_name'].strip()
                        category = row['category'].strip()
                        
                        # Add to our maps
                        merchant_map[merchant_name.lower()] = category
                        merchant_names.add(merchant_name.lower())
                        
                        # Also add without spaces for fuzzy matching
                        merchant_map[merchant_name.lower().replace(' ', '')] = category
                        
                        # Store abbreviation to merchant name mapping
                        if 'merchant_abbreviation' in row and row['merchant_abbreviation'].strip():
                            abbr = row['merchant_abbreviation'].strip()
                            merchant_map[abbr.lower()] = category
                            
                        # Store category mapping
                        if category not in merchant_categories:
                            merchant_categories[category] = []
                        merchant_categories[category].append(merchant_name)
                            
            print(f"Loaded {len(merchant_names)} merchants from main file")
        else:
            print(f"Warning: Merchant file not found at {merchant_file}")
    except Exception as e:
        print(f"Error loading merchant data: {e}")
    
    # Load additional merchant names from merchant_short.csv if available
    try:
        if os.path.exists(merchant_short_file):
            with open(merchant_short_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        for item in row:
                            # Format: "Merchant Name (ABBR)"
                            if '(' in item and ')' in item:
                                parts = item.split('(')
                                if len(parts) >= 2:
                                    name = parts[0].strip()
                                    abbr = parts[1].split(')')[0].strip()
                                    
                                    # If we already have a category for this abbreviation, use it
                                    category = None
                                    if abbr.lower() in merchant_map:
                                        category = merchant_map[abbr.lower()]
                                    else:
                                        # Try to determine category from name
                                        category = infer_category_from_name(name)
                                    
                                    if category:
                                        merchant_map[name.lower()] = category
                                        merchant_names.add(name.lower())
                                        
                                        # Also add without spaces for fuzzy matching
                                        merchant_map[name.lower().replace(' ', '')] = category
                                        
                                        # Store abbreviation to merchant name mapping
                                        merchant_map[abbr.lower()] = category
            
            print(f"Loaded additional merchants from short file")
        else:
            print(f"Warning: Short merchant file not found at {merchant_short_file}")
    except Exception as e:
        print(f"Error loading short merchant data: {e}")
    
    return merchant_map

def infer_category_from_name(merchant_name: str) -> str:
    """
    Infer a category from a merchant name when not explicitly listed
    
    Args:
        merchant_name: The merchant name to categorize
        
    Returns:
        The inferred category
    """
    name_lower = merchant_name.lower()
    
    # Keywords that suggest categories
    category_keywords = {
        "Groceries": ["mart", "super", "market", "fresh", "grocer", "food", "basket", "bazar", "hypermarket"],
        "Food Delivery": ["swiggy", "zomato", "food delivery", "uber eats"],
        "Dining": ["restaurant", "biryan", "kitchen", "cuisine", "eatery", "dining"],
        "Fast Food": ["pizza", "burger", "kfc", "mcdonalds", "domino", "subway"],
        "Cafe": ["cafe", "coffee", "chai", "bakery", "starbucks"],
        "Travel": ["travel", "flight", "trip", "holiday", "journey", "stay", "vacation"],
        "Hotels": ["hotel", "resort", "inn", "lodge", "suite", "accommodation"],
        "Ride": ["cab", "taxi", "uber", "ola", "ride", "auto"],
        "Fuel": ["petrol", "gas", "fuel", "petroleum", "pump", "iocl", "bpcl", "hpcl", "cng"],
        "Fashion": ["fashion", "wear", "cloth", "apparel", "myntra", "dress", "trend"],
        "Electronics": ["electronic", "digital", "gadget", "device", "tech", "croma"],
        "Beauty": ["beauty", "cosmetic", "makeup", "salon", "spa", "nyka"],
        "Shopping": ["shop", "store", "mart", "retail", "amazon", "flipkart", "bazaar"],
        "Entertainment": ["cinema", "movie", "theatre", "pvr", "inox", "ticket", "netflix", "hotstar"],
        "Health": ["health", "pharmacy", "medical", "medicine", "hospital", "clinic", "apollo"],
        "Utilities": ["electric", "water", "gas", "utility", "bill", "power", "broadband", "telecom"],
        "Education": ["education", "school", "college", "university", "course", "study", "learn", "tuition"],
        "Insurance": ["insurance", "policy", "cover", "protect", "premium", "plan"]
    }
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category
    
    # Default to Shopping if no match found
    return "Other"

def get_category(merchant_name: str) -> str:
    """
    Get the category for a merchant
    
    Args:
        merchant_name: The merchant name to look up
        
    Returns:
        Category name or "Other" if not found
    """
    # Load merchant data if not loaded yet
    if not merchant_map:
        load_merchant_map()
    
    if not merchant_name:
        return "Other"
        
    merchant_lower = merchant_name.lower()
    
    # Direct lookup
    if merchant_lower in merchant_map:
        return merchant_map[merchant_lower]
    
    # Try without spaces
    if merchant_lower.replace(' ', '') in merchant_map:
        return merchant_map[merchant_lower.replace(' ', '')]
    
    # Try fuzzy matching - check if merchant name contains any known merchant
    for known_merchant in merchant_names:
        if known_merchant in merchant_lower or merchant_lower in known_merchant:
            return merchant_map[known_merchant]
    
    # Try to infer from name
    return infer_category_from_name(merchant_name)

def is_transaction_indicator(text: str) -> bool:
    """
    Check if text contains transaction indicator keywords
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains transaction indicators
    """
    # Load data if not loaded
    if not transaction_indicators:
        load_merchant_map()
    
    text_lower = text.lower()
    
    for indicator in transaction_indicators:
        if indicator in text_lower:
            return True
    
    return False

def is_known_merchant(merchant_name: str) -> bool:
    """
    Check if a merchant name is in our database
    
    Args:
        merchant_name: Merchant name to check
        
    Returns:
        True if this is a known merchant
    """
    # Load data if not loaded
    if not merchant_map:
        load_merchant_map()
    
    if not merchant_name:
        return False
        
    merchant_lower = merchant_name.lower()
    
    # Direct lookup
    if merchant_lower in merchant_map:
        return True
    
    # Try without spaces
    if merchant_lower.replace(' ', '') in merchant_map:
        return True
    
    # Try fuzzy matching - check if merchant name contains any known merchant
    for known_merchant in merchant_names:
        if known_merchant in merchant_lower or merchant_lower in known_merchant:
            return True
    
    return False

def get_all_merchants_by_category(category: str) -> List[str]:
    """
    Get all merchants in a specific category
    
    Args:
        category: Category name
        
    Returns:
        List of merchant names in that category
    """
    # Load data if not loaded
    if not merchant_categories:
        load_merchant_map()
    
    if category in merchant_categories:
        return merchant_categories[category]
    
    return []

def extract_merchant_from_sms(sms_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract merchant name and category from SMS text
    
    Args:
        sms_text: SMS text to analyze
        
    Returns:
        Tuple of (merchant_name, category) or (None, None) if not found
    """
    # Load data if not loaded
    if not merchant_map:
        load_merchant_map()
    
    sms_lower = sms_text.lower()
    
    # First check for direct merchant names
    for merchant in sorted(merchant_names, key=len, reverse=True):
        if merchant in sms_lower:
            category = merchant_map[merchant]
            # Convert back to proper case using the original text
            start_idx = sms_lower.find(merchant)
            end_idx = start_idx + len(merchant)
            original_case = sms_text[start_idx:end_idx]
            return original_case, category
    
    # No direct merchant found
    return None, None

def get_category_for_merchant(merchant_name: str) -> str:
    """
    Get category for a merchant name using enhanced mapping
    
    Args:
        merchant_name: Name of the merchant
        
    Returns:
        Category name
    """
    # Normalize merchant name
    merchant_lower = merchant_name.lower().strip()
    
    # Enhanced category mapping with more specific categories
    category_mapping = {
        'food': [
            'restaurant', 'cafe', 'food', 'dining', 'eatery', 'bistro', 'bakery',
            'pizza', 'burger', 'sandwich', 'coffee', 'tea', 'juice', 'ice cream',
            'dessert', 'sweets', 'confectionery', 'groceries', 'supermarket',
            'provisions', 'food delivery', 'takeaway', 'dine-in'
        ],
        'shopping': [
            'store', 'shop', 'retail', 'mall', 'market', 'bazaar', 'outlet',
            'fashion', 'clothing', 'apparel', 'footwear', 'accessories',
            'electronics', 'gadgets', 'appliances', 'furniture', 'home decor',
            'jewelry', 'watches', 'cosmetics', 'beauty', 'pharmacy', 'medical',
            'books', 'stationery', 'toys', 'games', 'sports', 'fitness'
        ],
        'transport': [
            'taxi', 'cab', 'uber', 'ola', 'auto', 'rickshaw', 'bus', 'train',
            'metro', 'railway', 'airport', 'airlines', 'flight', 'travel',
            'tourism', 'hotel', 'lodging', 'accommodation', 'parking',
            'toll', 'fuel', 'petrol', 'diesel', 'gas', 'vehicle', 'car',
            'bike', 'scooter', 'rental', 'lease'
        ],
        'entertainment': [
            'movie', 'cinema', 'theatre', 'concert', 'show', 'event',
            'amusement', 'park', 'zoo', 'museum', 'gallery', 'exhibition',
            'sports', 'game', 'match', 'tournament', 'gym', 'fitness',
            'yoga', 'dance', 'music', 'art', 'craft', 'hobby', 'club',
            'pub', 'bar', 'lounge', 'casino', 'gaming'
        ],
        'utilities': [
            'electricity', 'power', 'water', 'gas', 'utility', 'bill',
            'mobile', 'phone', 'telephone', 'internet', 'broadband',
            'cable', 'dth', 'tv', 'television', 'newspaper', 'magazine',
            'subscription', 'membership', 'insurance', 'premium',
            'maintenance', 'repair', 'service', 'cleaning', 'security'
        ],
        'education': [
            'school', 'college', 'university', 'institute', 'academy',
            'training', 'course', 'tuition', 'coaching', 'education',
            'learning', 'study', 'books', 'stationery', 'library',
            'research', 'exam', 'test', 'certification', 'degree'
        ],
        'healthcare': [
            'hospital', 'clinic', 'doctor', 'physician', 'dentist',
            'pharmacy', 'medical', 'health', 'wellness', 'fitness',
            'gym', 'yoga', 'therapy', 'treatment', 'diagnostic',
            'laboratory', 'test', 'scan', 'x-ray', 'medicine'
        ],
        'financial': [
            'bank', 'atm', 'finance', 'investment', 'insurance',
            'loan', 'emi', 'credit', 'debit', 'card', 'payment',
            'transfer', 'withdrawal', 'deposit', 'account', 'savings',
            'fixed deposit', 'mutual fund', 'stock', 'share', 'trading'
        ],
        'professional': [
            'consultant', 'advisor', 'lawyer', 'attorney', 'accountant',
            'auditor', 'architect', 'engineer', 'designer', 'developer',
            'programmer', 'writer', 'editor', 'translator', 'interpreter',
            'agent', 'broker', 'dealer', 'distributor', 'supplier'
        ],
        'government': [
            'government', 'municipal', 'corporation', 'council',
            'department', 'ministry', 'office', 'authority', 'agency',
            'commission', 'board', 'court', 'police', 'defense',
            'customs', 'tax', 'revenue', 'license', 'permit', 'fee'
        ]
    }
    
    # Check for exact matches first
    for category, keywords in category_mapping.items():
        if merchant_lower in keywords:
            return category
    
    # Check for partial matches
    for category, keywords in category_mapping.items():
        if any(keyword in merchant_lower for keyword in keywords):
            return category
    
    # Check for common patterns
    patterns = {
        'food': r'(?:restaurant|cafe|food|dining|eatery|bistro|bakery)',
        'shopping': r'(?:store|shop|retail|mall|market|bazaar|outlet)',
        'transport': r'(?:taxi|cab|uber|ola|auto|rickshaw|bus|train)',
        'entertainment': r'(?:movie|cinema|theatre|concert|show|event)',
        'utilities': r'(?:electricity|water|gas|utility|bill|mobile|phone)',
        'education': r'(?:school|college|university|institute|academy)',
        'healthcare': r'(?:hospital|clinic|doctor|physician|dentist)',
        'financial': r'(?:bank|atm|finance|investment|insurance)',
        'professional': r'(?:consultant|advisor|lawyer|attorney|accountant)',
        'government': r'(?:government|municipal|corporation|council)'
    }
    
    for category, pattern in patterns.items():
        if re.search(pattern, merchant_lower):
            return category
    
    # Default to 'other' if no match found
    return 'other'

# Load data on module import
load_merchant_map()

if __name__ == "__main__":
    # Test functionality
    load_merchant_map()
    print(f"Loaded {len(merchant_map)} merchant mappings")
    
    test_merchants = [
        "Swiggy", 
        "Amazon", 
        "IRCTC", 
        "Uber", 
        "HDFC Bank",
        "BigBasket",
        "Zomato",
        "Reliance Fresh",
        "Unknown Merchant"
    ]
    
    print("\nTesting merchant lookups:")
    for merchant in test_merchants:
        category = get_category(merchant)
        print(f"{merchant}: {category}")
    
    print("\nTesting SMS merchant extraction:")
    test_sms = [
        "Your HDFC Bank Card ending with 1234 has been debited for Rs.349 at Swiggy on 30-04-2024.",
        "Rs.15000 credited to your account ending with 5678 on 06-04-2023.",
        "Thank you for shopping at Amazon. Your order for Rs.2500 will be delivered tomorrow.",
        "Your Uber ride from Home to Office cost Rs.250."
    ]
    
    for sms in test_sms:
        merchant, category = extract_merchant_from_sms(sms)
        print(f"SMS: {sms}\nMerchant: {merchant}, Category: {category}\n") 