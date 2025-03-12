import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def test_anthropic_connection():
    """Test if we can connect to the Anthropic API"""
    try:
        # Simple message to test the connection
        message = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": "Hello Claude, this is a test. Please respond with a short greeting."}
            ]
        )
        return f"✅ Connection successful! Claude says: {message.content[0].text}"
    except Exception as e:
        return f"❌ Connection failed: {str(e)}"

if __name__ == "__main__":
    print("Testing Anthropic connection...")
    result = test_anthropic_connection()
    print(result)