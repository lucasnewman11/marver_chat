import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class SimpleContentChatbot:
    def __init__(self):
        self.content = None
        
    def load_content(self, text_content=None):
        """Store text content for later retrieval"""
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
        
        self.content = text_content
        return f"Loaded content with {len(text_content)} characters"
    
    def chat(self, message: str) -> str:
        """Process a user message and return a response based on content"""
        if not self.content:
            return "Please load content first using load_content()"
            
        # Create prompt with the content and the question
        prompt = f"""
        Please answer the following question based only on the information provided in the content below.
        
        CONTENT:
        {self.content}
        
        QUESTION: {message}
        """
        
        # Use Claude to generate a response
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text

def test_simple_chat():
    """Test a simple chatbot with Claude directly (no RAG)"""
    chatbot = SimpleContentChatbot()
    print("Loading test content...")
    result = chatbot.load_content()
    print(result)
    
    print("\nTesting chatbot with query...")
    response = chatbot.chat("What are the key features of the chatbot?")
    print(f"Chatbot response: {response}")

if __name__ == "__main__":
    print("Testing simple content-based chatbot...")
    test_simple_chat()