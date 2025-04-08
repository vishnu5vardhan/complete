# SMS Parser

A comprehensive SMS parser for banking transactions, promotional messages, and fraud detection.

## Features

- Parse banking transaction SMS messages
- Detect promotional SMS messages
- Identify potential fraud in SMS messages
- Light filtering to quickly identify irrelevant messages
- Fallback parsing when API is unavailable
- Database storage for transactions and fraud logs
- Web interface for easy interaction
- CLI tool for command-line usage

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sms-parser.git
cd sms-parser
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Usage

### CLI

```bash
# Parse a single SMS
sms-parser -s "Your account XX1234 has been debited with Rs.1500.00" -f HDFCBK

# Parse with verbose output
sms-parser -s "Your SMS text here" -f SENDER -v

# Output as JSON
sms-parser -s "Your SMS text here" -f SENDER -j
```

### Web Interface

```bash
# Start the web server
python sms_web.py
```

Then open your browser to `http://localhost:5000`

### Python API

```python
from sms_parser.cli.main import process_sms

result = process_sms("Your SMS text here", sender="SENDER")
print(result)
```

## Project Structure

```
sms_parser/
├── cli/                # Command-line interface
├── core/               # Core functionality
│   ├── config.py      # Configuration settings
│   ├── database.py    # Database operations
│   └── logger.py      # Logging setup
├── detectors/          # Detection modules
│   ├── fraud_detector.py
│   └── promo_detector.py
├── parsers/           # Parsing modules
│   ├── base_parser.py
│   ├── fallback_parser.py
│   ├── gemini_parser.py
│   └── light_filter.py
└── tests/             # Test files
    └── test_sms_examples.py
```

## Testing

Run the test suite:
```bash
python -m pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
