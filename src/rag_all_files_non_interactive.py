import os
from dotenv import load_dotenv
import tempfile
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from anthropic import Anthropic
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# Load environment variables
load_dotenv()

# Set this to True to load files from Google Drive
# Set to False to load from local cache if available
LOAD_FROM_DRIVE = False

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

def download_file(args):
    """Download a single file (for parallel processing)"""
    service, file = args
    file_id = file['id']
    file_name = file['name']
    
    content, _ = get_file_content(service, file_id)
    if content:
        # Only return if we have content
        return file_id, file_name, content
    return None

def save_all_contents(file_list):
    """Save all file contents to a local file with parallel downloading"""
    # Create a directory to store all the files
    os.makedirs("all_transcripts", exist_ok=True)
    
    # Check if we already have saved content
    metadata_path = "all_transcripts/metadata.json"
    if os.path.exists(metadata_path) and not LOAD_FROM_DRIVE:
        print("Loading file data from local cache...")
        with open(metadata_path, "r") as f:
            all_files_data = json.load(f)
        print(f"Loaded metadata for {len(all_files_data)} files from cache.")
        return all_files_data
    
    # We need to download from Google Drive
    service = get_google_drive_service()
    
    # Save the files
    print(f"Retrieving and saving content from {len(file_list)} files...")
    
    # Dictionary to store file metadata and content
    all_files_data = {}
    
    # Prepare arguments for parallel download
    args_list = [(service, file) for file in file_list]
    
    # Use ThreadPoolExecutor for parallel downloads
    max_workers = min(10, len(file_list))  # Don't use more than 10 workers
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_file, args) for args in args_list]
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading files"):
            result = future.result()
            if result:
                file_id, file_name, content = result
                
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
    with open(metadata_path, "w") as f:
        json.dump(all_files_data, f, indent=2)
    
    print(f"Successfully saved {len(all_files_data)} files to the 'all_transcripts' directory.")
    return all_files_data

def smart_document_selection(file_data, query, max_chars=100000):
    """Select documents that are most relevant to the query"""
    # For now, we'll just select documents based on available space
    # In a more advanced version, we could use embeddings to select the most relevant documents
    
    contents = []
    total_chars = 0
    
    # First pass: collect all documents
    all_docs = []
    for file_id, metadata in file_data.items():
        path = metadata["path"]
        
        with open(path, "r") as f:
            content = f.read()
            all_docs.append({
                "id": file_id,
                "name": metadata["name"],
                "content": content,
                "length": len(content)
            })
    
    # Sort documents by name to group similar documents together
    all_docs.sort(key=lambda x: x["name"])
    
    # Add documents until we hit the character limit
    for doc in all_docs:
        if total_chars + doc["length"] > max_chars:
            # Check if we have space for a truncated version
            available_chars = max_chars - total_chars
            if available_chars >= 1000:  # Only add if we can include a substantial portion
                truncated_content = doc["content"][:available_chars]
                contents.append(f"[From {doc['name']} - TRUNCATED]\n{truncated_content}")
                total_chars = max_chars
                break
        else:
            contents.append(f"[From {doc['name']}]\n{doc['content']}")
            total_chars += doc["length"]
    
    return contents, total_chars

def load_transcript_metadata():
    """Load transcript metadata from local cache"""
    metadata_path = "all_transcripts/metadata.json"
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            all_files_data = json.load(f)
        return all_files_data
    else:
        # If metadata doesn't exist, create it
        files = get_all_files()
        file_data = save_all_contents(files)
        return file_data

def load_transcript_content(file_data, query="", max_chars=100000):
    """Load transcript content for RAG"""
    contents, total_chars = smart_document_selection(file_data, query, max_chars)
    return contents

def query_claude(query, contents, system_prompt=None):
    """Query Claude with the given query and contents"""
    # Initialize Anthropic client
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Combine the contents
    combined_content = "\n\n---\n\n".join(contents)
    
    # Use default system prompt if none provided
    if system_prompt is None:
        system_prompt = "You are a helpful AI research assistant analyzing sales call transcripts. Please answer the following question based on all the sales call transcript documents provided below."
    
    response = anthropic_client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=2000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"""
            QUESTION: {query}
            
            TRANSCRIPTS:
            {combined_content}
            """}
        ]
    )
    
    return response.content[0].text

def perform_rag_query(file_data, query):
    """Perform a RAG query on the downloaded content"""
    print(f"Loading content for RAG query...")
    contents = load_transcript_content(file_data, query)
    print(f"Loaded {len(contents)} documents with {sum(len(c) for c in contents)} characters total")
    
    print(f"\nAsking Claude: {query}")
    
    response = query_claude(query, contents)
    
    print("\nClaude's response:")
    print(response)
    return response

if __name__ == "__main__":
    # Check if a query was provided as a command-line argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        
        # Get all files
        files = get_all_files()
        
        # Save their contents
        file_data = save_all_contents(files)
        
        # Perform the query
        perform_rag_query(file_data, query)
    else:
        print("Please provide a query as a command-line argument.")
        print("Example: python -m src.rag_all_files_non_interactive 'What common objections are mentioned in these sales calls?'")
        sys.exit(1)