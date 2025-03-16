/**
 * Service to interact with Pinecone for vector database operations
 */

import { Pinecone } from '@pinecone-database/pinecone';
import { v4 as uuidv4 } from 'uuid';

// Initialize Pinecone client
let pineconeClient = null;
let pineconeIndex = null;

/**
 * Initialize Pinecone client and index
 */
export const initPinecone = async () => {
  try {
    // Return cached clients if available
    if (pineconeClient && pineconeIndex) {
      return { client: pineconeClient, index: pineconeIndex };
    }

    // Get API key and index name from environment variables
    const apiKey = process.env.REACT_APP_PINECONE_API_KEY;
    const indexName = process.env.REACT_APP_PINECONE_INDEX_NAME || 'sales-simulator';

    // Validate required configuration
    if (!apiKey) {
      throw new Error('Pinecone API key is required');
    }

    console.log('Initializing Pinecone client...');
    // Initialize Pinecone client
    pineconeClient = new Pinecone({
      apiKey
    });

    // Get or create index
    const indexesList = await pineconeClient.listIndexes();
    const indexList = indexesList.indexes?.map(index => index.name) || [];
    
    if (!indexList.includes(indexName)) {
      console.log(`Creating Pinecone index: ${indexName}`);
      // Create index with vector dimensions for our simple embeddings
      // Using dimension 1024 as a sensible default
      await pineconeClient.createIndex({
        name: indexName,
        dimension: 1024, 
        metric: 'cosine',
        spec: {
          serverless: {
            cloud: 'gcp',
            region: 'us-central1'
          }
        }
      });
      
      // Wait for index initialization (can take a minute)
      console.log('Waiting for index to initialize...');
      await new Promise(resolve => setTimeout(resolve, 60000));
    }

    // Connect to the index
    pineconeIndex = pineconeClient.index(indexName);
    console.log(`Connected to Pinecone index: ${indexName}`);

    return { client: pineconeClient, index: pineconeIndex };
  } catch (error) {
    console.error('Error initializing Pinecone:', error);
    throw error;
  }
};

/**
 * Convert sparse embeddings to dense vectors
 * @param {Object} sparseEmbedding - Sparse embedding (term -> weight)
 * @param {number} dimension - Desired vector dimension
 * @returns {Array} - Dense vector
 */
const convertToDenseVector = (sparseEmbedding, dimension = 1024) => {
  // Simple conversion: hash terms to positions and use weights as values
  const vector = new Array(dimension).fill(0);
  
  // Compute hash-based indices for each term
  Object.entries(sparseEmbedding).forEach(([term, weight]) => {
    // Simple hashing function to map string to index
    const hashCode = term.split('').reduce(
      (hash, char) => ((hash << 5) - hash) + char.charCodeAt(0), 0
    );
    const index = Math.abs(hashCode) % dimension;
    vector[index] = weight;
  });
  
  return vector;
};

/**
 * Upsert document vectors to Pinecone
 * @param {Array} documents - Array of document objects with embeddings
 */
export const upsertVectors = async (documents) => {
  try {
    const { index } = await initPinecone();
    
    // Convert documents to Pinecone vector format
    const vectors = documents.map(doc => {
      // Convert sparse embedding to dense vector
      const vector = convertToDenseVector(doc.embedding);
      
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
      await index.upsert(batch);
      console.log(`Upserted batch ${i/batchSize + 1} of ${Math.ceil(vectors.length/batchSize)}`);
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
 * @param {Array} queryVector - Query vector
 * @param {number} topK - Number of results to return
 * @returns {Array} - Array of matching documents
 */
export const queryVectors = async (queryEmbedding, topK = 3) => {
  try {
    const { index } = await initPinecone();
    
    // Convert query embedding to dense vector
    const queryVector = convertToDenseVector(queryEmbedding);
    
    // Query Pinecone
    const results = await index.query({
      vector: queryVector,
      topK,
      includeMetadata: true,
      namespace: ''
    });
    
    // Format results
    return results.matches.map(match => ({
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
    const { index } = await initPinecone();
    
    // Get all unique metadata.fileId values from the index
    // We have to use a fetch endpoint since Pinecone doesn't have a direct way to list unique metadata values
    const result = await index.fetch({ 
      ids: [], 
      top_k: 10000 // Set a large enough value to get all vectors
    });
    
    // Extract unique file IDs from the metadata
    const fileIds = new Set();
    const vectors = Object.values(result.vectors || {});
    
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