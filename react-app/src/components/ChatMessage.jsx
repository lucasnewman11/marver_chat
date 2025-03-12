import React from 'react';

function ChatMessage({ message }) {
  const { role, content } = message;
  
  return (
    <div className={`chat-message ${role === 'user' ? 'user-message' : 'assistant-message'}`}>
      <div className="message-avatar">
        {role === 'user' ? '=d' : '>'}
      </div>
      <div className="message-content">
        <p>{content}</p>
      </div>
    </div>
  );
}

export default ChatMessage;