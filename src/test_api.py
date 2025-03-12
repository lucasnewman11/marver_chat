from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

app = FastAPI()
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        # Simple message to test the connection
        message = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": request.message}
            ]
        )
        return {"response": message.content[0].text}
    except Exception as e:
        return {"error": str(e)}

# Test client for the API
client = TestClient(app)

def test_api():
    """Test if the API endpoint works"""
    response = client.post(
        "/chat",
        json={"message": "Hello Claude, this is a test. Please respond with a short greeting."}
    )
    assert response.status_code == 200
    print(f"API response: {response.json()}")

if __name__ == "__main__":
    print("Testing API endpoint...")
    test_api()