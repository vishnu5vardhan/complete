#!/usr/bin/env python3

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_URL", "sms_parser/data/sms_data.db")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "sms_parser/data/sms_parser.log")

# Web Interface Configuration
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))

# API Configuration
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Feature flags
ENABLE_MOCK_MODE = os.getenv("ENABLE_MOCK_MODE", "False").lower() == "true"
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "True").lower() == "true"

# Paths to data files
FRAUD_KEYWORDS_PATH = os.getenv("FRAUD_KEYWORDS_PATH", "sms_parser/data/fraud_keywords.txt")
MERCHANT_LIST_PATH = os.getenv("MERCHANT_LIST_PATH", "sms_parser/data/merchant_list.csv") 