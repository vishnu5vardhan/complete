# SMS Transaction Parser and Recommendation System

A complete system for parsing financial SMS messages, extracting transaction details, categorizing merchants, classifying user archetypes, and providing personalized product recommendations.

## Features

- **SMS Parsing**: Extract transaction details from raw SMS messages
- **Transaction Categorization**: Automatically categorize transactions based on merchant
- **Financial Archetypes**: Classify users into financial archetypes based on spending patterns
- **Product Recommendations**: Provide personalized credit card recommendations based on spending
- **Multiple Interfaces**: CLI, API, and Web UI
- **Analytics**: Track user interactions and gather insights

## System Architecture

- **Enhanced SMS Parser**: Core processing engine powered by Gemini AI
- **SQLite Database**: Persistent storage for transactions and analytics
- **FastAPI Server**: RESTful API for integration
- **CLI Tool**: Command-line interface for batch processing
- **Web Frontend**: User-friendly interface for interaction

## Setup

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd sms-transaction-parser
   ```

2. **Create a virtual environment:**
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Initialize the database:**
   ```
   python db.py
   ```

## Usage

### Command Line Interface

Process a single SMS:
```
python cli.py -s "Your SMS message here"
```

Process multiple SMS from a file:
```
python cli.py -f path/to/sms_file.txt -o results.json
```

### API Server

Start the API server:
```
python api.py
```

The server will run at `http://localhost:8000` with the following endpoints:

- `POST /sms`: Process an SMS message
- `GET /summary`: Get financial summary and archetype
- `GET /recommendations`: Get product recommendations
- `GET /transactions`: Get recent transactions
- `GET /analytics`: Get analytics data

Interactive API documentation available at `http://localhost:8000/docs`

### Web Frontend

1. Start the API server:
   ```
   python api.py
   ```

2. Open `frontend/index.html` in your browser

## Components

- `enhanced_sms_parser.py`: Core engine for SMS parsing and enhancement
- `db.py`: Database utilities for SQLite
- `cli.py`: Command-line interface
- `api.py`: FastAPI server
- `frontend/`: Web interface files
- `services/`: Supporting services (merchant mapping, transaction type detection, etc.)

## Analytics

The system tracks:
- Archetype distribution
- Category spending totals
- Recommendation clicks

View analytics via the `/analytics` API endpoint or run:
```
curl http://localhost:8000/analytics
```

## Example

```python
from enhanced_sms_parser import run_end_to_end

# Process an SMS
result = run_end_to_end("Your card ending with 1234 has been debited for Rs.2500 at Swiggy on 05-04-2023.")

# Print results
print(f"Transaction: {result['transaction']['amount']} {result['transaction']['transaction_type']}")
print(f"Category: {result['category']}")
print(f"Archetype: {result['archetype']}")
print(f"Recommendations: {result['top_3_recommendations']}")
```

## License

MIT
