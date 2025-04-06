# SMS Transaction Parser and Recommendation System

A complete system for parsing financial SMS messages, extracting transaction details, categorizing merchants, classifying user archetypes, and providing personalized product recommendations.

## Features

- **SMS Parsing**: Extract transaction details from raw SMS messages
- **Transaction Categorization**: Automatically categorize transactions based on merchant
- **Financial Archetypes**: Classify users into financial archetypes based on spending patterns
- **Product Recommendations**: Provide personalized credit card recommendations based on spending
- **Multiple Interfaces**: CLI, API, and Web UI
- **Analytics**: Track user interactions and gather insights
- **LangChain Integration**: Optional LangChain-powered workflows for enhanced capabilities

## System Architecture

- **Enhanced SMS Parser**: Core processing engine powered by Gemini AI
- **LangChain Integration**: Optional structured processing workflows using LangChain
- **SQLite Database**: Persistent storage for transactions and analytics
- **FastAPI Server**: RESTful API for integration
- **CLI Tool**: Command-line interface for batch processing
- **Web Frontend**: User-friendly interface for interaction
- **Background Service**: Real-time SMS monitoring and processing

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

Check account balances:
```
python cli.py -b
```

View financial insights:
```
python cli.py -i
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
- `GET /balance`: Get account balances
- `POST /question`: Process financial questions
- `POST /background/enqueue`: Add SMS to background processing queue
- `GET /background/status`: Get background service status
- `POST /background/start`: Start background service
- `POST /background/stop`: Stop background service

Interactive API documentation available at `http://localhost:8000/docs`

### Web Frontend

1. Start the API server:
   ```
   python api.py
   ```

2. Open `frontend/chat.html` in your browser for the interactive chat interface

## Components

- `enhanced_sms_parser.py`: Core engine for SMS parsing and enhancement
- `langchain_wrapper.py`: LangChain integration for structured data extraction
- `db.py`: Database utilities for SQLite
- `cli.py`: Command-line interface
- `api.py`: FastAPI server
- `background_service.py`: Real-time SMS monitoring service
- `frontend/`: Web interface files
- `services/`: Supporting services (merchant mapping, transaction type detection, etc.)

## LangChain Integration

The system now supports LangChain integration for enhanced capabilities:

```python
# Using the LangChain wrapper
from langchain_wrapper import ask_gemini, extract_structured_data

# Simple query with LangChain
response = ask_gemini("What's the best credit card for travel?")

# Structured data extraction
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "number"}
    }
}
data = extract_structured_data("John Doe is 30 years old", schema)
```

To test the LangChain integration:
```
python test_langchain.py
```

The integration maintains the same outputs and behavior as the direct Gemini API implementation while adding structured extraction capabilities.

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
