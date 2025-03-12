# Deployment Guide for Sales Call Simulator

This guide walks you through the process of deploying the Sales Call Simulator to Streamlit Cloud.

## Prerequisites

Before deploying, you need:

1. **API Keys**:
   - Anthropic API key
   - Pinecone API key
   - Voyage AI API key (or alternative embedding provider)

2. **Google Drive Setup**:
   - Google Cloud project
   - Service account with Drive access
   - Service account JSON credentials
   - Folders shared with service account email

3. **GitHub Account**:
   - Repository for this project
   - Git installed locally

## Step 1: Configure Local Environment

1. Fill in your API keys in `.streamlit/secrets.toml`:
   ```toml
   ANTHROPIC_API_KEY = "your_anthropic_key"
   PINECONE_API_KEY = "your_pinecone_key"
   PINECONE_ENVIRONMENT = "your_pinecone_environment"
   PINECONE_INDEX_NAME = "sales-simulator"
   VOYAGE_API_KEY = "your_voyage_key"
   
   # Paste your entire service account JSON here
   GOOGLE_SERVICE_ACCOUNT_JSON = """
   {
     "type": "service_account",
     ...
   }
   """
   ```

2. Test locally with:
   ```bash
   chmod +x run_local.sh
   ./run_local.sh
   ```

## Step 2: Push to GitHub

1. Create a new repository on GitHub

2. Initialize git and push your code:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/your-username/your-repo-name.git
   git push -u origin main
   ```

## Step 3: Deploy to Streamlit Cloud

1. Sign up/login to [Streamlit Cloud](https://streamlit.io/cloud)

2. Click "New app"

3. Select your GitHub repository, branch, and the main file path (`app.py`)

4. Click "Deploy"

## Step 4: Configure Secrets in Streamlit Cloud

1. Once deployed, go to your app settings

2. Navigate to the "Secrets" section

3. Add the same secrets as in your local `.streamlit/secrets.toml` file:
   ```toml
   ANTHROPIC_API_KEY = "your_anthropic_key"
   PINECONE_API_KEY = "your_pinecone_key"
   PINECONE_ENVIRONMENT = "your_pinecone_environment"
   PINECONE_INDEX_NAME = "sales-simulator"
   VOYAGE_API_KEY = "your_voyage_key"
   
   # Paste your entire service account JSON here
   GOOGLE_SERVICE_ACCOUNT_JSON = """
   {
     "type": "service_account",
     ...
   }
   """
   ```

4. Save your secrets

## Step 5: Using the Deployed App

1. Open your app's URL

2. Enter your Google Drive folder IDs in the sidebar:
   - Simulation Folder ID (high-quality calls)
   - Technical Folder ID (product specs, etc.)
   - General Folder ID (other calls)

3. Click "Load and Index Documents"

4. Once indexed, you can use the chat interface!

## Troubleshooting

If you encounter issues:

1. **App crashes during loading**: Check your Google Drive folder IDs and make sure the service account has access

2. **API errors**: Verify your API keys are correct in the Streamlit Cloud secrets

3. **Memory errors**: You might need to reduce the number of documents or chunk size if you hit Streamlit's memory limits