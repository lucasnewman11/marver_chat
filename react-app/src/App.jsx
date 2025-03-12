import React, { useState, useEffect } from 'react';
import ConfigPanel from './components/ConfigPanel';
import ChatInterface from './components/ChatInterface';
import './App.css';

// These services will be used later when we integrate with the backend
// import indexingService from './services/indexingService';
// import chatService from './services/chatService';

function App() {
  // State management
  const [mode, setMode] = useState('assistant'); // 'assistant' or 'simulation'
  const [initialized, setInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [config, setConfig] = useState({
    apiKeys: {
      anthropic: process.env.REACT_APP_ANTHROPIC_API_KEY || '',
      voyage: process.env.REACT_APP_VOYAGE_API_KEY || '',
      pinecone: process.env.REACT_APP_PINECONE_API_KEY || ''
    },
    pinecone: {
      environment: process.env.REACT_APP_PINECONE_ENVIRONMENT || '',
      indexName: process.env.REACT_APP_PINECONE_INDEX_NAME || 'sales-simulator'
    },
    googleDrive: {
      serviceAccountKey: process.env.REACT_APP_GOOGLE_SERVICE_ACCOUNT_JSON || '',
      simulationFolderId: process.env.REACT_APP_SIMULATION_FOLDER_ID || '',
      technicalFolderId: process.env.REACT_APP_TECHNICAL_FOLDER_ID || '',
      generalFolderId: process.env.REACT_APP_GENERAL_FOLDER_ID || ''
    }
  });

  // Load config from local storage on mount
  useEffect(() => {
    const savedConfig = localStorage.getItem('chatbotConfig');
    if (savedConfig) {
      try {
        setConfig(JSON.parse(savedConfig));
      } catch (e) {
        console.error('Error parsing saved config:', e);
      }
    }
  }, []);

  // Save config to local storage when it changes
  useEffect(() => {
    localStorage.setItem('chatbotConfig', JSON.stringify(config));
  }, [config]);

  const handleModeChange = (newMode) => {
    setMode(newMode);
  };

  const handleConfigChange = (newConfig) => {
    setConfig({...config, ...newConfig});
  };

  const handleInitialize = async (folderIds) => {
    setLoading(true);
    try {
      // Save the folder IDs to the config
      const updatedConfig = {
        ...config,
        googleDrive: {
          ...config.googleDrive,
          simulationFolderId: folderIds.simulation,
          technicalFolderId: folderIds.technical,
          generalFolderId: folderIds.general
        }
      };
      setConfig(updatedConfig);
      
      // For now, we're simulating the indexing process
      console.log('Would initialize with folder IDs:', folderIds);
      
      // Simulate delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      console.log('Indexing complete (simulated)');
      setInitialized(true);
    } catch (error) {
      console.error('Initialization error:', error);
      alert(`Error initializing: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setInitialized(false);
    setMessages([]);
  };

  const handleSendMessage = async (message) => {
    try {
      // Add user message to chat
      const newMessages = [...messages, { role: 'user', content: message }];
      setMessages(newMessages);
      
      // For now, we're simulating the chat response
      console.log('Would send message:', message, 'in mode:', mode);
      
      // Simulate delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Simulated response based on mode
      let response;
      if (mode === 'simulation') {
        response = "This is a simulated sales response. As a salesperson, I'd suggest our premium solar panel package that would be perfect for your home. I notice you're interested in reducing your energy bills, and our panels could save you up to 60% annually. Would you like me to tell you more about our financing options?";
      } else {
        response = "As an assistant, I can tell you that our solar panels have an efficiency rating of 22%, which is among the highest in the industry. Each panel generates approximately 400 watts of power in ideal conditions. The warranty covers 25 years of performance with minimal degradation over time.";
      }
      
      // Add assistant response to chat
      setMessages([...newMessages, { role: 'assistant', content: response }]);
    } catch (error) {
      console.error('Error sending message:', error);
      alert(`Error: ${error.message}`);
      
      // Add error message to chat
      const errorMessages = [...messages, { role: 'user', content: message }];
      setMessages([
        ...errorMessages, 
        { 
          role: 'assistant', 
          content: `I'm sorry, I encountered an error: ${error.message}. Please try again.` 
        }
      ]);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Sales Call Simulator</h1>
      </header>
      <main>
        <div className="container">
          <div className="sidebar">
            <ConfigPanel 
              config={config}
              onConfigChange={handleConfigChange}
              onInitialize={handleInitialize}
              onReset={handleReset}
              initialized={initialized}
              loading={loading}
              mode={mode}
              onModeChange={handleModeChange}
            />
          </div>
          <div className="content">
            <ChatInterface 
              messages={messages}
              onSendMessage={handleSendMessage}
              isInitialized={initialized}
              mode={mode}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;