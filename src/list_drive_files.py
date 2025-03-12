import os
from dotenv import load_dotenv
import json
import pickle
import tempfile
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# Load environment variables
load_dotenv()

def list_all_files():
    """List all files accessible to the service account"""
    print("Listing files accessible to the service account...")
    
    # Get the service account key
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not service_account_json:
        print("Google Service Account JSON not found in environment variables")
        return
    
    # Create a temporary file to store the service account key
    fd, path = tempfile.mkstemp()
    try:
        with os.fdopen(fd, 'w') as tmp:
            # Check if it's a JSON string
            if service_account_json.strip().startswith('{'):
                tmp.write(service_account_json)
            else:
                # It might be a path to a file
                with open(service_account_json, 'r') as f:
                    tmp.write(f.read())
                    
        # Set up the Drive API client
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        # List all files the service account has access to
        results = service.files().list(
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, owners, shared, sharingUser)",
            q="trashed=false"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print('No files found.')
            return
            
        print(f'Found {len(items)} files:')
        
        # Group items by type
        folders = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
        files = [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
        
        # Print folders first
        print("\nFOLDERS:")
        for folder in folders:
            print(f"ID: {folder['id']} | Name: {folder['name']}")
        
        # Print files
        print("\nFILES:")
        for file in files:
            print(f"ID: {file['id']} | Name: {file['name']} | Type: {file['mimeType']}")
            
    except HttpError as error:
        print(f'An error occurred: {error}')
    except Exception as e:
        print(f'An error occurred: {e}')
    finally:
        # Clean up
        os.remove(path)

if __name__ == '__main__':
    list_all_files()