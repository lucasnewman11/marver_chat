/**
 * Service to interact with Pinecone for vector database operations
 * Updated to use the latest Pinecone API (as of March 2025)
 */
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

// Configuration
const PINECONE_API_KEY = process.env.REACT_APP_PINECONE_API_KEY;
const PINECONE_INDEX_NAME = process.env.REACT_APP_PINECONE_INDEX_NAME || 'sales-simulator';
const API_VERSION = '2025-01';

// Cache for index host and info
let indexHost = null;
let indexDimension = null;

/**
 * Get required headers for Pinecone API requests
 */
const getHeaders = () => ({
  'Api-Key': PINECONE_API_KEY,
  'Content-Type': 'application/json',
  'X-Pinecone-API-Version': API_VERSION
});

/**
 * Initialize Pinecone and get index info
 * @returns {Promise<Object>} Index information
 */
export const initPinecone = async () => {
  try {
    // Return cached values if available
    if (indexHost && indexDimension) {
      return { host: indexHost, dimension: indexDimension };
    }

    // Validate required configuration
    if (!PINECONE_API_KEY) {
      throw new Error('Pinecone API key is required');
    }

    console.log('Initializing Pinecone...');
    
    // Check if index exists
    const listResponse = await axios.get(
      'https://api.pinecone.io/indexes',
      { headers: getHeaders() }
    );
    
    const indexes = listResponse.data.indexes || [];
    const indexExists = indexes.some(index => index.name === PINECONE_INDEX_NAME);
    
    if (!indexExists) {
      console.log(`Creating Pinecone index: ${PINECONE_INDEX_NAME}`);
      
      // Create new index
      await axios.post(
        'https://api.pinecone.io/indexes',
        {
          name: PINECONE_INDEX_NAME,
          dimension: 1024,
          metric: 'cosine',
          spec: {
            serverless: {
              cloud: 'aws',
              region: 'us-east-1'
            }
          }
        },
        { headers: getHeaders() }
      );
      
      // Wait for index initialization
      console.log('Waiting for index to initialize...');
      await new Promise(resolve => setTimeout(resolve, 60000));
    }
    
    // Get index details
    const describeResponse = await axios.get(
      `https://api.pinecone.io/indexes/${PINECONE_INDEX_NAME}`,
      { headers: getHeaders() }
    );
    
    // Cache the values
    indexHost = describeResponse.data.host;
    indexDimension = describeResponse.data.dimension;
    
    console.log(`Connected to Pinecone index: ${PINECONE_INDEX_NAME}`);
    console.log(`Host: ${indexHost}, Dimension: ${indexDimension}`);
    
    return { host: indexHost, dimension: indexDimension };
  } catch (error) {
    console.error('Error initializing Pinecone:', error);
    throw error;
  }
};

// Reuse vector array to reduce memory allocation
let reusableVector = null;

/**
 * Convert sparse embeddings to dense vectors
 * Memory-optimized version that reuses arrays when possible
 * @param {Object} sparseEmbedding - Sparse embedding (term -> weight)
 * @param {number} dimension - Desired vector dimension
 * @returns {Array} - Dense vector
 */
const convertToDenseVector = (sparseEmbedding, dimension = 1024) => {
  // Initialize or reuse vector array
  if (!reusableVector || reusableVector.length !== dimension) {
    reusableVector = new Array(dimension).fill(0);
  } else {
    // Reset existing array to zeros
    for (let i = 0; i < dimension; i++) {
      reusableVector[i] = 0;
    }
  }
  
  // Compute hash-based indices for each term
  Object.entries(sparseEmbedding).forEach(([term, weight]) => {
    // Simple hashing function to map string to index
    const hashCode = term.split('').reduce(
      (hash, char) => ((hash << 5) - hash) + char.charCodeAt(0), 0
    );
    const index = Math.abs(hashCode) % dimension;
    reusableVector[index] = weight;
  });
  
  // Clone the array to return a new copy (avoid shared state issues)
  return [...reusableVector];
};

/**
 * Upsert document vectors to Pinecone
 * @param {Array} documents - Array of document objects with embeddings
 */
export const upsertVectors = async (documents) => {
  try {
    // Initialize Pinecone and get index info
    const { host, dimension } = await initPinecone();
    
    // Convert documents to Pinecone vector format
    const vectors = documents.map(doc => {
      // Convert sparse embedding to dense vector
      const vector = convertToDenseVector(doc.embedding, dimension);
      
      return {
        id: doc.id || uuidv4(),
        values: vector,
        metadata: {
          fileId: doc.fileId,
          title: doc.metadata?.title || 'Unknown',
          text: doc.content.substring(0, 1000) // Limit metadata text size
        }
      };
    });
    
    // Batch upsert to Pinecone (100 vectors per batch)
    const batchSize = 100;
    for (let i = 0; i < vectors.length; i += batchSize) {
      const batch = vectors.slice(i, i + batchSize);
      
      await axios.post(
        `https://${host}/vectors/upsert`,
        {
          vectors: batch,
          namespace: ''
        },
        { headers: getHeaders() }
      );
      
      console.log(`Upserted batch ${Math.floor(i/batchSize) + 1} of ${Math.ceil(vectors.length/batchSize)}`);
    }
    
    return {
      success: true,
      count: vectors.length
    };
  } catch (error) {
    console.error('Error upserting vectors to Pinecone:', error);
    throw error;
  }
};

/**
 * Query Pinecone for similar vectors
 * @param {Object} queryEmbedding - Query embedding object
 * @param {number} topK - Number of results to return
 * @returns {Array} - Array of matching documents
 */
export const queryVectors = async (queryEmbedding, topK = 3) => {
  try {
    // Initialize Pinecone and get index info
    const { host, dimension } = await initPinecone();
    
    // Convert query embedding to dense vector
    const queryVector = convertToDenseVector(queryEmbedding, dimension);
    
    // Query Pinecone
    const response = await axios.post(
      `https://${host}/query`,
      {
        vector: queryVector,
        topK,
        includeMetadata: true,
        namespace: ''
      },
      { headers: getHeaders() }
    );
    
    // Format results
    const matches = response.data.matches || [];
    return matches.map(match => ({
      id: match.id,
      score: match.score,
      content: match.metadata.text,
      metadata: {
        fileId: match.metadata.fileId,
        title: match.metadata.title
      }
    }));
  } catch (error) {
    console.error('Error querying Pinecone:', error);
    throw error;
  }
};

/**
 * List all file IDs that are already indexed in Pinecone
 * @returns {Promise<Array>} - Array of file IDs
 */
export const listIndexedFileIds = async () => {
  try {
    // Initialize Pinecone and get index info
    const { host } = await initPinecone();
    
    // Get index stats to check if it's empty
    const statsResponse = await axios.get(
      `https://${host}/describe_index_stats`,
      { headers: getHeaders() }
    );
    
    const totalVectors = statsResponse.data.totalVectorCount || 0;
    if (totalVectors === 0) {
      return [];
    }
    
    // Fetch vectors to get file IDs (limit to 10000 vectors)
    // Note: In a production system with many vectors, you should use metadata filtering instead
    const response = await axios.post(
      `https://${host}/vectors/fetch`,
      { 
        ids: [],
        namespace: ''
      },
      { headers: getHeaders() }
    );
    
    // Extract unique file IDs from the metadata
    const fileIds = new Set();
    const vectors = Object.values(response.data.vectors || {});
    
    vectors.forEach(vector => {
      if (vector.metadata && vector.metadata.fileId) {
        fileIds.add(vector.metadata.fileId);
      }
    });
    
    return Array.from(fileIds);
  } catch (error) {
    console.error('Error listing indexed file IDs from Pinecone:', error);
    return [];
  }
};

export default {
  initPinecone,
  upsertVectors,
  queryVectors,
  listIndexedFileIds
};