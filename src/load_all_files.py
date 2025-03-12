import os
from dotenv import load_dotenv
import tempfile
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from anthropic import Anthropic
from tqdm import tqdm

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

def get_all_files():
    """Get all files accessible to the service account"""
    service = get_google_drive_service()
    
    print("Fetching list of all accessible files...")
    results = service.files().list(
        q="trashed=false and mimeType='application/vnd.google-apps.document'",
        spaces='drive',
        fields="nextPageToken, files(id, name)",
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    
    if not files:
        print('No files found.')
        return []
        
    print(f"Found {len(files)} files.")
    return files

def get_file_content(service, file_id):
    """Get the content of a Google Drive file"""
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
            return content.decode('utf-8'), file['name']
        else:
            # For other file types
            content = service.files().get_media(fileId=file_id).execute()
            return content.decode('utf-8'), file['name']
    except HttpError as error:
        print(f'Error retrieving file {file_id}: {error}')
        return None, None

def save_all_contents(file_list):
    """Save all file contents to a local file"""
    service = get_google_drive_service()
    
    # Create a directory to store all the files
    os.makedirs("all_transcripts", exist_ok=True)
    
    # Save the files
    print(f"Retrieving and saving content from {len(file_list)} files...")
    
    # Dictionary to store file metadata and content
    all_files_data = {}
    
    for file in tqdm(file_list):
        file_id = file['id']
        file_name = file['name']
        
        content, _ = get_file_content(service, file_id)
        if content:
            # Save to file
            file_path = os.path.join("all_transcripts", f"{file_id}.txt")
            with open(file_path, "w") as f:
                f.write(content)
            
            # Add to dictionary
            all_files_data[file_id] = {
                "name": file_name,
                "path": file_path,
                "content_length": len(content)
            }
    
    # Save metadata
    with open("all_transcripts/metadata.json", "w") as f:
        json.dump(all_files_data, f, indent=2)
    
    print(f"Successfully saved {len(all_files_data)} files to the 'all_transcripts' directory.")
    return all_files_data

def perform_rag_query(file_data, query):
    """Perform a RAG query on the downloaded content"""
    # Initialize Anthropic client
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Collect all the content (with size limit)
    contents = []
    total_chars = 0
    max_chars = 50000  # Limit total content to ~50k chars to avoid token limits
    
    print(f"Loading content for RAG query...")
    for file_id, metadata in file_data.items():
        path = metadata["path"]
        
        with open(path, "r") as f:
            content = f.read()
            
            # Add a truncated version if needed
            if total_chars + len(content) > max_chars:
                available_chars = max_chars - total_chars
                if available_chars < 1000:  # Skip if we can only add a tiny fragment
                    continue
                    
                content = content[:available_chars]
                contents.append(f"[From {metadata['name']} - TRUNCATED]\n{content}")
                total_chars = max_chars
                break
            else:
                contents.append(f"[From {metadata['name']}]\n{content}")
                total_chars += len(content)
    
    print(f"Loaded {len(contents)} documents with {total_chars} characters total")
    
    # Combine the contents
    combined_content = "\n\n---\n\n".join(contents)
    
    print(f"\nAsking Claude: {query}")
    
    prompt = f"""
    You are a helpful AI research assistant analyzing sales call transcripts. Please answer the following question based on all the sales call transcript documents I'll provide below.
    
    QUESTION: {query}
    
    TRANSCRIPTS:
    {combined_content}
    """
    
    response = anthropic_client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    print("\nClaude's response:")
    print(response.content[0].text)
    return response.content[0].text

if __name__ == "__main__":
    # Get all files
    files = get_all_files()
    
    # Save their contents
    file_data = save_all_contents(files)
    
    # Now we can perform RAG queries using the saved content
    print("\nWe've now saved all file contents to the 'all_transcripts' directory.")
    print("You can use this content for RAG queries.")
    
    # Ask if the user wants to try a query
    print("\nWould you like to try a RAG query on all the content? (y/n)")
    choice = input().strip().lower()
    
    if choice == 'y':
        print("\nEnter your question about the sales call transcripts:")
        query = input().strip()
        if query:
            perform_rag_query(file_data, query)
    else:
        print("\nYou can run this script again or use the saved content for RAG queries later.")
        print("All transcripts are saved in the 'all_transcripts' directory.")
        print("A metadata.json file contains the mapping between file IDs and filenames.")