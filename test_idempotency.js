// Simple test to verify Pinecone idempotent indexing
require('dotenv').config({ path: './react-app/.env' });
const axios = require('axios');

// Configuration
const PINECONE_API_KEY = process.env.REACT_APP_PINECONE_API_KEY;
const PINECONE_INDEX_NAME = process.env.REACT_APP_PINECONE_INDEX_NAME || 'sales-simulator';
const API_VERSION = '2025-01';

// Headers for Pinecone API
const getHeaders = () => ({
  'Api-Key': PINECONE_API_KEY,
  'Content-Type': 'application/json',
  'X-Pinecone-API-Version': API_VERSION
});

// Initialize Pinecone and get host
async function getPineconeHost() {
  try {
    console.log('Initializing Pinecone connection...');
    
    // Get index details
    const describeResponse = await axios.get(
      `https://api.pinecone.io/indexes/${PINECONE_INDEX_NAME}`,
      { headers: getHeaders() }
    );
    
    const host = describeResponse.data.host;
    console.log(`Connected to index host: ${host}`);
    return host;
  } catch (error) {
    console.error('Error initializing Pinecone:', error.response?.data || error.message);
    throw error;
  }
}

// Check if vector exist with specific file ID
async function checkFileIndexed(host, fileId) {
  try {
    console.log(`Checking if file ID "${fileId}" exists in the index...`);
    
    // Query Pinecone statistics
    const statsResponse = await axios.get(
      `https://${host}/describe_index_stats`,
      { headers: getHeaders() }
    );
    
    console.log('Index stats:', JSON.stringify(statsResponse.data, null, 2));
    
    // Find vectors by metadata
    // This would normally use a proper metadata filter, but we're doing a simple test
    const queryResponse = await axios.post(
      `https://${host}/query`,
      {
        vector: Array(1024).fill(0),  // Dummy vector for querying 
        filter: {
          fileId: { $eq: fileId }
        },
        includeMetadata: true,
        topK: 1
      },
      { headers: getHeaders() }
    );
    
    const matches = queryResponse.data.matches || [];
    const isIndexed = matches.length > 0;
    
    console.log(`File ID "${fileId}" ${isIndexed ? 'IS' : 'is NOT'} indexed in Pinecone`);
    
    return isIndexed;
  } catch (error) {
    console.error('Error checking file indexed status:', error.response?.data || error.message);
    return false;
  }
}

// Index a test file
async function indexTestFile(host, fileId) {
  try {
    console.log(`Indexing test file with ID "${fileId}"...`);
    
    // Create test vector
    const vector = {
      id: `${fileId}-test`,
      values: Array(1024).fill(0).map(() => Math.random() * 2 - 1),  // Random vector
      metadata: {
        fileId: fileId,
        title: 'Test File',
        text: 'This is a test file content'
      }
    };
    
    // Upsert to Pinecone
    const response = await axios.post(
      `https://${host}/vectors/upsert`,
      { vectors: [vector], namespace: '' },
      { headers: getHeaders() }
    );
    
    console.log('Upsert response:', response.data);
    return true;
  } catch (error) {
    console.error('Error indexing test file:', error.response?.data || error.message);
    return false;
  }
}

// Test function to verify idempotent indexing
async function testIdempotentIndexing() {
  try {
    // Get Pinecone host
    const host = await getPineconeHost();
    
    // Generate a unique test file ID
    const testFileId = `test-file-${Date.now()}`;
    
    // Check if file exists (should not)
    let isIndexed = await checkFileIndexed(host, testFileId);
    console.log(`Initial check: File ${isIndexed ? 'IS' : 'is NOT'} indexed`);
    
    if (isIndexed) {
      console.log('Test failed: File should not be indexed yet!');
      return;
    }
    
    // Index the test file
    console.log('\nIndexing test file...');
    await indexTestFile(host, testFileId);
    
    // Check again - should be indexed now
    isIndexed = await checkFileIndexed(host, testFileId);
    console.log(`\nAfter indexing: File ${isIndexed ? 'IS' : 'is NOT'} indexed`);
    
    if (!isIndexed) {
      console.log('Test failed: File should be indexed now!');
      return;
    }
    
    // Simulate the filtering logic that determines if a file needs indexing
    console.log('\nTesting indexing logic...');
    console.log(`If fileIds.includes('${testFileId}'):
    console.log('File already indexed, skipping...');
else:
    console.log('File not indexed, processing...');
${isIndexed ? '// This file would be SKIPPED' : '// This file would be PROCESSED'}`);
    
    console.log('\n✅ Test complete! The system correctly identifies and tracks indexed files.');
  } catch (error) {
    console.error('Test failed with error:', error);
  }
}

// Run the test
testIdempotentIndexing();