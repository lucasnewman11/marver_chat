import os
from dotenv import load_dotenv
import json
import tempfile
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# Load environment variables
load_dotenv()

def list_all_folders():
    """List all folders accessible to the service account"""
    print("Listing folders accessible to the service account...")
    
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
        
        # List all folders the service account has access to
        print("\nQuerying for folders...")
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields="nextPageToken, files(id, name, parents, shared, sharingUser)",
            pageSize=100
        ).execute()
        
        folders = results.get('files', [])
        
        if not folders:
            print('No folders found. The service account may not have access to any folders.')
            return
            
        print(f'Found {len(folders)} folders:\n')
        
        # Print folder details including parent folder if available
        for folder in folders:
            folder_id = folder['id']
            folder_name = folder['name']
            
            # Get parent folder name if available
            parent_info = ""
            if 'parents' in folder:
                try:
                    for parent_id in folder['parents']:
                        parent = service.files().get(fileId=parent_id, fields="name").execute()
                        parent_info = f" (parent: {parent['name']} - {parent_id})"
                except HttpError:
                    parent_info = " (parent folder access denied)"
            
            # Print folder details
            print(f"Folder: {folder_name}")
            print(f"ID: {folder_id}{parent_info}")
            
            # Print sharing information if available
            if folder.get('shared', False):
                sharing_user = folder.get('sharingUser', {})
                share_info = ""
                if sharing_user:
                    share_info = f" (shared by: {sharing_user.get('displayName', 'Unknown')})"
                print(f"Shared: Yes{share_info}")
            else:
                print("Shared: No")
                
            # List contents of this folder (first level only)
            try:
                folder_contents = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces='drive',
                    fields="files(id, name, mimeType)",
                    pageSize=10
                ).execute()
                
                contents = folder_contents.get('files', [])
                if contents:
                    print(f"Contents (first {min(len(contents), 10)} items):")
                    for item in contents[:10]:
                        item_type = "Folder" if item['mimeType'] == 'application/vnd.google-apps.folder' else "File"
                        print(f"  - {item_type}: {item['name']} (ID: {item['id']})")
                    
                    if len(contents) > 10:
                        print(f"  - ... and {len(contents) - 10} more items")
                else:
                    print("Contents: Empty folder")
            except HttpError as error:
                print(f"Could not list contents: {error}")
            
            print("")  # Add a blank line between folders
            
    except HttpError as error:
        print(f'An error occurred: {error}')
    except Exception as e:
        print(f'An error occurred: {e}')
    finally:
        # Clean up
        os.remove(path)

def list_drive_root():
    """List files and folders in the root of Drive"""
    print("Attempting to list files and folders in the Drive root...")
    
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
        
        print("\nQuerying for root items...")
        # Try to list files in the root
        # This query tries to find files that don't have a parent
        # Note: This might not work as expected with service accounts
        results = service.files().list(
            q="'root' in parents and trashed=false",
            spaces='drive',
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=100
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print('No files found in root. The service account may not have access to the root.')
            return
            
        print(f'Found {len(items)} items in root:\n')
        
        # Group items by type
        folders = [item for item in items if item['mimeType'] == 'application/vnd.google-apps.folder']
        files = [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
        
        # Print folders first
        if folders:
            print("ROOT FOLDERS:")
            for folder in folders:
                print(f"ID: {folder['id']} | Name: {folder['name']}")
            print("")
        
        # Print files
        if files:
            print("ROOT FILES:")
            for file in files:
                print(f"ID: {file['id']} | Name: {file['name']} | Type: {file['mimeType']}")
            print("")
            
    except HttpError as error:
        print(f'An error occurred: {error}')
    except Exception as e:
        print(f'An error occurred: {e}')
    finally:
        # Clean up
        os.remove(path)

if __name__ == '__main__':
    print("==== LISTING ALL FOLDERS ====")
    list_all_folders()
    
    print("\n==== LISTING ROOT DIRECTORY ====")
    list_drive_root()