# Sales Call Simulator

A Streamlit application for simulating sales calls based on real transcript data, with a hybrid RAG system for retrieving specific information.

## Features

- **Dual Mode Operation**: Switch between general assistant mode and sales call simulation
- **Smart Document Processing**: 
  - High-quality call transcripts loaded with minimal chunking for authentic simulation
  - Technical documents chunked for precise information retrieval
- **Google Drive Integration**: Load documents directly from your Drive folders
- **Pinecone Vector Database**: Fast, scalable vector search for efficient retrieval

## Setup

1. **Create API Keys**:
   - [Anthropic](https://www.anthropic.com/) - For Claude API access
   - [Pinecone](https://www.pinecone.io/) - For vector database
   - [Voyage AI](https://voyageai.com/) - For embeddings (optional, can use OpenAI embeddings)

2. **Google Drive Setup**:
   - Create a service account with Drive access
   - Share your document folders with the service account email
   - Organize folders:
     - High-quality complete call transcripts in a "Simulation" folder
     - Technical documents in a "Technical" folder
     - Other call transcripts in a "General" folder

3. **Configuration**:
   - Set up your secrets in `.streamlit/secrets.toml` for local testing
   - When deploying, add these same secrets to Streamlit Cloud

## Deployment

1. Push this code to a GitHub repository
2. Visit [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repo
4. Add your secrets in the Streamlit dashboard
5. Deploy!

## Usage

1. After deployment, open the app and enter your Google Drive folder IDs
2. Load and index your documents (this may take a few minutes)
3. Switch between Assistant and Simulation modes using the sidebar
4. Chat with the system!