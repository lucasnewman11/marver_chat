# Claude Google Drive Chatbot

A simple chatbot that uses Claude to interact with your Google Drive documents.

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   - Copy `.env.example` to `.env`
   - Add your Anthropic API key
   - Add Google Service Account JSON (either path or content)

## Google Drive Setup

1. Create a Google Cloud project
2. Enable the Google Drive API
3. Create a service account
4. Generate and download a JSON key for the service account
5. Share the desired Google Drive folders/files with the service account email

## Usage

### Starting the API server:

```bash
python -m src.api
```

The API will be available at `http://localhost:8000`

### API Endpoints:

1. Load documents:
   ```
   POST /load-documents
   {
     "folder_id": "your_google_drive_folder_id",
     "file_ids": ["optional_file_id1", "optional_file_id2"]
   }
   ```

2. Chat with documents:
   ```
   POST /chat
   {
     "message": "What information is in my documents?"
   }
   ```

## Direct Python Usage

```python
from src.chatbot import GoogleDriveChatbot

# Initialize the chatbot
chatbot = GoogleDriveChatbot()

# Load documents from Google Drive
chatbot.load_documents(folder_id="your_folder_id")
# OR
chatbot.load_documents(file_ids=["your_file_id1", "your_file_id2"])

# Chat with your documents
response = chatbot.chat("What information is in my documents?")
print(response)
```