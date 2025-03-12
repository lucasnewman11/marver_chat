import streamlit as st
import os
import tempfile
from dotenv import load_dotenv
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pinecone
from anthropic import Anthropic
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from old llama_index version (0.9.x)
from llama_index import VectorStoreIndex, Document, ServiceContext
from llama_index import set_global_service_context
from llama_index.vector_stores import PineconeVectorStore
from llama_index.storage.storage_context import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding  # Use OpenAI embeddings instead of Voyage
from llama_index.llms.anthropic import Anthropic as LlamaIndexAnthropic
from llama_index.langchain_helpers.text_splitter import SentenceSplitter
from llama_index.readers.google import GoogleDriveReader

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Sales Call Simulator",
    page_icon="☎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title
st.title("Sales Call Simulator")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = "assistant"  # or "simulation"
if "initialized" not in st.session_state:
    st.session_state.initialized = False

# Sidebar for configuration
st.sidebar.title("Configuration")
mode = st.sidebar.radio("Mode", ["Assistant", "Sales Simulation"])
st.session_state.mode = mode.lower()

# Function to get secrets
def get_secret(key):
    # Try to get from Streamlit secrets first (for deployment)
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    # Then try environment variables (for local development)
    return os.getenv(key)

# Initialize Google Drive service
@st.cache_resource
def get_google_drive_service():
    """Create a Google Drive service"""
    # Get the service account key
    service_account_json = get_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    
    if not service_account_json:
        raise ValueError("Google Service Account JSON not found")
    
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

# Initialize Pinecone
@st.cache_resource
def init_pinecone():
    api_key = get_secret("PINECONE_API_KEY")
    environment = get_secret("PINECONE_ENVIRONMENT")
    
    if not api_key or not environment:
        raise ValueError("Pinecone API key or environment not found")
    
    pinecone.init(api_key=api_key, environment=environment)
    
    index_name = get_secret("PINECONE_INDEX_NAME") or "sales-simulator"
    
    # Check if index exists, create if it doesn't
    if index_name not in pinecone.list_indexes():
        # Use OpenAI dimensions (1536) as default
        pinecone.create_index(index_name, dimension=1536, metric="cosine")
        st.sidebar.success(f"Created new Pinecone index: {index_name}")
    
    return pinecone.Index(index_name)

# Initialize LlamaIndex components
@st.cache_resource
def init_llama_index():
    # Set up embedding model
    embed_model = OpenAIEmbedding(
        api_key=get_secret("ANTHROPIC_API_KEY"),  # Using Anthropic key for now 
        embed_batch_size=10
    )
    
    # Set up LLM
    llm = LlamaIndexAnthropic(
        api_key=get_secret("ANTHROPIC_API_KEY"),
        model="claude-3-7-sonnet-20250219"
    )
    
    # Create service context
    service_context = ServiceContext.from_defaults(
        llm=llm,
        embed_model=embed_model,
    )
    
    # Set as global default
    set_global_service_context(service_context)
    
    return service_context

# Initialize vector store and index
@st.cache_resource
def init_vector_store():
    pinecone_index = init_pinecone()
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create empty index if not existing
    try:
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            service_context=init_llama_index()
        )
    except Exception as e:
        st.sidebar.warning(f"Creating new index: {e}")
        index = VectorStoreIndex.from_documents(
            [],  # Empty index to start
            storage_context=storage_context,
            service_context=init_llama_index()
        )
    
    return index, vector_store

# Initialize Anthropic client
@st.cache_resource
def init_anthropic():
    return Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))

# Document loading functions
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
    except Exception as error:
        st.error(f'Error retrieving file {file_id}: {error}')
        return None, None

def download_file(args):
    """Download a single file (for parallel processing)"""
    service, file, file_type = args
    file_id = file['id']
    file_name = file['name']
    
    content, _ = get_file_content(service, file_id)
    if content:
        # Only return if we have content
        return file_id, file_name, content, file_type
    return None

def load_documents_from_drive(simulation_folder_id=None, technical_folder_id=None, general_folder_id=None):
    """Load documents from Google Drive folders"""
    
    if not any([simulation_folder_id, technical_folder_id, general_folder_id]):
        raise ValueError("At least one folder ID must be provided")
    
    service = get_google_drive_service()
    all_documents = []
    
    # Helper function to get files from a folder
    def get_files_from_folder(folder_id, doc_type):
        if not folder_id:
            return []
            
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.document'",
                spaces='drive',
                fields="nextPageToken, files(id, name)",
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                st.warning(f'No files found in {doc_type} folder.')
                return []
                
            st.success(f"Found {len(files)} {doc_type} files.")
            return [(file, doc_type) for file in files]
        except Exception as e:
            st.error(f"Error accessing {doc_type} folder: {e}")
            return []
    
    # Get files from all folders
    all_files = []
    if simulation_folder_id:
        all_files.extend(get_files_from_folder(simulation_folder_id, "simulation"))
    if technical_folder_id:
        all_files.extend(get_files_from_folder(technical_folder_id, "technical"))
    if general_folder_id:
        all_files.extend(get_files_from_folder(general_folder_id, "general"))
    
    # Download files in parallel
    st.text(f"Downloading {len(all_files)} files...")
    progress_bar = st.progress(0)
    
    # Prepare arguments for parallel download
    args_list = [(service, file, doc_type) for file, doc_type in all_files]
    
    # Use ThreadPoolExecutor for parallel downloads
    max_workers = min(10, len(all_files))  # Don't use more than 10 workers
    counter = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_file, args) for args in args_list]
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                file_id, file_name, content, doc_type = result
                
                # Create a Document object
                metadata = {
                    "title": file_name,
                    "type": doc_type,
                    "file_id": file_id,
                    "complete": doc_type == "simulation"  # Mark simulation docs as complete
                }
                
                doc = Document(
                    text=content,
                    metadata=metadata
                )
                
                all_documents.append(doc)
            
            # Update progress bar
            counter += 1
            progress_bar.progress(counter / len(all_files))
    
    st.success(f"Successfully loaded {len(all_documents)} documents.")
    return all_documents

# Index creation functions
def create_indexes(documents):
    """Create indexes for the documents"""
    # Split documents by type
    simulation_docs = [doc for doc in documents if doc.metadata.get("type") == "simulation"]
    technical_docs = [doc for doc in documents if doc.metadata.get("type") == "technical"]
    general_docs = [doc for doc in documents if doc.metadata.get("type") == "general"]
    
    st.text(f"Processing {len(simulation_docs)} simulation docs, {len(technical_docs)} technical docs, and {len(general_docs)} general docs")
    
    # Get the vector store
    index, vector_store = init_vector_store()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Process simulation documents (minimal chunking)
    if simulation_docs:
        st.text("Indexing simulation documents...")
        simulation_parser = SentenceSplitter(chunk_size=3000, chunk_overlap=100)
        VectorStoreIndex.from_documents(
            simulation_docs,
            storage_context=storage_context,
            transformations=[simulation_parser],
            service_context=init_llama_index()
        )
    
    # Process technical and general documents (standard chunking)
    other_docs = technical_docs + general_docs
    if other_docs:
        st.text("Indexing technical and general documents...")
        standard_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        VectorStoreIndex.from_documents(
            other_docs,
            storage_context=storage_context,
            transformations=[standard_parser],
            service_context=init_llama_index()
        )
    
    st.success("Indexing complete!")
    return index

# Main functionality
def main():
    # Initialize services
    try:
        index, vector_store = init_vector_store()
        anthropic_client = init_anthropic()
    except Exception as e:
        st.error(f"Error initializing services: {e}")
        st.stop()
    
    # Data loading UI in sidebar
    with st.sidebar:
        st.header("Data Loading")
        
        # Only show data loading if not already loaded
        if not st.session_state.initialized:
            # Folder IDs
            simulation_folder_id = st.text_input("Simulation Folder ID (High-quality calls)", 
                                                help="Google Drive folder ID containing your high-quality call transcripts")
            technical_folder_id = st.text_input("Technical Folder ID (Product specs, etc.)", 
                                               help="Google Drive folder ID for technical documents")
            general_folder_id = st.text_input("General Folder ID (Other calls)", 
                                             help="Google Drive folder ID for other call transcripts")
            
            # Load button
            if st.button("Load and Index Documents"):
                if not any([simulation_folder_id, technical_folder_id, general_folder_id]):
                    st.error("Please enter at least one folder ID")
                else:
                    with st.spinner("Loading documents from Google Drive..."):
                        try:
                            documents = load_documents_from_drive(
                                simulation_folder_id=simulation_folder_id or None,
                                technical_folder_id=technical_folder_id or None,
                                general_folder_id=general_folder_id or None
                            )
                            
                            if documents:
                                with st.spinner("Creating indexes..."):
                                    create_indexes(documents)
                                st.session_state.initialized = True
                                st.success("Documents loaded and indexed successfully!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error loading documents: {e}")
        else:
            st.success("Documents loaded and indexed!")
            if st.button("Reset and Load New Documents"):
                st.session_state.initialized = False
                st.rerun()
    
    # Chat interface
    st.header("Chat Interface")
    
    if not st.session_state.initialized:
        st.info("Please load documents using the sidebar before chatting")
    else:
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Input field for new message
        if prompt := st.chat_input("Type your message here..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.write(prompt)
            
            # Get response based on current mode
            with st.spinner("Thinking..."):
                try:
                    # Create retriever with appropriate filter
                    if st.session_state.mode == "simulation":
                        retriever = index.as_retriever(
                            similarity_top_k=3,
                            filters={"type": "simulation"}
                        )
                    else:
                        # Use hybrid retrieval for assistant mode
                        retriever = index.as_retriever(
                            similarity_top_k=5
                        )
                    
                    # Get context from retriever
                    retrieved_nodes = retriever.retrieve(prompt)
                    context = ""
                    
                    for node in retrieved_nodes:
                        doc_type = node.metadata.get("type", "unknown")
                        title = node.metadata.get("title", "Untitled")
                        context += f"\n\n--- From {doc_type.upper()} document: {title} ---\n{node.text}"
                    
                    # Build prompt based on mode
                    if st.session_state.mode == "simulation":
                        system_prompt = (
                            "You are simulating a solar panel salesperson based on real sales call transcripts. "
                            "Maintain the tone, style, objection handling techniques, and approach used in these transcripts. "
                            "Answer as if you are the salesperson in a live call. Use the same language patterns, "
                            "terminology, and conversational approach seen in the transcripts."
                        )
                    else:
                        system_prompt = (
                            "You are a helpful assistant that provides factual information about solar panels, "
                            "sales processes, and technical specifications. Provide clear, accurate information "
                            "based on the documents available to you."
                        )
                    
                    # Get response from Claude
                    response = anthropic_client.messages.create(
                        model="claude-3-7-sonnet-20250219",
                        max_tokens=1000,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": f"Context from documents:\n{context}\n\nUser question: {prompt}"}
                        ]
                    )
                    
                    # Display assistant response
                    with st.chat_message("assistant"):
                        st.write(response.content[0].text)
                    
                    # Add to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response.content[0].text})
                    
                except Exception as e:
                    st.error(f"Error: {e}")

if __name__ == "__main__":
    main()