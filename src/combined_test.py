import os
import tempfile
from dotenv import load_dotenv
from anthropic import Anthropic
import json

# Load environment variables
load_dotenv()

# Initialize Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = Anthropic(api_key=anthropic_api_key)

def test_anthropic_connection():
    """Test if we can connect to the Anthropic API"""
    try:
        print("Testing Anthropic API connection...")
        
        # Simple message to test the connection
        message = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello Claude, this is a test. Please respond with a short greeting."}
            ]
        )
        
        print(f"✅ Anthropic API connection successful! Claude says: {message.content[0].text}\n")
        return True
    except Exception as e:
        print(f"❌ Anthropic API connection failed: {str(e)}\n")
        return False

def test_google_service_account():
    """Test if the Google Service Account JSON is properly configured"""
    try:
        print("Testing Google Service Account configuration...")
        
        google_service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        
        if not google_service_account_json:
            print("❌ Google Service Account JSON not found in environment\n")
            return False
            
        # Try to parse the JSON
        service_account_info = json.loads(google_service_account_json)
        
        # Check for required fields
        required_fields = [
            "type", "project_id", "private_key_id", "private_key", 
            "client_email", "client_id", "auth_uri", "token_uri"
        ]
        
        for field in required_fields:
            if field not in service_account_info:
                print(f"❌ Google Service Account JSON missing required field: {field}\n")
                return False
                
        print(f"✅ Google Service Account JSON properly formatted\n")
        
        # Note: We can't actually test the Google Drive connection without 
        # having access to specific folders/files, but we can check the configuration
        
        return True
    except json.JSONDecodeError:
        print("❌ Google Service Account JSON is not valid JSON\n")
        return False
    except Exception as e:
        print(f"❌ Google Service Account check failed: {str(e)}\n")
        return False

def test_simple_chatbot():
    """Test a simple chatbot functionality with local content"""
    print("Testing simple chatbot functionality...")
    
    # Sample content
    content = """
    The Google Drive Chatbot is a tool that allows users to interact with their Google Drive documents using Claude AI.
    It can search through documents, answer questions, and provide summaries of the content found in Google Drive.
    The chatbot uses LlamaIndex for document indexing and Anthropic's Claude for natural language understanding.
    
    Key features:
    1. Connect to Google Drive using service account authentication
    2. Index documents for fast retrieval
    3. Process natural language queries
    4. Provide context-aware responses based on document content
    """
    
    try:
        # Create prompt with the content and the question
        prompt = f"""
        Please answer the following question based only on the information provided in the content below.
        
        CONTENT:
        {content}
        
        QUESTION: What are the key features of the chatbot?
        """
        
        # Use Claude to generate a response
        response = anthropic_client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        print(f"✅ Simple chatbot test successful! Response: {response.content[0].text}\n")
        return True
    except Exception as e:
        print(f"❌ Simple chatbot test failed: {str(e)}\n")
        return False

def run_all_tests():
    """Run all the tests and print a summary"""
    print("🔍 RUNNING ALL TESTS 🔍\n")
    
    test_results = {
        "Anthropic API Connection": test_anthropic_connection(),
        "Google Service Account Configuration": test_google_service_account(),
        "Simple Chatbot Functionality": test_simple_chatbot()
    }
    
    print("\n📋 TEST SUMMARY 📋")
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n🏁 OVERALL RESULT 🏁")
    if all_passed:
        print("✅ All tests passed! The chatbot is ready to use.")
    else:
        print("❌ Some tests failed. Please fix the issues before proceeding.")

if __name__ == "__main__":
    run_all_tests()