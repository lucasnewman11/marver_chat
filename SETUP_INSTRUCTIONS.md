# Claude Google Drive Chatbot - Setup Instructions

## Accessing Your Google Drive Content

The service account email address for this chatbot is:
```
transcript-creator@sales-calls-transcripts.iam.gserviceaccount.com
```

### Method 1: Use Existing Files

The service account already has access to 49 Google Docs files with sales call transcripts. You can use these files directly with the chatbot:

```python
from src.chatbot import GoogleDriveChatbot

# Initialize the chatbot
chatbot = GoogleDriveChatbot()

# Load specific files by ID
file_ids = [
    "1EmF_3pnHuR2zMZ8IeDDLMdNM8KozU1zIxNzE-R2fd20",
    "175_pqhVhzaRee5afrMx6dQXaTHw_ckqfzULoOPNat5k"
    # Add more file IDs as needed
]
chatbot.load_documents(file_ids=file_ids)

# Chat with your documents
response = chatbot.chat("What information is in my documents?")
print(response)
```

For convenience, we've created a script that uses a subset of these files:
```
python -m src.use_all_files
```

### Method 2: Create a New Folder Structure

If you want to organize your files in a folder structure:

1. In Google Drive, create a new folder (e.g., "Sales Call Transcripts")
2. Share this folder with the service account email address:
   - Right-click on the folder
   - Click "Share"
   - Enter: `transcript-creator@sales-calls-transcripts.iam.gserviceaccount.com`
   - Make sure to grant "Editor" access
   - Click "Share"
3. Move your documents into this folder
4. Get the folder ID from the URL:
   - Open the folder in Google Drive
   - The URL will look like: `https://drive.google.com/drive/folders/YOUR_FOLDER_ID`
   - Copy the `YOUR_FOLDER_ID` portion
5. Use this folder ID in your code:

```python
from src.chatbot import GoogleDriveChatbot

# Initialize the chatbot
chatbot = GoogleDriveChatbot()

# Load documents from a folder
folder_id = "YOUR_FOLDER_ID"
chatbot.load_documents(folder_id=folder_id)

# Chat with your documents
response = chatbot.chat("What information is in my documents?")
print(response)
```

### Finding File and Folder IDs

To list all files and folders the service account has access to:
```
python -m src.list_drive_files
```

## Running the Chatbot API

To start the API server:
```
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