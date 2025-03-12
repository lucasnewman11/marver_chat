import api from './api';

/**
 * Lists files in a Google Drive folder
 * @param {string} folderId - Google Drive folder ID
 * @param {object} serviceAccountKey - Google Service Account key as JSON object
 * @returns {Promise<Array>} - Array of file objects
 */
export const listFiles = async (folderId, serviceAccountKey) => {
  return api.post('/google-drive/list-files', {
    folderId,
    serviceAccountKey: JSON.parse(serviceAccountKey)
  });
};

/**
 * Gets the content of a Google Drive file
 * @param {string} fileId - Google Drive file ID
 * @param {object} serviceAccountKey - Google Service Account key as JSON object
 * @returns {Promise<Object>} - File content and metadata
 */
export const getFileContent = async (fileId, serviceAccountKey) => {
  return api.post('/google-drive/get-file-content', {
    fileId,
    serviceAccountKey: JSON.parse(serviceAccountKey)
  });
};

/**
 * Loads all files from multiple folders
 * @param {object} folderIds - Object with folder IDs by type
 * @param {object} serviceAccountKey - Google Service Account key as JSON object
 * @returns {Promise<Array>} - Array of document objects
 */
export const loadAllFiles = async (folderIds, serviceAccountKey) => {
  try {
    const parsedKey = JSON.parse(serviceAccountKey);
    const documents = [];
    
    // Process each folder in parallel
    const folders = Object.entries(folderIds).filter(([_, id]) => id);
    
    if (folders.length === 0) {
      throw new Error('No valid folder IDs provided');
    }
    
    await Promise.all(
      folders.map(async ([type, folderId]) => {
        // List files in folder
        const files = await listFiles(folderId, serviceAccountKey);
        
        // Get content for each file in parallel
        const filePromises = files.map(async (file) => {
          const { content, name } = await getFileContent(file.id, serviceAccountKey);
          
          return {
            id: file.id,
            name: name || file.name,
            content,
            type
          };
        });
        
        const folderDocuments = await Promise.all(filePromises);
        documents.push(...folderDocuments);
      })
    );
    
    return documents;
  } catch (error) {
    console.error('Error loading files:', error);
    throw error;
  }
};

export default {
  listFiles,
  getFileContent,
  loadAllFiles
};