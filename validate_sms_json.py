#!/usr/bin/env python3

import json
from typing import Dict, Any, List, Tuple

def validate_sms_json(data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate the JSON output from Gemini API to ensure it has all required fields
    and correct data types.
    
    Args:
        data: JSON data from Gemini API
        
    Returns:
        Tuple containing:
        - bool: True if valid, False otherwise
        - List[str]: List of validation errors
        - Dict[str, Any]: Cleaned/fixed data with default values for missing fields
    """
    errors = []
    
    # Create a copy of the data to fix
    fixed_data = data.copy() if data else {}
    
    # Required fields and their types
    required_fields = {
        "transaction_amount": float,
        "available_balance": float,
        "account_number": str,
        "transaction_type": str,
        "merchant": str,
        "category": str,
        "transaction_date": str,
        "description": str,
        "is_promotional": bool,
        "is_fraud": bool,
        "is_banking_sms": bool,
        "fraud_risk_level": str,
        "suspicious_indicators": list
    }
    
    # Check for missing fields and fix if possible
    for field, field_type in required_fields.items():
        if field not in fixed_data:
            errors.append(f"Missing field: {field}")
            # Set default values for missing fields
            if field_type == float:
                fixed_data[field] = 0.0
            elif field_type == str:
                fixed_data[field] = ""
            elif field_type == bool:
                fixed_data[field] = False
            elif field_type == list:
                fixed_data[field] = []
    
    # Validate field types and try to fix if possible
    for field, field_type in required_fields.items():
        # Skip if field is missing (already reported above)
        if field not in fixed_data:
            continue
            
        if not isinstance(fixed_data[field], field_type):
            # Try to convert the type if possible
            try:
                if field_type == float:
                    fixed_data[field] = float(fixed_data[field])
                elif field_type == str:
                    fixed_data[field] = str(fixed_data[field])
                elif field_type == bool:
                    # Handle various string representations of boolean
                    if isinstance(fixed_data[field], str):
                        if fixed_data[field].lower() in ('true', 'yes', '1', 't', 'y'):
                            fixed_data[field] = True
                        else:
                            fixed_data[field] = False
                    else:
                        fixed_data[field] = bool(fixed_data[field])
                elif field_type == list and not isinstance(fixed_data[field], list):
                    # Convert to list if it's a string representation of a list
                    if isinstance(fixed_data[field], str):
                        if fixed_data[field].startswith('[') and fixed_data[field].endswith(']'):
                            try:
                                fixed_data[field] = json.loads(fixed_data[field])
                            except json.JSONDecodeError:
                                fixed_data[field] = []
                        else:
                            fixed_data[field] = [fixed_data[field]] if fixed_data[field] else []
                    else:
                        fixed_data[field] = []
            except (ValueError, TypeError):
                errors.append(f"Invalid type for {field}: expected {field_type.__name__}, got {type(fixed_data[field]).__name__}")
                # Set default value
                if field_type == float:
                    fixed_data[field] = 0.0
                elif field_type == str:
                    fixed_data[field] = ""
                elif field_type == bool:
                    fixed_data[field] = False
                elif field_type == list:
                    fixed_data[field] = []
    
    # Validate specific fields
    if "fraud_risk_level" in fixed_data:
        valid_risk_levels = ["none", "low", "medium", "high"]
        if fixed_data["fraud_risk_level"] not in valid_risk_levels:
            errors.append(f"Invalid fraud_risk_level: {fixed_data['fraud_risk_level']}. Must be one of {valid_risk_levels}")
            fixed_data["fraud_risk_level"] = "none"
    
    # Ensure transaction_type is lowercase
    if "transaction_type" in fixed_data:
        fixed_data["transaction_type"] = fixed_data["transaction_type"].lower()
    
    # Validate date format
    if "transaction_date" in fixed_data and fixed_data["transaction_date"]:
        # Simple date validation - should have at least YYYY-MM format
        if len(fixed_data["transaction_date"]) >= 7:
            try:
                # Check if it has valid year and month
                year_str, month_str = fixed_data["transaction_date"].split("-")[:2]
                year = int(year_str)
                month = int(month_str)
                if not (1900 <= year <= 2100 and 1 <= month <= 12):
                    raise ValueError("Invalid year or month")
            except (ValueError, IndexError):
                errors.append(f"Invalid date format: {fixed_data['transaction_date']}. Expected YYYY-MM-DD")
                fixed_data["transaction_date"] = ""
    
    # Handle suspicious indicators
    if "suspicious_indicators" in fixed_data:
        # Ensure it's a list of strings
        try:
            fixed_data["suspicious_indicators"] = [str(item) for item in fixed_data["suspicious_indicators"]]
        except (TypeError, ValueError):
            fixed_data["suspicious_indicators"] = []
    
    # Add duplicate fields needed for frontend compatibility
    if "transaction_amount" in fixed_data:
        fixed_data["amount"] = fixed_data["transaction_amount"]
    
    if "account_number" in fixed_data:
        fixed_data["account"] = fixed_data["account_number"]
        
    if "merchant" in fixed_data:
        fixed_data["merchant_name"] = fixed_data["merchant"]
    
    # Return validation results
    is_valid = len(errors) == 0
    return is_valid, errors, fixed_data

def is_banking_sms(data: Dict[str, Any]) -> bool:
    """
    Check if the SMS is a banking SMS based on the is_banking_sms field
    and other indicators
    
    Args:
        data: Validated JSON data
        
    Returns:
        bool: True if it's a banking SMS, False otherwise
    """
    # Check if explicitly marked as banking SMS
    if data.get("is_banking_sms", False):
        return True
    
    # Check if it has a transaction amount and is not promotional or fraud
    if (data.get("transaction_amount", 0) > 0 and 
        not data.get("is_promotional", False) and 
        not data.get("is_fraud", False) and
        data.get("transaction_type", "")):
        return True
    
    return False

if __name__ == "__main__":
    # Test validation
    test_data = {
        "transaction_amount": "689.0",  # String instead of float
        "available_balance": 12310.0,
        "account_number": "XX1823",
        "transaction_type": "Debit",  # Uppercase
        "merchant": "McDonald's",
        "category": "Dining",
        "transaction_date": "2025-04-03",
        "description": "Credit card payment at McDonald's",
        "is_promotional": "false",  # String instead of boolean
        "is_fraud": False,
        "is_banking_sms": True,
        "fraud_risk_level": "invalid",  # Invalid value
        "suspicious_indicators": "None"  # String instead of list
    }
    
    is_valid, errors, fixed_data = validate_sms_json(test_data)
    
    print(f"Valid: {is_valid}")
    if not is_valid:
        print("\nErrors:")
        for error in errors:
            print(f"- {error}")
    
    print("\nFixed data:")
    print(json.dumps(fixed_data, indent=2)) 