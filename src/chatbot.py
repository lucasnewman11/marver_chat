import os
from dotenv import load_dotenv
from anthropic import Anthropic
from llama_index.readers.google import GoogleDriveReader
from llama_index.core import Settings, VectorStoreIndex, Document
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.llms.anthropic import Anthropic as LlamaIndexAnthropic
from typing import List

# Load environment variables
load_dotenv()

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
llm = LlamaIndexAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), model="claude-3-7-sonnet-20250219")

# Initialize Voyage AI for embeddings
from llama_index.embeddings.voyageai import VoyageEmbedding
voyage_api_key = os.getenv("VOYAGE_API_KEY", "pa-Hj2UDd0uOnPfrSlYLyfka-XlM859rV4MWwx8B-5YAOM")
embed_model = VoyageEmbedding(
    voyage_api_key=voyage_api_key,
    model_name="voyage-3",
    input_type="search_query"
)

# Set LlamaIndex settings
Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 512

class GoogleDriveChatbot:
    def __init__(self):
        # Initialize Google Drive reader
        google_service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        
        # Check if it's a JSON string or a file path
        if google_service_account_json and google_service_account_json.strip().startswith("{"):
            # It's a JSON string
            import json
            service_account_key = json.loads(google_service_account_json)
            self.drive_reader = GoogleDriveReader(
                service_account_key=service_account_key
            )
        else:
            # Assume it's a file path
            self.drive_reader = GoogleDriveReader(
                service_account_json=google_service_account_json
            )
        self.index = None
        
    def load_documents(self, folder_id: str = None, file_ids: List[str] = None):
        """Load documents from Google Drive and create an index"""
        documents = []
        
        if folder_id:
            print(f"Loading documents from folder {folder_id}")
            documents.extend(self.drive_reader.load_data(folder_id=folder_id))
        
        if file_ids:
            print(f"Loading documents from files {file_ids}")
            for file_id in file_ids:
                documents.extend(self.drive_reader.load_data(file_ids=[file_id]))
        
        if not documents:
            raise ValueError("No documents loaded. Provide either folder_id or file_ids.")
            
        self.index = VectorStoreIndex.from_documents(documents)
        return f"Loaded {len(documents)} documents"
    
    def chat(self, message: str) -> str:
        """Process a user message and return a response based on documents"""
        if not self.index:
            return "Please load documents first using load_documents()"
            
        query_engine = self.index.as_query_engine()
        response = query_engine.query(message)
        return str(response)

# Example usage
if __name__ == "__main__":
    # Load your environment variables first!
    chatbot = GoogleDriveChatbot()
    
    # Replace with your Google Drive folder or file IDs
    # chatbot.load_documents(folder_id="your_folder_id")
    # chatbot.load_documents(file_ids=["your_file_id"])
    
    # Example chat
    # response = chatbot.chat("What information is in my documents?")
    # print(response)