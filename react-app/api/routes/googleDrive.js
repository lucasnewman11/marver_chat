const express = require('express');
const router = express.Router();
const { google } = require('googleapis');
const { Readable } = require('stream');

// Helper to initialize Google Drive client
const getDriveClient = (serviceAccountKey) => {
  const auth = new google.auth.GoogleAuth({
    credentials: serviceAccountKey,
    scopes: ['https://www.googleapis.com/auth/drive.readonly']
  });
  
  return google.drive({ version: 'v3', auth });
};

// List files in a folder
router.post('/list-files', async (req, res) => {
  try {
    const { folderId, serviceAccountKey } = req.body;
    
    if (!folderId) {
      return res.status(400).json({ error: 'Folder ID is required' });
    }
    
    if (!serviceAccountKey) {
      return res.status(400).json({ error: 'Service account key is required' });
    }
    
    const drive = getDriveClient(serviceAccountKey);
    
    const response = await drive.files.list({
      q: `'${folderId}' in parents and trashed=false and mimeType='application/vnd.google-apps.document'`,
      fields: 'files(id, name, mimeType)',
      pageSize: 100
    });
    
    res.json(response.data.files);
  } catch (error) {
    console.error('Error listing files:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get file content
router.post('/get-file-content', async (req, res) => {
  try {
    const { fileId, serviceAccountKey } = req.body;
    
    if (!fileId) {
      return res.status(400).json({ error: 'File ID is required' });
    }
    
    if (!serviceAccountKey) {
      return res.status(400).json({ error: 'Service account key is required' });
    }
    
    const drive = getDriveClient(serviceAccountKey);
    
    // Get file metadata
    const fileMetadata = await drive.files.get({
      fileId,
      fields: 'name,mimeType'
    });
    
    let content;
    
    // Handle Google Docs differently
    if (fileMetadata.data.mimeType === 'application/vnd.google-apps.document') {
      const response = await drive.files.export({
        fileId,
        mimeType: 'text/plain'
      });
      content = response.data;
    } else {
      // For other file types
      const response = await drive.files.get({
        fileId,
        alt: 'media'
      });
      content = response.data;
    }
    
    res.json({
      name: fileMetadata.data.name,
      content
    });
  } catch (error) {
    console.error('Error getting file content:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;