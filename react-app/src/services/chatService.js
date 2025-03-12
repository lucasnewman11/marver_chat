import api from './api';

/**
 * Sends a message to the chat API
 * @param {string} message - User's message
 * @param {string} context - Retrieved context from documents
 * @param {string} mode - Chat mode ('assistant' or 'simulation')
 * @param {string} anthropicApiKey - Anthropic API key
 * @returns {Promise<Object>} - Response message
 */
export const sendMessage = async (message, context, mode, anthropicApiKey) => {
  return api.post('/chat/message', {
    message,
    context,
    mode,
    anthropicApiKey
  });
};

/**
 * Queries the index and gets a response
 * @param {string} message - User's message
 * @param {string} mode - Chat mode ('assistant' or 'simulation')
 * @param {object} config - Configuration object with API keys
 * @returns {Promise<string>} - Assistant response
 */
export const queryAndGetResponse = async (message, mode, config) => {
  try {
    // Query the vector store to get relevant context
    const queryResponse = await api.post('/indexing/query', {
      query: message,
      mode,
      pineconeApiKey: config.apiKeys.pinecone,
      pineconeEnvironment: config.pinecone.environment,
      pineconeIndexName: config.pinecone.indexName,
      voyageApiKey: config.apiKeys.voyage,
      topK: mode === 'simulation' ? 3 : 5
    });
    
    // Get response from Anthropic
    const chatResponse = await sendMessage(
      message,
      queryResponse.context,
      mode,
      config.apiKeys.anthropic
    );
    
    return chatResponse.message;
  } catch (error) {
    console.error('Error in query and response:', error);
    throw error;
  }
};

export default {
  sendMessage,
  queryAndGetResponse
};