import os
from dotenv import load_dotenv
from src.chatbot import GoogleDriveChatbot

# Load environment variables
load_dotenv()

def get_all_file_ids():
    """Get all file IDs from the previous scan"""
    file_ids = [
        # Just a few sales call transcripts to stay within rate limits
        "1EmF_3pnHuR2zMZ8IeDDLMdNM8KozU1zIxNzE-R2fd20",
        "175_pqhVhzaRee5afrMx6dQXaTHw_ckqfzULoOPNat5k"
    ]
    return file_ids

def setup_and_test_chatbot():
    """Set up the chatbot with all available files and test it"""
    print("Setting up chatbot with all available files...")
    
    # Initialize the chatbot
    chatbot = GoogleDriveChatbot()
    
    # Get all file IDs
    file_ids = get_all_file_ids()
    
    # Load documents from Google Drive
    print(f"Loading documents from {len(file_ids)} files...")
    result = chatbot.load_documents(file_ids=file_ids)
    print(result)
    
    # Test the chatbot with a query
    print("\nTesting chatbot with a query...")
    test_query = "What are the common topics in these sales call transcripts?"
    response = chatbot.chat(test_query)
    print(f"Query: {test_query}")
    print(f"Response:\n{response}")

if __name__ == "__main__":
    setup_and_test_chatbot()