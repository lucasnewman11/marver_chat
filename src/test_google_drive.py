import os
from dotenv import load_dotenv
import json
from llama_index.readers.google import GoogleDriveReader

# Load environment variables
load_dotenv()

def initialize_drive_reader():
    """Initialize a Google Drive reader"""
    # Get the service account JSON
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not service_account_json:
        print("❌ Google Service Account JSON not found in environment variables")
        return None
        
    # Initialize the Google Drive reader
    try:
        # Check if it's a JSON string or a file path
        if service_account_json and service_account_json.strip().startswith("{"):
            # It's a JSON string
            service_account_key = json.loads(service_account_json)
            drive_reader = GoogleDriveReader(
                service_account_key=service_account_key
            )
        else:
            # Assume it's a file path
            drive_reader = GoogleDriveReader(
                service_account_json=service_account_json
            )
        return drive_reader
    except ValueError as e:
        print(f"❌ Failed to initialize GoogleDriveReader: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error initializing GoogleDriveReader: {str(e)}")
        return None

def test_google_drive_auth():
    """Test if we can authenticate with Google Drive"""
    try:
        print("Testing Google Drive authentication...")
        
        drive_reader = initialize_drive_reader()
        if drive_reader:
            print("✅ Successfully initialized GoogleDriveReader with service account credentials")
            return True
        return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
        
def test_list_folder(folder_id=None):
    """Test if we can list files from a Google Drive folder"""
    if not folder_id:
        print("⚠️ No folder_id provided, skipping folder listing test")
        return None
        
    try:
        print(f"Testing listing files from folder {folder_id}...")
        
        drive_reader = initialize_drive_reader()
        if not drive_reader:
            return False
            
        try:
            # Try to list documents in the folder
            documents = drive_reader.load_data(folder_id=folder_id)
            print(f"✅ Successfully listed {len(documents)} documents from folder")
            
            # Print first few document titles
            if documents:
                print("\nDocuments found:")
                for i, doc in enumerate(documents[:5]):  # Show up to 5 docs
                    print(f"  - {doc.metadata.get('file_name', 'Unknown')}")
                if len(documents) > 5:
                    print(f"  - ... and {len(documents) - 5} more")
                    
            return True
        except Exception as e:
            print(f"❌ Failed to list folder contents: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    auth_result = test_google_drive_auth()
    
    if auth_result:
        print("\nDo you want to test listing files from a Google Drive folder? (y/n)")
        choice = input().strip().lower()
        
        if choice == 'y':
            print("Enter a Google Drive folder ID to test:")
            folder_id = input().strip()
            if folder_id:
                test_list_folder(folder_id)
            else:
                print("No folder ID provided, skipping test.")
    else:
        print("\nAuthentication failed, cannot proceed with folder listing test.")