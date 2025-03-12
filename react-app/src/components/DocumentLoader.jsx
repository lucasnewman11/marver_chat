import React, { useState } from 'react';

function DocumentLoader({ config, onInitialize, loading }) {
  const [simulationFolderId, setSimulationFolderId] = useState(config.googleDrive.simulationFolderId || '');
  const [technicalFolderId, setTechnicalFolderId] = useState(config.googleDrive.technicalFolderId || '');
  const [generalFolderId, setGeneralFolderId] = useState(config.googleDrive.generalFolderId || '');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    const folderIds = {
      simulation: simulationFolderId,
      technical: technicalFolderId,
      general: generalFolderId
    };
    
    // Check if at least one folder ID is provided
    if (!simulationFolderId && !technicalFolderId && !generalFolderId) {
      alert('Please enter at least one folder ID');
      return;
    }
    
    onInitialize(folderIds);
  };
  
  return (
    <div className="document-loader">
      <h3>Google Drive Folders</h3>
      <p>Specify the Google Drive folder IDs containing your documents:</p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="simulationFolderId">Simulation Folder ID:</label>
          <input 
            type="text" 
            id="simulationFolderId" 
            value={simulationFolderId}
            onChange={(e) => setSimulationFolderId(e.target.value)}
            disabled={loading}
            placeholder="Google Drive folder with high-quality calls"
          />
          <small>Contains high-quality sales call transcripts</small>
        </div>
        
        <div className="form-group">
          <label htmlFor="technicalFolderId">Technical Folder ID:</label>
          <input 
            type="text" 
            id="technicalFolderId" 
            value={technicalFolderId}
            onChange={(e) => setTechnicalFolderId(e.target.value)}
            disabled={loading}
            placeholder="Google Drive folder with technical docs"
          />
          <small>Contains product specifications and technical documents</small>
        </div>
        
        <div className="form-group">
          <label htmlFor="generalFolderId">General Folder ID:</label>
          <input 
            type="text" 
            id="generalFolderId" 
            value={generalFolderId}
            onChange={(e) => setGeneralFolderId(e.target.value)}
            disabled={loading}
            placeholder="Google Drive folder with other calls"
          />
          <small>Contains other call transcripts or general documentation</small>
        </div>
        
        <button 
          type="submit" 
          disabled={loading}
          className="primary-button"
        >
          {loading ? 'Loading and Indexing...' : 'Load and Index Documents'}
        </button>
        
        {loading && <div className="loading-indicator">Processing documents...</div>}
      </form>
      
      <div className="credentials-note">
        <p><small>API keys and credentials are loaded from environment variables.</small></p>
      </div>
    </div>
  );
}

export default DocumentLoader;