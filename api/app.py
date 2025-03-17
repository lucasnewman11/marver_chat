#!/usr/bin/env python3
"""
Python backend API for the Chatbot application.
Handles transcript processing and Pinecone vector database operations.
"""

import os
import json
import time
import random
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import numpy as np

# Load environment variables
load_dotenv()

# Configuration
PINECONE_API_KEY = os.getenv("REACT_APP_PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("REACT_APP_PINECONE_INDEX_NAME", "sales-simulator")
PINECONE_ENVIRONMENT = os.getenv("REACT_APP_PINECONE_ENVIRONMENT", "us-east-1-aws")
VOYAGE_API_KEY = os.getenv("REACT_APP_VOYAGE_API_KEY")
API_VERSION = "2025-01"
TRANSCRIPTS_DIR = Path("../all_transcripts")
PROGRESS_FILE = Path("./.indexing_progress.json")

# Initialize FastAPI
app = FastAPI(title="Chatbot API", description="API for processing transcripts and interacting with Pinecone")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for request/response
class Document(BaseModel):
    id: str
    name: str
    content: str
    type: str

class ProcessRequest(BaseModel):
    documents: List[Document]
    pineconeApiKey: Optional[str] = None
    pineconeEnvironment: Optional[str] = None
    pineconeIndexName: Optional[str] = None
    voyageApiKey: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    mode: Optional[str] = None
    pineconeApiKey: Optional[str] = None
    pineconeEnvironment: Optional[str] = None
    pineconeIndexName: Optional[str] = None
    voyageApiKey: Optional[str] = None
    topK: Optional[int] = 5

# Helper functions
def get_headers() -> dict:
    """Generate headers for Pinecone API requests."""
    return {
        "Api-Key": PINECONE_API_KEY,
        "Content-Type": "application/json",
        "X-Pinecone-API-Version": API_VERSION
    }

async def init_pinecone(api_key: str = None, environment: str = None, index_name: str = None) -> dict:
    """Initialize Pinecone and get index details."""
    api_key = api_key or PINECONE_API_KEY
    environment = environment or PINECONE_ENVIRONMENT
    index_name = index_name or PINECONE_INDEX_NAME
    
    if not api_key:
        raise HTTPException(status_code=400, detail="Pinecone API key is required")
    
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json",
        "X-Pinecone-API-Version": API_VERSION
    }
    
    # Check if index exists
    async with httpx.AsyncClient() as client:
        # List indexes
        list_response = await client.get(
            "https://api.pinecone.io/indexes",
            headers=headers
        )
        
        if list_response.status_code != 200:
            raise HTTPException(
                status_code=list_response.status_code,
                detail=f"Error connecting to Pinecone: {list_response.text}"
            )
        
        indexes = list_response.json().get("indexes", [])
        index_exists = any(index.get("name") == index_name for index in indexes)
        
        if not index_exists:
            # Create index
            print(f"Creating new Pinecone index: {index_name}")
            create_response = await client.post(
                "https://api.pinecone.io/indexes",
                headers=headers,
                json={
                    "name": index_name,
                    "dimension": 1024,
                    "metric": "cosine",
                    "spec": {
                        "serverless": {
                            "cloud": "aws",
                            "region": "us-east-1"
                        }
                    }
                }
            )
            
            if create_response.status_code != 201:
                raise HTTPException(
                    status_code=create_response.status_code,
                    detail=f"Error creating Pinecone index: {create_response.text}"
                )
            
            # Wait for index to initialize
            print("Waiting for index to initialize...")
            await asyncio.sleep(60)  # Wait 60 seconds - adjust as needed
        
        # Get index details
        describe_response = await client.get(
            f"https://api.pinecone.io/indexes/{index_name}",
            headers=headers
        )
        
        if describe_response.status_code != 200:
            raise HTTPException(
                status_code=describe_response.status_code,
                detail=f"Error getting Pinecone index details: {describe_response.text}"
            )
        
        index_data = describe_response.json()
        host = index_data.get("host")
        dimension = index_data.get("dimension")
        
        print(f"Connected to Pinecone index: {index_name}")
        print(f"Host: {host}, Dimension: {dimension}")
        
        return {
            "host": host,
            "dimension": dimension
        }

async def get_indexed_file_ids(host: str, headers: dict) -> List[str]:
    """Get list of already indexed file IDs from Pinecone."""
    try:
        async with httpx.AsyncClient() as client:
            # Get index stats
            stats_response = await client.get(
                f"https://{host}/describe_index_stats",
                headers=headers
            )
            
            if stats_response.status_code != 200:
                print(f"Error getting index stats: {stats_response.text}")
                return []
            
            total_vectors = stats_response.json().get("totalVectorCount", 0)
            
            if total_vectors == 0:
                print("No vectors in the index yet")
                return []
            
            # Try to sample some vectors to extract file IDs
            # This is a simplified approach - in production you might want to implement pagination
            query_response = await client.post(
                f"https://{host}/query",
                headers=headers,
                json={
                    "vector": [0] * 1024,  # Dummy vector for querying
                    "topK": min(total_vectors, 100),
                    "includeMetadata": True
                }
            )
            
            if query_response.status_code != 200:
                print(f"Error querying vectors: {query_response.text}")
                return []
            
            matches = query_response.json().get("matches", [])
            file_ids = set()
            
            for match in matches:
                metadata = match.get("metadata", {})
                if metadata and "fileId" in metadata:
                    file_ids.add(metadata["fileId"])
            
            print(f"Found {len(file_ids)} already indexed file IDs")
            return list(file_ids)
    
    except Exception as e:
        print(f"Error getting indexed file IDs: {str(e)}")
        return []

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 100) -> List[str]:
    """Split text into chunks with overlap."""
    # Clean text
    cleaned_text = " ".join(text.split())
    
    chunks = []
    start = 0
    
    while start < len(cleaned_text):
        end = min(start + chunk_size, len(cleaned_text))
        
        # Try to end at sentence boundary
        if end < len(cleaned_text):
            next_period = cleaned_text.find(".", end - 20)
            if next_period > 0 and next_period < end + 20:
                end = next_period + 1
        
        chunks.append(cleaned_text[start:end])
        start = end - overlap
    
    return chunks

async def generate_embedding(text: str, api_key: str, retries: int = 3) -> List[float]:
    """Generate embedding using VoyageAI API."""
    if not api_key:
        # Use deterministic embedding for testing
        return generate_deterministic_embedding(text)
    
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    },
                    json={
                        "model": "voyage-2",
                        "input": text
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()["data"][0]["embedding"]
                
                print(f"Error generating embedding (attempt {attempt+1}/{retries}): {response.text}")
                
                if attempt < retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        except Exception as e:
            print(f"Exception generating embedding (attempt {attempt+1}/{retries}): {str(e)}")
            
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
    
    # Fallback to deterministic embedding
    print("Using fallback deterministic embedding")
    return generate_deterministic_embedding(text)

def generate_deterministic_embedding(text: str, dimension: int = 1024) -> List[float]:
    """Generate a deterministic embedding based on text hash."""
    # Create MD5 hash of the text
    md5 = hashlib.md5(text.encode()).hexdigest()
    
    # Use hash to seed random number generator for reproducibility
    seed = int(md5, 16) % (2**32)
    rng = random.Random(seed)
    
    # Generate deterministic vector
    return [rng.uniform(-1, 1) for _ in range(dimension)]

# API Endpoints
@app.get("/api")
async def api_info():
    """API status endpoint."""
    return {"message": "API server running"}

@app.post("/api/indexing/process")
async def process_documents(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Process and index documents in Pinecone."""
    try:
        documents = request.documents
        
        if not documents:
            raise HTTPException(status_code=400, detail="Documents are required")
        
        # Get API keys from request or environment
        pinecone_api_key = request.pineconeApiKey or PINECONE_API_KEY
        pinecone_environment = request.pineconeEnvironment or PINECONE_ENVIRONMENT
        pinecone_index_name = request.pineconeIndexName or PINECONE_INDEX_NAME
        voyage_api_key = request.voyageApiKey or VOYAGE_API_KEY
        
        if not pinecone_api_key:
            raise HTTPException(status_code=400, detail="Pinecone API key is required")
        
        # Initialize Pinecone
        pinecone_info = await init_pinecone(
            pinecone_api_key,
            pinecone_environment,
            pinecone_index_name
        )
        
        host = pinecone_info["host"]
        
        # Prepare headers
        headers = {
            "Api-Key": pinecone_api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": API_VERSION
        }
        
        # Get already indexed file IDs
        indexed_file_ids = await get_indexed_file_ids(host, headers)
        
        # Filter out already indexed documents
        new_documents = [doc for doc in documents if doc.id not in indexed_file_ids]
        
        if not new_documents:
            return {
                "message": "All documents are already indexed",
                "documentCounts": {
                    "simulation": 0,
                    "technical": 0,
                    "general": 0
                },
                "chunkCount": 0
            }
        
        # Group documents by type
        simulation_docs = [doc for doc in new_documents if doc.type == "simulation"]
        technical_docs = [doc for doc in new_documents if doc.type == "technical"]
        general_docs = [doc for doc in new_documents if doc.type == "general"]
        
        # Start background processing task
        background_tasks.add_task(
            process_documents_background,
            simulation_docs,
            technical_docs,
            general_docs,
            host,
            headers,
            voyage_api_key
        )
        
        return {
            "message": f"Processing started for {len(new_documents)} new documents",
            "documentCounts": {
                "simulation": len(simulation_docs),
                "technical": len(technical_docs),
                "general": len(general_docs)
            },
            "chunkCount": "Calculating..."
        }
    
    except Exception as e:
        print(f"Error processing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_documents_background(
    simulation_docs: List[Document],
    technical_docs: List[Document],
    general_docs: List[Document],
    host: str,
    headers: dict,
    voyage_api_key: str
):
    """Process documents in background task."""
    try:
        total_chunks = 0
        
        # Process simulation docs
        print(f"Processing {len(simulation_docs)} simulation documents")
        for doc in simulation_docs:
            chunks = chunk_text(doc.content, 3000, 100)
            print(f"Created {len(chunks)} chunks for simulation doc {doc.id}")
            
            # Process chunks in batches
            for i in range(0, len(chunks), 10):
                batch = chunks[i:i+10]
                vectors = []
                
                # Generate embeddings and create vectors
                for j, chunk in enumerate(batch):
                    embedding = await generate_embedding(chunk, voyage_api_key)
                    
                    vectors.append({
                        "id": f"{doc.id}-chunk-{i+j}",
                        "values": embedding,
                        "metadata": {
                            "text": chunk[:1000],  # Limit metadata size
                            "fileId": doc.id,
                            "title": doc.name,
                            "type": "simulation"
                        }
                    })
                
                # Upsert vectors to Pinecone
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"https://{host}/vectors/upsert",
                        headers=headers,
                        json={"vectors": vectors, "namespace": ""}
                    )
                    
                    if response.status_code != 200:
                        print(f"Error upserting vectors: {response.text}")
                    else:
                        print(f"Upserted batch {i//10 + 1}/{(len(chunks) + 9)//10} for doc {doc.id}")
                
                total_chunks += len(batch)
        
        # Process technical and general docs
        all_other_docs = technical_docs + general_docs
        print(f"Processing {len(all_other_docs)} technical/general documents")
        
        for doc in all_other_docs:
            chunks = chunk_text(doc.content, 512, 50)
            print(f"Created {len(chunks)} chunks for {doc.type} doc {doc.id}")
            
            # Process chunks in batches
            for i in range(0, len(chunks), 10):
                batch = chunks[i:i+10]
                vectors = []
                
                # Generate embeddings and create vectors
                for j, chunk in enumerate(batch):
                    embedding = await generate_embedding(chunk, voyage_api_key)
                    
                    vectors.append({
                        "id": f"{doc.id}-chunk-{i+j}",
                        "values": embedding,
                        "metadata": {
                            "text": chunk[:1000],  # Limit metadata size
                            "fileId": doc.id,
                            "title": doc.name,
                            "type": doc.type
                        }
                    })
                
                # Upsert vectors to Pinecone
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"https://{host}/vectors/upsert",
                        headers=headers,
                        json={"vectors": vectors, "namespace": ""}
                    )
                    
                    if response.status_code != 200:
                        print(f"Error upserting vectors: {response.text}")
                    else:
                        print(f"Upserted batch {i//10 + 1}/{(len(chunks) + 9)//10} for doc {doc.id}")
                
                total_chunks += len(batch)
        
        print(f"Completed processing {len(simulation_docs) + len(all_other_docs)} documents")
        print(f"Total chunks: {total_chunks}")
    
    except Exception as e:
        print(f"Error in background processing: {str(e)}")

@app.post("/api/indexing/query")
async def query_vectors(request: QueryRequest):
    """Query Pinecone for similar vectors."""
    try:
        # Get API keys from request or environment
        pinecone_api_key = request.pineconeApiKey or PINECONE_API_KEY
        pinecone_environment = request.pineconeEnvironment or PINECONE_ENVIRONMENT
        pinecone_index_name = request.pineconeIndexName or PINECONE_INDEX_NAME
        voyage_api_key = request.voyageApiKey or VOYAGE_API_KEY
        
        if not pinecone_api_key:
            raise HTTPException(status_code=400, detail="Pinecone API key is required")
        
        if not request.query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Initialize Pinecone
        pinecone_info = await init_pinecone(
            pinecone_api_key,
            pinecone_environment,
            pinecone_index_name
        )
        
        host = pinecone_info["host"]
        
        # Prepare headers
        headers = {
            "Api-Key": pinecone_api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": API_VERSION
        }
        
        # Generate query embedding
        print(f"Generating embedding for query: {request.query}")
        query_embedding = await generate_embedding(request.query, voyage_api_key)
        
        # Query Pinecone
        print("Querying Pinecone")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{host}/query",
                headers=headers,
                json={
                    "vector": query_embedding,
                    "topK": request.topK,
                    "includeMetadata": True
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error querying Pinecone: {response.text}"
                )
            
            results = response.json()
            matches = results.get("matches", [])
            
            print(f"Found {len(matches)} matches")
            
            # Format results
            context_items = []
            for match in matches:
                metadata = match.get("metadata", {})
                context_items.append({
                    "score": match.get("score"),
                    "content": metadata.get("text", "No text available"),
                    "metadata": {
                        "fileId": metadata.get("fileId"),
                        "title": metadata.get("title", "Unknown")
                    }
                })
            
            # Combine contexts
            combined_context = "\n\n".join([
                f"[{item['metadata']['title']}]: {item['content']}"
                for item in context_items
            ])
            
            return {
                "context": combined_context,
                "rawMatches": context_items
            }
    
    except Exception as e:
        print(f"Error querying vector store: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Import this at the end to avoid circular imports
import asyncio

# Run the app with Uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)