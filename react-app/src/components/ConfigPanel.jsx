import React from 'react';
import DocumentLoader from './DocumentLoader';

function ConfigPanel({ 
  config, 
  onConfigChange, 
  onInitialize, 
  onReset, 
  initialized, 
  loading, 
  mode, 
  onModeChange 
}) {
  const handleModeChange = (e) => {
    onModeChange(e.target.value);
  };

  return (
    <div className="config-panel">
      <h2>Configuration</h2>
      
      {/* Mode Selection */}
      <div className="mode-selection">
        <label htmlFor="mode">Mode:</label>
        <select 
          id="mode" 
          value={mode} 
          onChange={handleModeChange}
          disabled={loading}
        >
          <option value="assistant">Assistant</option>
          <option value="simulation">Sales Simulation</option>
        </select>
      </div>
      
      <div className="documents">
        <h3>Document Sources</h3>
        
        <div className="api-keys-info">
          <p>API keys are loaded from environment variables.</p>
        </div>
        
        {!initialized ? (
          <DocumentLoader 
            config={config}
            onInitialize={onInitialize}
            loading={loading}
          />
        ) : (
          <div className="documents-loaded">
            <p>Documents loaded and indexed!</p>
            <button 
              onClick={onReset}
              disabled={loading}
            >
              Reset & Load New Documents
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ConfigPanel;