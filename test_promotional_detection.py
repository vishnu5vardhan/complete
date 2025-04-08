#!/usr/bin/env python3

import unittest
from typing import Dict, Any

from sms_parser.detectors.promo_detector import is_promotional_sms
from sms_parser.tests.test_sms_examples import get_test_sms
from sms_parser.core.logger import get_logger

logger = get_logger(__name__)

# ... existing code ... 