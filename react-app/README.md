# Sales Call Simulator - React Version

This application provides a React-based interface for the Sales Call Simulator. It allows you to load and process documents from Google Drive, index them using Pinecone and VoyageAI embeddings, and chat with Claude based on the processed documents.

## Features

- Document loading from Google Drive (simulation, technical, and general categories)
- Document processing and indexing with different chunking strategies
- Dual-mode chat interface:
  - Assistant mode: Provides factual information about the documents
  - Sales Simulation mode: Responds as if it were a salesperson on a call
- Secure API key storage in local browser storage
- Vector similarity search with filters based on document type

## Prerequisites

- Node.js 14+ and npm
- Google Service Account with Drive API access
- API keys for:
  - Anthropic Claude
  - VoyageAI
  - Pinecone

## Setup

1. Clone the repository
2. Install dependencies:

```
npm install
```

3. Create a `.env` file with the following variables (optional for development):

```
REACT_APP_API_URL=http://localhost:5000/api
```

4. Start the development server:

```
npm start
```

5. In a separate terminal, start the API server:

```
npm run api
```

## Configuration

Before using the application, you'll need to configure it with your API keys and settings:

1. **API Keys Tab**:
   - Enter your Anthropic API key
   - Enter your VoyageAI API key
   - Enter your Pinecone API key
   - Configure your Pinecone environment and index name

2. **Documents Tab**:
   - Paste your Google Service Account JSON
   - Enter Google Drive folder IDs for your documents:
     - Simulation folder: High-quality sales call transcripts
     - Technical folder: Product specifications and technical documents
     - General folder: Other call transcripts or general documentation

## Usage

1. Configure the application with your API keys and settings
2. Load and index your documents using the "Load and Index Documents" button
3. Switch between Assistant and Simulation modes as needed
4. Start chatting by typing your message in the input field

## Architecture

- **Frontend**: React with functional components and hooks
- **Backend**: Express server with RESTful API endpoints
- **External Services**:
  - Google Drive: Document storage
  - VoyageAI: Document and query embeddings
  - Pinecone: Vector database for similarity search
  - Anthropic Claude: LLM for response generation

## Development

### File Structure

```
/react-app
  /public
  /src
    /components      # UI components
    /services        # API service modules
    /context         # React context providers
    /hooks           # Custom React hooks
    /utils           # Utility functions
  /api
    /controllers     # API endpoint handlers
    /middleware      # Express middleware
    /routes          # API route definitions
    /services        # Business logic
    /utils           # Utility functions
```

### Adding New Features

1. Create the necessary backend endpoints in `/api/routes`
2. Implement the frontend services in `/src/services`
3. Create or update UI components in `/src/components`
4. Connect everything in the main App component

## License

This project is licensed under the MIT License - see the LICENSE file for details.