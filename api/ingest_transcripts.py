#!/usr/bin/env python3
"""
Script to directly ingest transcript files from the local directory into Pinecone.
This is a standalone script that doesn't require the API server to be running.
"""

import os
import json
import time
import asyncio
import random
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

import httpx

# Load environment variables
load_dotenv()

# Configuration
PINECONE_API_KEY = os.getenv("REACT_APP_PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("REACT_APP_PINECONE_INDEX_NAME", "sales-simulator")
PINECONE_ENVIRONMENT = os.getenv("REACT_APP_PINECONE_ENVIRONMENT", "us-east-1-aws")
VOYAGE_API_KEY = os.getenv("REACT_APP_VOYAGE_API_KEY")
API_VERSION = "2025-01"
TRANSCRIPTS_DIR = Path("../all_transcripts")
BATCH_SIZE = 10  # Number of chunks to process at once

# Helper functions
def get_headers() -> dict:
    """Generate headers for Pinecone API requests."""
    return {
        "Api-Key": PINECONE_API_KEY,
        "Content-Type": "application/json",
        "X-Pinecone-API-Version": API_VERSION
    }

async def init_pinecone() -> dict:
    """Initialize Pinecone and get index details."""
    print(f"Connecting to Pinecone index {PINECONE_INDEX_NAME}...")
    
    if not PINECONE_API_KEY:
        raise ValueError("Pinecone API key is required")
    
    headers = get_headers()
    
    # Check if index exists
    async with httpx.AsyncClient() as client:
        # List indexes
        list_response = await client.get(
            "https://api.pinecone.io/indexes",
            headers=headers
        )
        
        if list_response.status_code != 200:
            raise Exception(f"Error connecting to Pinecone: {list_response.text}")
        
        indexes = list_response.json().get("indexes", [])
        index_exists = any(index.get("name") == PINECONE_INDEX_NAME for index in indexes)
        
        if not index_exists:
            # Create index
            print(f"Creating new Pinecone index: {PINECONE_INDEX_NAME}")
            create_response = await client.post(
                "https://api.pinecone.io/indexes",
                headers=headers,
                json={
                    "name": PINECONE_INDEX_NAME,
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
                raise Exception(f"Error creating Pinecone index: {create_response.text}")
            
            # Wait for index to initialize
            print("Waiting for index to initialize...")
            await asyncio.sleep(60)  # Wait 60 seconds
        
        # Get index details
        describe_response = await client.get(
            f"https://api.pinecone.io/indexes/{PINECONE_INDEX_NAME}",
            headers=headers
        )
        
        if describe_response.status_code != 200:
            raise Exception(f"Error getting Pinecone index details: {describe_response.text}")
        
        index_data = describe_response.json()
        host = index_data.get("host")
        dimension = index_data.get("dimension")
        
        print(f"Connected to Pinecone index: {PINECONE_INDEX_NAME}")
        print(f"Host: {host}, Dimension: {dimension}")
        
        return {
            "host": host,
            "dimension": dimension
        }

async def get_indexed_file_ids(host: str) -> List[str]:
    """Get list of already indexed file IDs from Pinecone."""
    try:
        headers = get_headers()
        
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
            
            # Get a sample of vectors to extract file IDs
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
            
            # Extract file IDs from metadata
            matches = query_response.json().get("matches", [])
            file_ids = set()
            
            for match in matches:
                metadata = match.get("metadata", {})
                if metadata and "fileId" in metadata:
                    file_ids.add(metadata["fileId"])
            
            result = list(file_ids)
            print(f"Found {len(result)} already indexed files in Pinecone")
            return result
    
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

async def generate_embedding(text: str, retries: int = 3) -> List[float]:
    """Generate embedding using VoyageAI API if available, otherwise use deterministic method."""
    if not VOYAGE_API_KEY:
        # Use deterministic embedding if no API key available
        return generate_deterministic_embedding(text)
    
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {VOYAGE_API_KEY}"
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

async def process_file(file_path: Path, file_id: str, file_name: str, host: str) -> int:
    """Process a single transcript file."""
    try:
        print(f"\nProcessing {file_name} ({file_id})...")
        
        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Chunk the text
        chunks = chunk_text(content)
        print(f"  Created {len(chunks)} chunks")
        
        # Process chunks in batches
        headers = get_headers()
        total_chunks = 0
        
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            vectors = []
            
            # Process each chunk
            for j, chunk in enumerate(batch):
                # Generate embedding
                embedding = await generate_embedding(chunk)
                
                vectors.append({
                    "id": f"{file_id}-chunk-{i+j}",
                    "values": embedding,
                    "metadata": {
                        "text": chunk[:1000],  # Limit metadata size
                        "fileId": file_id,
                        "title": file_name,
                        "type": "transcript"
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
                    print(f"  Error upserting vectors: {response.text}")
                else:
                    print(f"  Upserted batch {i//BATCH_SIZE + 1}/{(len(chunks) + BATCH_SIZE - 1)//BATCH_SIZE}")
            
            total_chunks += len(batch)
            
            # Sleep to avoid rate limiting
            await asyncio.sleep(0.5)
        
        print(f"  Completed processing file {file_name} ({total_chunks} chunks)")
        return total_chunks
    
    except Exception as e:
        print(f"Error processing file {file_name}: {str(e)}")
        return 0

async def main():
    """Main entry point for transcript ingestion."""
    try:
        start_time = time.time()
        
        # Initialize Pinecone
        pinecone_info = await init_pinecone()
        host = pinecone_info["host"]
        
        # Get already indexed file IDs
        indexed_file_ids = await get_indexed_file_ids(host)
        
        # Get list of transcript files
        if not TRANSCRIPTS_DIR.exists():
            raise ValueError(f"Transcripts directory {TRANSCRIPTS_DIR} does not exist")
        
        transcript_files = []
        for file_path in TRANSCRIPTS_DIR.glob("*.txt"):
            if file_path.name != "metadata.json":
                transcript_files.append(file_path)
        
        print(f"Found {len(transcript_files)} transcript files in {TRANSCRIPTS_DIR}")
        
        # Read metadata file if it exists
        metadata = {}
        metadata_file = TRANSCRIPTS_DIR / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        
        # Filter out already indexed files
        new_files = []
        for file_path in transcript_files:
            file_id = file_path.stem  # Filename without extension
            if file_id not in indexed_file_ids:
                new_files.append((file_path, file_id))
        
        print(f"Found {len(new_files)} new files to index")
        
        if not new_files:
            print("All files already indexed. Nothing to do.")
            return
        
        # Process each file
        total_chunks = 0
        processed_files = 0
        
        for file_path, file_id in new_files:
            # Get file name from metadata if available
            file_name = metadata.get(file_id, {}).get("name", file_path.name)
            
            # Process file
            chunks = await process_file(file_path, file_id, file_name, host)
            total_chunks += chunks
            processed_files += 1
            
            # Show progress
            print(f"Progress: {processed_files}/{len(new_files)} files ({processed_files/len(new_files)*100:.1f}%)")
        
        # Show summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\nIndexing complete!")
        print(f"Processed {processed_files} files into {total_chunks} chunks")
        print(f"Took {duration:.2f} seconds ({duration/60:.2f} minutes)")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())