from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.chatbot import GoogleDriveChatbot

app = FastAPI()
chatbot = GoogleDriveChatbot()

class LoadDocsRequest(BaseModel):
    folder_id: Optional[str] = None
    file_ids: Optional[List[str]] = None

class ChatRequest(BaseModel):
    message: str

@app.post("/load-documents")
def load_documents(request: LoadDocsRequest):
    try:
        if not request.folder_id and not request.file_ids:
            raise HTTPException(status_code=400, detail="Please provide either folder_id or file_ids")
        
        result = chatbot.load_documents(folder_id=request.folder_id, file_ids=request.file_ids)
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        response = chatbot.chat(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)