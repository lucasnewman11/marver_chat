import streamlit as st
import os
import sys
import json
from dotenv import load_dotenv
from anthropic import Anthropic
import os

# Add the src directory to the path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.rag_all_files_non_interactive import load_transcript_metadata, load_transcript_content, query_claude

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Sales Call RAG System",
    page_icon="☎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents_loaded" not in st.session_state:
    st.session_state.documents_loaded = False
if "metadata" not in st.session_state:
    st.session_state.metadata = None

def load_documents():
    """Load documents from the cached transcripts"""
    with st.spinner("Loading document metadata..."):
        metadata = load_transcript_metadata()
        if metadata:
            st.session_state.metadata = metadata
            st.session_state.documents_loaded = True
            st.success(f"Loaded metadata for {len(metadata)} documents")
            return True
        return False

# Sidebar
st.sidebar.title("Sales Call RAG System")
st.sidebar.caption("A simple RAG interface for sales call transcripts")

# Load documents button
if not st.session_state.documents_loaded:
    if st.sidebar.button("Load Documents"):
        load_documents()
else:
    st.sidebar.success(f"{len(st.session_state.metadata)} documents loaded")

# Mode selection
mode = st.sidebar.radio(
    "Select Mode",
    ["Assistant", "Sales Simulation"]
)

# System prompt based on mode
if mode == "Assistant":
    system_prompt = """You are an AI assistant that provides factual information about sales calls.
    You should analyze the sales call transcripts objectively and provide clear, concise information.
    Stick to the facts present in the transcripts and avoid making assumptions."""
else:  # Sales Simulation
    system_prompt = """You are an AI that simulates a salesperson selling home energy products.
    Use the sales call transcripts as a guide for your tone, style, and techniques.
    Respond as if you are the salesperson in these transcripts, using similar persuasion techniques, 
    enthusiasm, and product knowledge. Focus on solar panel installation, energy efficiency, and cost savings."""

# Main content area
st.title("Sales Call RAG System")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about the sales call transcripts..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        if not st.session_state.documents_loaded:
            response = "Please load the documents first using the button in the sidebar."
            st.markdown(response)
        else:
            with st.spinner("Thinking..."):
                # Load content for the query
                message_placeholder = st.empty()
                message_placeholder.markdown("Loading relevant documents...")
                
                # Load relevant documents
                documents = load_transcript_content(st.session_state.metadata)
                
                # Query Claude with the prompt and documents
                message_placeholder.markdown("Generating response...")
                claude_response = query_claude(prompt, documents, system_prompt)
                
                # Display response
                message_placeholder.markdown(claude_response)
        
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": claude_response if st.session_state.documents_loaded else response})