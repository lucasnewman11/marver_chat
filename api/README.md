# Python Backend for Chatbot

This is a Python backend for the Chatbot application, which provides API endpoints that the React frontend can call to process and query transcripts using Pinecone vector database.

## Features

- FastAPI-based REST API for handling transcript processing and querying
- Efficient memory usage for processing large transcript files
- Background processing to handle long-running tasks
- Idempotent processing that only indexes new transcripts
- Standalone ingestion script for bulk uploading transcripts

## Setup

1. Install dependencies:
   ```bash
   pip install fastapi uvicorn httpx python-dotenv
   ```

2. Set up your environment variables in the `.env` file in the `react-app` directory:
   ```
   REACT_APP_PINECONE_API_KEY=your_pinecone_api_key
   REACT_APP_PINECONE_ENVIRONMENT=us-east-1-aws
   REACT_APP_PINECONE_INDEX_NAME=sales-simulator
   REACT_APP_VOYAGE_API_KEY=your_voyage_api_key (optional)
   ```

## Usage

### Start the API Server

```bash
cd api
uvicorn app:app --reload --port 5000
```

This will start the API server on port 5000, which the React frontend can call.

### API Endpoints

- `GET /api` - Get API status
- `POST /api/indexing/process` - Process and index documents
- `POST /api/indexing/query` - Query for similar documents

### Standalone Transcript Ingestion

For bulk processing transcripts without running the API server:

```bash
cd api
python ingest_transcripts.py
```

This script will:
1. Connect to Pinecone
2. Get a list of already indexed file IDs
3. Find all transcript files in the `all_transcripts` directory
4. Process and index only new transcripts that haven't been indexed before
5. Show progress as it processes files

## Connecting to the React Frontend

The React frontend can call these API endpoints just like it did with the Node.js backend. Make sure your React app is configured to point to this new backend:

```javascript
// In your React app's configuration
const API_URL = 'http://localhost:5000/api';
```

## Memory Efficiency

This Python backend is designed to be memory-efficient:

1. Files are processed one at a time
2. Chunks are processed in small batches
3. Asynchronous processing for better performance
4. No large in-memory collections
5. Python's memory management is more efficient for vector operations

## Troubleshooting

If you encounter any issues:

1. Check if your Pinecone API key is valid
2. Make sure the transcripts directory exists and contains valid files
3. Check if the environment variables are correctly set
4. Look at the server logs for detailed error messages