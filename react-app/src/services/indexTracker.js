/**
 * Service to track which transcripts have been indexed in Pinecone
 */

import localforage from 'localforage';

// Initialize localforage instance for tracking indexed transcripts
const indexedTranscriptsStore = localforage.createInstance({
  name: 'indexedTranscripts'
});

/**
 * Mark a transcript as indexed in Pinecone
 * @param {string} fileId - The file ID of the indexed transcript
 */
export const markTranscriptAsIndexed = async (fileId) => {
  try {
    // Get currently indexed transcripts
    const indexedTranscripts = await getIndexedTranscripts();
    
    // Add this file if it's not already there
    if (!indexedTranscripts.includes(fileId)) {
      indexedTranscripts.push(fileId);
      await indexedTranscriptsStore.setItem('indexed', indexedTranscripts);
    }
  } catch (error) {
    console.error('Error marking transcript as indexed:', error);
  }
};

/**
 * Mark multiple transcripts as indexed in Pinecone
 * @param {Array} fileIds - Array of file IDs
 */
export const markTranscriptsAsIndexed = async (fileIds) => {
  try {
    // Get currently indexed transcripts
    const indexedTranscripts = await getIndexedTranscripts();
    
    // Add all files that aren't already there
    let updated = false;
    for (const fileId of fileIds) {
      if (!indexedTranscripts.includes(fileId)) {
        indexedTranscripts.push(fileId);
        updated = true;
      }
    }
    
    // Save if there were updates
    if (updated) {
      await indexedTranscriptsStore.setItem('indexed', indexedTranscripts);
    }
  } catch (error) {
    console.error('Error marking transcripts as indexed:', error);
  }
};

/**
 * Get list of all transcripts already indexed in Pinecone
 * @returns {Array} - Array of file IDs
 */
export const getIndexedTranscripts = async () => {
  try {
    const indexedTranscripts = await indexedTranscriptsStore.getItem('indexed');
    return indexedTranscripts || [];
  } catch (error) {
    console.error('Error getting indexed transcripts:', error);
    return [];
  }
};

/**
 * Check if a transcript is already indexed in Pinecone
 * @param {string} fileId - The file ID to check
 * @returns {boolean} - Whether the transcript is indexed
 */
export const isTranscriptIndexed = async (fileId) => {
  try {
    const indexedTranscripts = await getIndexedTranscripts();
    return indexedTranscripts.includes(fileId);
  } catch (error) {
    console.error('Error checking if transcript is indexed:', error);
    return false;
  }
};

/**
 * Reset the indexed transcripts tracking
 */
export const resetIndexedTranscripts = async () => {
  try {
    await indexedTranscriptsStore.setItem('indexed', []);
  } catch (error) {
    console.error('Error resetting indexed transcripts:', error);
  }
};

export default {
  markTranscriptAsIndexed,
  markTranscriptsAsIndexed,
  getIndexedTranscripts,
  isTranscriptIndexed,
  resetIndexedTranscripts
};