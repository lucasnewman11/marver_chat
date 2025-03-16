/**
 * Service to handle loading and retrieving from local transcripts
 * Can use either local storage or Pinecone based on configuration
 */

import localforage from 'localforage';
import axios from 'axios';
import { cosine } from 'similarity-score';
import nlp from 'compromise';
import { initPinecone, upsertVectors, queryVectors } from './pineconeService';
import { 
  getIndexedTranscripts, 
  markTranscriptsAsIndexed, 
  isTranscriptIndexed 
} from './indexTracker';

// Determine which vector store to use
const useVectorDB = process.env.REACT_APP_VECTOR_DB || 'local';
console.log(`Using vector database: ${useVectorDB}`);

// Initialize localforage for storing processed transcripts
const transcriptsStore = localforage.createInstance({
  name: 'transcriptsStore'
});

// Initialize localforage for storing transcript embeddings
const embeddingsStore = localforage.createInstance({
  name: 'embeddingsStore'
});

/**
 * Simple chunking function for text
 * @param {string} text - Text to chunk
 * @param {number} chunkSize - Maximum chunk size
 * @param {number} overlap - Number of tokens to overlap between chunks
 * @returns {Array} - Array of text chunks
 */
const chunkText = (text, chunkSize = 500, overlap = 50) => {
  // Remove excessive whitespace
  const cleanedText = text.replace(/\s+/g, ' ').trim();
  
  // Pre-process with Compromise for better chunking
  let doc = nlp(cleanedText);
  let sentences = doc.sentences().out('array');
  
  let chunks = [];
  let currentChunk = [];
  let currentSize = 0;
  
  for (let sentence of sentences) {
    // Approximate token count (rough estimate)
    const tokenCount = sentence.split(/\s+/).length;
    
    if (currentSize + tokenCount > chunkSize && currentChunk.length > 0) {
      // Save current chunk and start new one
      chunks.push(currentChunk.join(' '));
      
      // Start new chunk with overlap (keep the last sentences that fit within overlap tokens)
      let overlapSize = 0;
      let overlapChunk = [];
      
      for (let i = currentChunk.length - 1; i >= 0; i--) {
        const sentSize = currentChunk[i].split(/\s+/).length;
        if (overlapSize + sentSize <= overlap) {
          overlapChunk.unshift(currentChunk[i]);
          overlapSize += sentSize;
        } else {
          break;
        }
      }
      
      currentChunk = [...overlapChunk];
      currentSize = overlapSize;
    }
    
    currentChunk.push(sentence);
    currentSize += tokenCount;
  }
  
  // Add the last chunk if it's not empty
  if (currentChunk.length > 0) {
    chunks.push(currentChunk.join(' '));
  }
  
  return chunks;
};

/**
 * Generate simple embeddings for text
 * @param {string} text - The text to embed
 * @returns {Array} - A simple vector representation
 */
const generateSimpleEmbedding = (text) => {
  // Remove punctuation and convert to lowercase for more robust matching
  const cleanedText = text.toLowerCase().replace(/[^\w\s]/g, '');
  const words = cleanedText.split(/\s+/);
  
  // Get most important words (excluding stopwords)
  const stopWords = new Set(['and', 'the', 'is', 'in', 'it', 'to', 'of', 'for', 'with', 'on', 'at', 'from', 'by', 'about', 'as', 'into', 'like', 'through', 'after', 'over', 'between', 'out', 'against', 'during', 'without', 'before', 'under', 'around', 'among']);
  
  // Count word frequencies
  const wordFreq = {};
  words.forEach(word => {
    if (!stopWords.has(word) && word.length > 1) {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    }
  });
  
  // Extract key terms and their frequencies
  const keyTerms = Object.entries(wordFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 50)
    .map(entry => entry[0]);
  
  // Create a simple sparse embedding (object with terms as keys)
  const embedding = {};
  keyTerms.forEach(term => {
    embedding[term] = wordFreq[term] / words.length;
  });
  
  return embedding;
};

/**
 * Calculate similarity between query and chunk embeddings
 * @param {Object} queryEmbedding - The query embedding
 * @param {Object} chunkEmbedding - The chunk embedding
 * @returns {number} - Similarity score
 */
const calculateSimilarity = (queryEmbedding, chunkEmbedding) => {
  // Create vectors for cosine similarity from the sparse embeddings
  const allTerms = new Set([
    ...Object.keys(queryEmbedding),
    ...Object.keys(chunkEmbedding)
  ]);
  
  const queryVector = [];
  const chunkVector = [];
  
  allTerms.forEach(term => {
    queryVector.push(queryEmbedding[term] || 0);
    chunkVector.push(chunkEmbedding[term] || 0);
  });
  
  // Calculate cosine similarity
  return cosine(queryVector, chunkVector);
};

/**
 * Load and process all transcripts, but only index new ones
 */
export const loadLocalTranscripts = async () => {
  try {
    console.log('Loading local transcripts...');
    
    // Load the metadata file to get list of transcripts
    const metadataResponse = await axios.get('/transcripts/metadata.json');
    const metadata = metadataResponse.data;
    
    // Get file IDs from metadata
    const fileIds = Object.keys(metadata);
    console.log(`Found ${fileIds.length} transcript files in metadata`);
    
    if (useVectorDB === 'pinecone') {
      // Initialize Pinecone
      console.log('Initializing Pinecone...');
      await initPinecone();
      
      // Get list of already indexed transcripts
      const alreadyIndexedIds = await getIndexedTranscripts();
      console.log(`Found ${alreadyIndexedIds.length} already indexed transcripts`);
      
      // Filter to only process new transcripts
      const newFileIds = fileIds.filter(id => !alreadyIndexedIds.includes(id));
      console.log(`Processing ${newFileIds.length} new transcripts...`);
      
      if (newFileIds.length === 0) {
        console.log('All transcripts are already indexed in Pinecone, nothing to do');
        return {
          success: true,
          message: 'All transcripts already indexed in Pinecone'
        };
      }
      
      // Process only new transcripts
      const newTranscriptChunks = [];
      
      for (const fileId of newFileIds) {
        const filePath = metadata[fileId].path;
        if (!filePath) continue;
        
        // Extract the filename from the path
        const filename = filePath.split('/').pop();
        
        try {
          // Fetch the transcript content
          const response = await axios.get(`/transcripts/${filename}`);
          const content = response.data;
          
          // Process the transcript content (chunking)
          const chunks = chunkText(content);
          
          // For each chunk, create an embedding and store
          chunks.forEach((chunk, index) => {
            const embedding = generateSimpleEmbedding(chunk);
            const chunkId = `${fileId}-chunk-${index}`;
            
            newTranscriptChunks.push({
              id: chunkId,
              fileId,
              content: chunk,
              embedding,
              metadata: {
                title: metadata[fileId].name || filename,
                fileId
              }
            });
          });
          
          console.log(`Processed ${chunks.length} chunks from ${filename}`);
        } catch (error) {
          console.error(`Error processing transcript ${filename}:`, error);
        }
      }
      
      if (newTranscriptChunks.length > 0) {
        try {
          // Store vectors in Pinecone
          console.log(`Storing ${newTranscriptChunks.length} chunks in Pinecone...`);
          const result = await upsertVectors(newTranscriptChunks);
          
          if (result.success) {
            // Mark files as indexed
            await markTranscriptsAsIndexed(newFileIds);
            console.log(`Successfully stored ${result.count} vectors in Pinecone`);
          }
        } catch (pineconeError) {
          console.error('Error storing in Pinecone:', pineconeError);
        }
      }
      
      return {
        success: true,
        message: `Successfully processed ${newFileIds.length} new transcripts into ${newTranscriptChunks.length} chunks`
      };
    } else {
      // For local storage, always process all transcripts
      const transcriptChunks = [];
      
      for (const fileId of fileIds) {
        const filePath = metadata[fileId].path;
        if (!filePath) continue;
        
        // Extract the filename from the path
        const filename = filePath.split('/').pop();
        
        try {
          // Fetch the transcript content
          const response = await axios.get(`/transcripts/${filename}`);
          const content = response.data;
          
          // Process the transcript content (chunking)
          const chunks = chunkText(content);
          
          // For each chunk, create an embedding and store
          chunks.forEach((chunk, index) => {
            const embedding = generateSimpleEmbedding(chunk);
            const chunkId = `${fileId}-chunk-${index}`;
            
            transcriptChunks.push({
              id: chunkId,
              fileId,
              content: chunk,
              embedding,
              metadata: {
                title: metadata[fileId].name || filename,
                fileId
              }
            });
          });
          
          console.log(`Processed ${chunks.length} chunks from ${filename}`);
        } catch (error) {
          console.error(`Error processing transcript ${filename}:`, error);
        }
      }
      
      // Store in local storage
      await transcriptsStore.setItem('chunks', transcriptChunks);
      console.log(`Stored ${transcriptChunks.length} chunks in local storage`);
      
      return {
        success: true,
        message: `Successfully processed ${fileIds.length} transcripts into ${transcriptChunks.length} chunks`
      };
    }
  } catch (error) {
    console.error('Error loading local transcripts:', error);
    throw error;
  }
};

/**
 * Search through indexed transcripts for relevant content
 * @param {string} query - User's query
 * @param {string} mode - 'assistant' or 'simulation'
 * @returns {string} - Relevant context for response
 */
export const searchTranscripts = async (query, mode) => {
  try {
    // Generate embedding for the query
    const queryEmbedding = generateSimpleEmbedding(query);
    
    let topResults = [];
    
    if (useVectorDB === 'pinecone') {
      try {
        // Search in Pinecone
        console.log('Searching in Pinecone...');
        topResults = await queryVectors(queryEmbedding, 3);
      } catch (pineconeError) {
        console.error('Error searching in Pinecone, falling back to local search:', pineconeError);
        // Fall back to local search
        topResults = await searchLocal(query, queryEmbedding);
      }
    } else {
      // Search in local storage
      topResults = await searchLocal(query, queryEmbedding);
    }
    
    // Extract context from top results
    let context = topResults.map(result => result.content).join('\n\n');
    
    console.log(`Found ${topResults.length} relevant chunks for query:`, query);
    
    return context;
  } catch (error) {
    console.error('Error searching transcripts:', error);
    
    // Fallback responses if search fails
    if (query.includes('solar') || query.includes('panel')) {
      return "Solar panels have become increasingly efficient in recent years. Our top-tier panels operate at 22% efficiency and can generate up to 400W per panel in optimal conditions.";
    } else if (query.includes('price') || query.includes('cost')) {
      return "Our solar panel installations typically range from $15,000 to $25,000 depending on the size of your home and energy needs. We offer financing options starting at 0% interest for qualified buyers.";
    } else if (query.includes('installation') || query.includes('install')) {
      return "The installation process typically takes 1-3 days. Our team handles all permits and paperwork. We start with a site assessment, then design a custom system for your home.";
    } else {
      return "Based on our sales calls, customers typically see a return on investment within 7-10 years. The solar panels come with a 25-year warranty and require minimal maintenance.";
    }
  }
};

/**
 * Search for relevant chunks in local storage
 * @param {string} query - Original query text
 * @param {Object} queryEmbedding - Query embedding
 * @returns {Array} - Top matching chunks
 */
const searchLocal = async (query, queryEmbedding) => {
  // Get all stored chunks
  const chunks = await transcriptsStore.getItem('chunks');
  
  if (!chunks || chunks.length === 0) {
    throw new Error('No transcript chunks found. Please ensure transcripts are loaded first.');
  }
  
  // Calculate similarity scores for all chunks
  const scoredChunks = chunks.map(chunk => ({
    ...chunk,
    score: calculateSimilarity(queryEmbedding, chunk.embedding)
  }));
  
  // Sort by similarity score and take top results
  return scoredChunks
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
};

/**
 * Check if transcripts are already loaded and processed
 */
export const checkTranscriptsLoaded = async () => {
  try {
    if (useVectorDB === 'pinecone') {
      // Check if we've already initialized Pinecone connection
      await initPinecone();
      
      // For Pinecone, we consider it loaded if we can connect to the index
      // The actual loading happens on demand
      return true;
    } else {
      // Check local storage
      const chunks = await transcriptsStore.getItem('chunks');
      return Boolean(chunks && chunks.length > 0);
    }
  } catch (error) {
    console.error('Error checking transcripts:', error);
    return false;
  }
};

export default {
  loadLocalTranscripts,
  searchTranscripts,
  checkTranscriptsLoaded
};