#!/usr/bin/env python3
"""
Script for memory-efficient transcript ingestion into Pinecone.
"""

import os
import json
import time
import random
import hashlib
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=Path('./react-app/.env'))

# Configuration
PINECONE_API_KEY = os.getenv('REACT_APP_PINECONE_API_KEY')
PINECONE_INDEX_NAME = os.getenv('REACT_APP_PINECONE_INDEX_NAME', 'sales-simulator')
TRANSCRIPTS_DIR = Path('./all_transcripts')
API_VERSION = '2025-01'
GLOBAL_BATCH_SIZE = 2  # Process 2 files at a time
VECTOR_BATCH_SIZE = 10  # Send 10 vectors at a time to Pinecone

# Headers for Pinecone API
def get_headers():
    return {
        'Api-Key': PINECONE_API_KEY,
        'Content-Type': 'application/json',
        'X-Pinecone-API-Version': API_VERSION
    }

# Initialize Pinecone
def init_pinecone():
    print('Connecting to Pinecone...')
    
    # List indexes
    list_response = requests.get(
        'https://api.pinecone.io/indexes',
        headers=get_headers()
    )
    list_response.raise_for_status()
    indexes = list_response.json().get('indexes', [])
    
    index_exists = any(index['name'] == PINECONE_INDEX_NAME for index in indexes)
    if not index_exists:
        print(f"Error: Index '{PINECONE_INDEX_NAME}' does not exist. Please create it first.")
        exit(1)
    
    # Get index details
    describe_response = requests.get(
        f'https://api.pinecone.io/indexes/{PINECONE_INDEX_NAME}',
        headers=get_headers()
    )
    describe_response.raise_for_status()
    index_host = describe_response.json()['host']
    index_dimension = describe_response.json()['dimension']
    
    print(f"Connected to Pinecone index: {PINECONE_INDEX_NAME}")
    print(f"Host: {index_host}, Dimension: {index_dimension}")
    
    return index_host, index_dimension

# Get already indexed file IDs from Pinecone
def get_indexed_file_ids(host):
    print('Getting list of already indexed files...')
    
    # Get index stats first
    stats_response = requests.get(
        f'https://{host}/describe_index_stats',
        headers=get_headers()
    )
    stats_response.raise_for_status()
    total_vectors = stats_response.json().get('totalVectorCount', 0)
    
    if total_vectors == 0:
        print('No vectors in the index yet.')
        return []
    
    # Fetch vectors to get file IDs
    try:
        response = requests.post(
            f'https://{host}/vectors/fetch',
            json={'ids': [], 'namespace': ''},
            headers=get_headers()
        )
        response.raise_for_status()
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text[:100]}...")  # Print first 100 chars
        
        # Extract unique file IDs from metadata
        file_ids = set()
        response_json = response.json()
        print(f"Response JSON keys: {list(response_json.keys())}")
        vectors = response_json.get('vectors', {}).values()
        
        for vector in vectors:
            if vector.get('metadata') and vector['metadata'].get('fileId'):
                file_ids.add(vector['metadata']['fileId'])
    except Exception as e:
        print(f"Error fetching vectors: {str(e)}")
        print("Continuing with empty file ID list...")
    
    result = list(file_ids)
    print(f"Found {len(result)} already indexed files.")
    return result

# Simple chunking function
def chunk_text(text, chunk_size=2000, overlap=100):
    chunks = []
    
    # Clean text first
    cleaned_text = ' '.join(text.split())
    
    start = 0
    while start < len(cleaned_text):
        end = min(start + chunk_size, len(cleaned_text))
        
        # Try to end chunks at sentence boundaries when possible
        if end < len(cleaned_text):
            next_period = cleaned_text.find('.', end - 20)
            if next_period > 0 and next_period < end + 20:
                end = next_period + 1
        
        chunks.append(cleaned_text[start:end])
        start = end - overlap
    
    return chunks

# Generate a simple embedding with a deterministic approach
def generate_simple_embedding(text, dimension=1024):
    # Create a deterministic seed from the text
    seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16) % (2**32)
    random.seed(seed)
    
    # Generate vector with seeded random numbers
    return [random.uniform(-1, 1) for _ in range(dimension)]

# Process a single transcript file
def process_transcript(file_path, file_id, file_name, host):
    try:
        print(f"Processing {file_name}...")
        
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Chunk the text
        chunks = chunk_text(content)
        print(f"  Created {len(chunks)} chunks")
        
        # Process chunks in batches to manage memory
        total_upserted = 0
        for i in range(0, len(chunks), VECTOR_BATCH_SIZE):
            batch = chunks[i:i + VECTOR_BATCH_SIZE]
            
            # Create vectors from chunks
            vectors = []
            for idx, chunk in enumerate(batch):
                # Generate embedding
                embedding = generate_simple_embedding(chunk)
                
                vectors.append({
                    'id': f"{file_id}-chunk-{i + idx}",
                    'values': embedding,
                    'metadata': {
                        'text': chunk[:1000],  # Limit metadata text size
                        'fileId': file_id,
                        'title': file_name,
                        'type': 'transcript'
                    }
                })
            
            # Upsert vectors to Pinecone
            print(f"  Upserting batch {i//VECTOR_BATCH_SIZE + 1}/{(len(chunks) + VECTOR_BATCH_SIZE - 1)//VECTOR_BATCH_SIZE}...")
            
            response = requests.post(
                f'https://{host}/vectors/upsert',
                json={'vectors': vectors, 'namespace': ''},
                headers=get_headers()
            )
            response.raise_for_status()
            
            upserted = response.json().get('upsertedCount', 0)
            total_upserted += upserted
            print(f"  Upserted {upserted} vectors")
            
            # Clear memory
            vectors.clear()
            
            # Sleep a bit to avoid rate limiting
            time.sleep(0.5)
        
        return len(chunks)
    except Exception as e:
        print(f"Error processing transcript {file_name}: {str(e)}")
        return 0

# Main function
def main():
    try:
        # Start timer
        start_time = time.time()
        
        # Initialize Pinecone
        host, dimension = init_pinecone()
        
        # Get list of already indexed file IDs
        indexed_file_ids = get_indexed_file_ids(host)
        
        # Get list of transcript files
        transcript_files = []
        for file in os.listdir(TRANSCRIPTS_DIR):
            if file.endswith('.txt') and file != 'metadata.json':
                transcript_files.append(file)
        
        print(f"Found {len(transcript_files)} transcript files")
        
        # Read metadata file if it exists
        metadata = {}
        try:
            with open(TRANSCRIPTS_DIR / 'metadata.json', 'r') as f:
                metadata = json.load(f)
        except:
            print('No metadata file found, using filenames only.')
        
        # Filter out already indexed files
        new_files = []
        for file in transcript_files:
            file_id = file.replace('.txt', '')
            if file_id not in indexed_file_ids:
                new_files.append(file)
        
        print(f"Found {len(new_files)} new files to index")
        
        if not new_files:
            print('All files already indexed. Nothing to do.')
            return
        
        # Process files in batches to manage memory
        total_chunks = 0
        processed_files = 0
        
        for i in range(0, len(new_files), GLOBAL_BATCH_SIZE):
            batch = new_files[i:i + GLOBAL_BATCH_SIZE]
            print(f"Processing batch {i//GLOBAL_BATCH_SIZE + 1}/{(len(new_files) + GLOBAL_BATCH_SIZE - 1)//GLOBAL_BATCH_SIZE}...")
            
            # Process files sequentially to avoid memory issues
            batch_chunks = 0
            for file in batch:
                file_id = file.replace('.txt', '')
                file_name = metadata.get(file_id, {}).get('name', file)
                file_path = TRANSCRIPTS_DIR / file
                
                chunks = process_transcript(file_path, file_id, file_name, host)
                batch_chunks += chunks
                processed_files += 1
            
            total_chunks += batch_chunks
            
            print(f"Completed {processed_files}/{len(new_files)} files ({processed_files/len(new_files)*100:.1f}%)")
            
            # Sleep between batches to prevent memory buildup
            time.sleep(1)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print('\nIndexing complete!')
        print(f"Processed {processed_files} files into {total_chunks} chunks")
        print(f"Took {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()