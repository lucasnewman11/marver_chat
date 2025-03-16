# Sales Call Simulator - React Version

This application provides a React-based interface for the Sales Call Simulator, using local transcripts for retrieval-augmented generation (RAG).

## Features

- Chat interface with two modes: Assistant and Sales Simulation
- Local transcript processing and indexing
- Vector similarity search for relevant context retrieval
- Support for both local and Pinecone vector databases
- Automatic loading and processing of transcripts

## Getting Started

1. Install dependencies:
```
npm install
```

2. Start the application:
```
npm start
```

## Configuration

All configuration is handled through environment variables in the `.env` file:

### API Keys and Services

```
# API Keys
REACT_APP_ANTHROPIC_API_KEY=your-anthropic-api-key
REACT_APP_VOYAGE_API_KEY=your-voyage-api-key

# Pinecone settings
REACT_APP_PINECONE_API_KEY=your-pinecone-api-key
REACT_APP_PINECONE_ENVIRONMENT=your-pinecone-environment 
REACT_APP_PINECONE_INDEX_NAME=sales-simulator

# Vector database choice - "pinecone" or "local"
REACT_APP_VECTOR_DB=local
```

## Vector Database Options

This application supports two vector database options:

1. **Local Storage** (`REACT_APP_VECTOR_DB=local`):
   - Uses browser IndexedDB through localforage
   - All processing happens in-browser
   - Data persists across browser sessions
   - Simpler setup, no external dependencies

2. **Pinecone** (`REACT_APP_VECTOR_DB=pinecone`):
   - Uses Pinecone vector database service
   - Requires a Pinecone API key
   - Better performance for larger datasets
   - Persistent storage outside the browser

### Using Pinecone

To use Pinecone:

1. Create a Pinecone account at [https://www.pinecone.io/](https://www.pinecone.io/)
2. Create an API key in the Pinecone dashboard
3. Update your `.env` file with:
   ```
   REACT_APP_PINECONE_API_KEY=your-actual-key
   REACT_APP_PINECONE_ENVIRONMENT=your-environment (e.g., us-west1-gcp)
   REACT_APP_PINECONE_INDEX_NAME=sales-simulator
   REACT_APP_VECTOR_DB=pinecone
   ```

The application will automatically:
- Create an index if it doesn't exist
- Process transcripts and store vectors
- Query the index for relevant content

## Local Transcripts

Transcripts are stored in the `public/transcripts` directory and are loaded and processed automatically when the application starts. The processing workflow:

1. Load transcript metadata
2. Fetch and process each transcript file
3. Split text into meaningful chunks
4. Generate embeddings for each chunk
5. Store in the selected vector database

## Embedding Method

The application uses a simple TF-IDF style embedding approach for matching queries to relevant content. This provides decent semantic search capabilities without requiring external embedding APIs.

## License

This project is licensed under the MIT License.