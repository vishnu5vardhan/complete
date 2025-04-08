#!/usr/bin/env python3

import re
import json
import datetime
from typing import Dict, Any, Optional

from sms_parser.detectors.promo_detector import is_promotional_sms
from sms_parser.parsers.gemini_parser import parse_sms
from sms_parser.parsers.fallback_parser import parse_sms_fallback
from sms_parser.parsers.light_filter import light_filter
from sms_parser.core.logger import get_logger

logger = get_logger(__name__)

import re
import json
import datetime
from typing import Dict, Any, Optional

from sms_parser.detectors.promo_detector import is_promotional_sms
from sms_parser.parsers.gemini_parser import parse_sms
from sms_parser.parsers.fallback_parser import parse_sms_fallback
from sms_parser.parsers.light_filter import light_filter
from sms_parser.core.logger import get_logger

logger = get_logger(__name__) 