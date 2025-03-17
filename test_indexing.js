// Test script for indexing documents and querying the vector database
require('dotenv').config({ path: './react-app/.env' });
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

// Configuration
const config = {
  pineconeApiKey: process.env.REACT_APP_PINECONE_API_KEY,
  pineconeEnvironment: process.env.REACT_APP_PINECONE_ENVIRONMENT,
  pineconeIndexName: process.env.REACT_APP_PINECONE_INDEX_NAME,
  voyageApiKey: process.env.REACT_APP_VOYAGE_API_KEY,
  anthropicApiKey: process.env.REACT_APP_ANTHROPIC_API_KEY
};

// Load a small sample of transcript content for testing
async function loadSampleTranscripts() {
  // Create small sample documents instead of reading large files
  const documents = [
    {
      id: 'doc-1',
      name: 'Sample Sales Call 1',
      content: "Speaker 1: Tell me about your current solar setup?\nSpeaker 2: We don't have one yet, but we're interested in learning more about the options.\nSpeaker 1: Great! Our free program in DC allows homeowners to get solar panels installed with no upfront cost.\nSpeaker 2: That sounds too good to be true. What's the catch?",
      type: 'simulation'
    },
    {
      id: 'doc-2',
      name: 'Product Features Overview',
      content: "Our solar panels have a 25-year warranty and typically provide 30-40% savings on electric bills. The system includes monitoring software so you can track production in real-time.",
      type: 'technical'
    },
    {
      id: 'doc-3',
      name: 'Common Objections',
      content: "When customers ask about pricing, emphasize that there are zero upfront costs with our program. For concerns about roof damage, explain our installation process and warranties.",
      type: 'general'
    }
  ];
  
  console.log(`Created ${documents.length} sample documents for testing`);
  return documents;
}

// Index documents
async function indexDocuments(documents) {
  try {
    console.log('Indexing documents...');
    const response = await axios.post(`${API_URL}/indexing/process`, {
      documents,
      pineconeApiKey: config.pineconeApiKey,
      pineconeEnvironment: config.pineconeEnvironment,
      pineconeIndexName: config.pineconeIndexName,
      voyageApiKey: config.voyageApiKey
    });
    
    console.log('Indexing response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error indexing documents:', error.response?.data || error.message);
    throw error;
  }
}

// Query the vector database
async function queryVectorStore(query, mode = 'simulation') {
  try {
    console.log(`Querying with: "${query}"`);
    const response = await axios.post(`${API_URL}/indexing/query`, {
      query,
      mode,
      pineconeApiKey: config.pineconeApiKey,
      pineconeEnvironment: config.pineconeEnvironment,
      pineconeIndexName: config.pineconeIndexName,
      voyageApiKey: config.voyageApiKey,
      topK: 3
    });
    
    console.log('Query response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error querying vector store:', error.response?.data || error.message);
    throw error;
  }
}

// Run the test
async function runTest() {
  try {
    // 1. Load sample transcripts
    const documents = await loadSampleTranscripts();
    
    // 2. Index the documents
    await indexDocuments(documents);
    
    // 3. Query the vector store with a few example queries
    await queryVectorStore("What are common customer objections?");
    await queryVectorStore("How to explain pricing to customers?");
    await queryVectorStore("Tell me about product features");
    
  } catch (error) {
    console.error('Test failed:', error);
  }
}

// Start the API server and run the test
const { spawn } = require('child_process');

console.log('Starting API server...');
const apiServer = spawn('node', ['./react-app/api/server.js'], {
  stdio: 'inherit',
  env: { ...process.env, PORT: '5001' }
});

// Wait a bit for the server to start
setTimeout(async () => {
  try {
    await runTest();
    console.log('Test completed!');
  } catch (error) {
    console.error('Test error:', error);
  } finally {
    // Shutdown the API server
    apiServer.kill();
    process.exit(0);
  }
}, 3000);

// Handle cleanup on exit
process.on('SIGINT', () => {
  apiServer.kill();
  process.exit(0);
});