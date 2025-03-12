import api from './api';
import googleDriveService from './googleDrive';

/**
 * Processes documents and creates embeddings in Pinecone
 * @param {Array} documents - Array of document objects
 * @param {object} config - Configuration object with API keys
 * @returns {Promise<Object>} - Indexing result
 */
export const processDocuments = async (documents, config) => {
  return api.post('/indexing/process', {
    documents,
    pineconeApiKey: config.apiKeys.pinecone,
    pineconeEnvironment: config.pinecone.environment,
    pineconeIndexName: config.pinecone.indexName,
    voyageApiKey: config.apiKeys.voyage
  });
};

/**
 * Loads documents from Google Drive and processes them for indexing
 * @param {object} folderIds - Object with folder IDs by type
 * @param {object} config - Configuration object with API keys
 * @returns {Promise<Object>} - Indexing result
 */
export const loadAndProcessDocuments = async (folderIds, config) => {
  try {
    // Step 1: Load documents from Google Drive
    const documents = await googleDriveService.loadAllFiles(
      folderIds, 
      config.googleDrive.serviceAccountKey
    );
    
    if (!documents || documents.length === 0) {
      throw new Error('No documents were loaded from Google Drive');
    }
    
    console.log(`Loaded ${documents.length} documents from Google Drive`);
    
    // Step 2: Process and index documents
    const result = await processDocuments(documents, config);
    
    return {
      documentCount: documents.length,
      ...result
    };
  } catch (error) {
    console.error('Error in document loading and processing:', error);
    throw error;
  }
};

export default {
  processDocuments,
  loadAndProcessDocuments
};