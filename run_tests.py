#!/usr/bin/env python3

import os
import sys
import unittest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set ENABLE_MOCK_MODE to True for testing without API key
os.environ["ENABLE_MOCK_MODE"] = "True"

# Run the tests
if __name__ == "__main__":
    # Add the current directory to sys.path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Discover and run tests
    test_suite = unittest.defaultTestLoader.discover('sms_parser/tests', pattern='test_*.py')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Exit with non-zero code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1) 