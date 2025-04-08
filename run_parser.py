#!/usr/bin/env python3

import argparse
import sys
from typing import Dict, Any

from sms_parser.parsers.light_filter import light_filter
from sms_parser.parsers.gemini_parser import parse_sms
from sms_parser.parsers.fallback_parser import parse_sms_fallback
from sms_parser.detectors.fraud_detector import FraudDetector
from sms_parser.core.database import init_database, save_transaction, save_fraud_log, save_promotional_sms
from sms_parser.core.logger import get_logger

logger = get_logger(__name__)

# ... existing code ... 