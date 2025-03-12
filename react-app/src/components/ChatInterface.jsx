import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';

function ChatInterface({ messages, onSendMessage, isInitialized, mode, loadingStatus }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && isInitialized) {
      onSendMessage(input);
      setInput('');
    }
  };
  
  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {!isInitialized ? (
          <div className="initialization-message">
            <p>{loadingStatus || 'Loading transcripts...'}</p>
            <div className="loading-spinner"></div>
          </div>
        ) : messages.length === 0 ? (
          <div className="empty-chat">
            <p>Ask a question about sales calls or solar panel installations.</p>
            {mode === 'simulation' && (
              <p className="simulation-hint">
                In simulation mode, the AI will respond as if it were a salesperson on a call.
              </p>
            )}
          </div>
        ) : (
          messages.map((msg, index) => (
            <ChatMessage key={index} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isInitialized ? "Type your message here..." : "Loading..."}
          disabled={!isInitialized}
        />
        <button 
          type="submit" 
          disabled={!isInitialized || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default ChatInterface;