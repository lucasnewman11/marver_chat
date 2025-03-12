import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import { loadLocalTranscripts, searchTranscripts, checkTranscriptsLoaded } from './services/localTranscripts';
import './App.css';

function App() {
  // State management
  const [mode, setMode] = useState('assistant'); // 'assistant' or 'simulation'
  const [messages, setMessages] = useState([]);
  const [initialized, setInitialized] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(''); // Track loading status

  // Automatically initialize on mount
  useEffect(() => {
    const initializeTranscripts = async () => {
      try {
        setLoadingStatus('Checking if transcripts are already processed...');
        console.log('Checking if transcripts are already processed...');
        
        // Check if we've already processed the transcripts
        const alreadyLoaded = await checkTranscriptsLoaded();
        
        if (alreadyLoaded) {
          setLoadingStatus('Transcripts already processed and loaded');
          console.log('Transcripts already processed and loaded');
          setInitialized(true);
          return;
        }
        
        setLoadingStatus('Processing local transcripts...');
        console.log('Processing local transcripts...');
        // Process transcripts from scratch
        const result = await loadLocalTranscripts();
        
        if (result.success) {
          setLoadingStatus(result.message);
          console.log(result.message);
          setInitialized(true);
        }
      } catch (error) {
        console.error('Error loading transcripts:', error);
      }
    };
    
    initializeTranscripts();
  }, []);

  const handleModeChange = (newMode) => {
    setMode(newMode);
  };

  const handleSendMessage = async (message) => {
    try {
      // Add user message to chat
      const newMessages = [...messages, { role: 'user', content: message }];
      setMessages(newMessages);
      
      console.log('Processing message:', message, 'in mode:', mode);
      
      // Search transcripts for relevant content
      const context = await searchTranscripts(message, mode);
      
      // Generate response based on context and mode
      let response;
      if (mode === 'simulation') {
        // Add sales-person-like language to response
        response = `Thanks for your question! ${context} I'd be happy to discuss this more based on your specific needs. Would you like to hear about our financing options to make this more affordable?`;
      } else {
        // More straightforward response as an assistant
        response = `Based on our data: ${context}`;
      }
      
      // Add assistant response to chat
      setMessages([...newMessages, { role: 'assistant', content: response }]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message to chat
      const errorMessages = [...messages, { role: 'user', content: message }];
      setMessages([
        ...errorMessages, 
        { 
          role: 'assistant', 
          content: `I'm sorry, I encountered an error. Please try again.` 
        }
      ]);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Sales Call Simulator</h1>
        <div className="mode-toggle">
          <label>
            <input 
              type="radio" 
              name="mode" 
              value="assistant" 
              checked={mode === 'assistant'} 
              onChange={() => handleModeChange('assistant')} 
            />
            Assistant Mode
          </label>
          <label>
            <input 
              type="radio" 
              name="mode" 
              value="simulation" 
              checked={mode === 'simulation'} 
              onChange={() => handleModeChange('simulation')} 
            />
            Sales Simulation
          </label>
        </div>
      </header>
      <main>
        <ChatInterface 
          messages={messages}
          onSendMessage={handleSendMessage}
          isInitialized={initialized}
          mode={mode}
          loadingStatus={loadingStatus}
        />
      </main>
    </div>
  );
}

export default App;