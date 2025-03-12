import os
from dotenv import load_dotenv
from anthropic import Anthropic
from llama_index.core import Settings, VectorStoreIndex, Document
from llama_index.llms.anthropic import Anthropic as LlamaIndexAnthropic
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Load environment variables
load_dotenv()

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
llm = LlamaIndexAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), model="claude-3-sonnet-20240229")

# Set LlamaIndex settings
Settings.llm = llm
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.chunk_size = 512

class LocalDocumentChatbot:
    def __init__(self):
        self.index = None
        
    def load_documents(self, text_content=None):
        """Load documents from text content and create an index"""
        if not text_content:
            text_content = """
            The Google Drive Chatbot is a tool that allows users to interact with their Google Drive documents using Claude AI.
            It can search through documents, answer questions, and provide summaries of the content found in Google Drive.
            The chatbot uses LlamaIndex for document indexing and Anthropic's Claude for natural language understanding.
            
            Key features:
            1. Connect to Google Drive using service account authentication
            2. Index documents for fast retrieval
            3. Process natural language queries
            4. Provide context-aware responses based on document content
            """
            
        documents = [Document(text=text_content)]
        self.index = VectorStoreIndex.from_documents(documents)
        return f"Loaded {len(documents)} documents with {len(text_content)} characters"
    
    def chat(self, message: str) -> str:
        """Process a user message and return a response based on documents"""
        if not self.index:
            return "Please load documents first using load_documents()"
            
        query_engine = self.index.as_query_engine()
        response = query_engine.query(message)
        return str(response)

def test_rag():
    """Test RAG functionality with a local document"""
    chatbot = LocalDocumentChatbot()
    print("Loading test document...")
    result = chatbot.load_documents()
    print(result)
    
    print("\nTesting chatbot with query...")
    response = chatbot.chat("What are the key features of the chatbot?")
    print(f"Chatbot response: {response}")

if __name__ == "__main__":
    print("Testing RAG functionality...")
    test_rag()