import os
from dotenv import load_dotenv
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from anthropic import Anthropic

# Load environment variables
load_dotenv()

def get_google_drive_service():
    """Create a Google Drive service"""
    # Get the service account key
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not service_account_json:
        raise ValueError("Google Service Account JSON not found in environment variables")
    
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
        return service
    finally:
        # Clean up
        os.remove(path)

def get_file_content(file_id):
    """Get the content of a Google Drive file"""
    service = get_google_drive_service()
    
    try:
        # Get the file metadata
        file = service.files().get(fileId=file_id).execute()
        
        # If it's a Google Doc
        if file['mimeType'] == 'application/vnd.google-apps.document':
            # Export as plain text
            content = service.files().export(
                fileId=file_id,
                mimeType='text/plain'
            ).execute()
            return content.decode('utf-8')
        else:
            # For other file types
            content = service.files().get_media(fileId=file_id).execute()
            return content.decode('utf-8')
    except HttpError as error:
        print(f'An error occurred: {error}')
        return f"Error: {error}"

def simple_chatbot_test():
    """Test a simplified version of the chatbot functionality"""
    print("Running simple chatbot test...")
    
    # Initialize Anthropic client
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # File IDs to test with (just using a few of the available ones)
    file_ids = [
        # Sales call transcripts
        "1EmF_3pnHuR2zMZ8IeDDLMdNM8KozU1zIxNzE-R2fd20",
        "175_pqhVhzaRee5afrMx6dQXaTHw_ckqfzULoOPNat5k"
    ]
    
    print("Fetching file contents...")
    contents = []
    for file_id in file_ids:
        print(f"Getting content for file {file_id}...")
        content = get_file_content(file_id)
        if content.startswith("Error:"):
            print(f"  Failed: {content}")
        else:
            print(f"  Success: Retrieved {len(content)} characters")
            contents.append(content)
    
    if not contents:
        print("No file contents retrieved. Cannot continue.")
        return
    
    # Combine the contents (limited to avoid token limits)
    combined_content = "\n\n---\n\n".join(content[:5000] for content in contents)
    
    print("\nAsking Claude a question about the content...")
    query = "What are the main topics discussed in these sales call transcripts?"
    
    prompt = f"""
    Please analyze the following sales call transcripts and answer this question:
    {query}
    
    TRANSCRIPTS:
    {combined_content}
    """
    
    response = anthropic_client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    print(f"\nResponse to query '{query}':")
    print(response.content[0].text)

if __name__ == "__main__":
    simple_chatbot_test()