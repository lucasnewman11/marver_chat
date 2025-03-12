const express = require('express');
const router = express.Router();
const { PineconeClient } = require('@pinecone-database/pinecone');

// Helper function to initialize Pinecone
const initPinecone = async (apiKey, environment, indexName, dimension = 1024) => {
  const pinecone = new PineconeClient();
  await pinecone.init({
    apiKey,
    environment
  });

  // Check if index exists
  const existingIndexes = await pinecone.listIndexes();
  
  if (!existingIndexes.includes(indexName)) {
    // Create index if it doesn't exist
    await pinecone.createIndex({
      name: indexName,
      dimension,
      metric: 'cosine'
    });
    console.log(`Created new Pinecone index: ${indexName}`);
  }
  
  return pinecone.Index(indexName);
};

// Process documents and create embeddings
router.post('/process', async (req, res) => {
  try {
    const { 
      documents, 
      pineconeApiKey, 
      pineconeEnvironment, 
      pineconeIndexName,
      voyageApiKey
    } = req.body;
    
    if (!documents || !documents.length) {
      return res.status(400).json({ error: 'Documents are required' });
    }
    
    if (!pineconeApiKey || !pineconeEnvironment) {
      return res.status(400).json({ error: 'Pinecone credentials are required' });
    }
    
    if (!voyageApiKey) {
      return res.status(400).json({ error: 'VoyageAI API key is required' });
    }
    
    // Initialize Pinecone
    const index = await initPinecone(
      pineconeApiKey, 
      pineconeEnvironment, 
      pineconeIndexName || 'sales-simulator'
    );
    
    // Group documents by type
    const simulationDocs = documents.filter(doc => doc.type === 'simulation');
    const technicalDocs = documents.filter(doc => doc.type === 'technical');
    const generalDocs = documents.filter(doc => doc.type === 'general');
    
    // Process and chunk documents (simplified version)
    // In a real implementation, this would use proper text chunking and the VoyageAI API
    
    // Simplified example - would be replaced with actual embedding logic
    const chunks = [];
    
    // Add chunking logic here - this would be much more complex in a real implementation
    // For simulation docs (larger chunks)
    simulationDocs.forEach(doc => {
      const textChunks = chunkText(doc.content, 3000, 100);
      textChunks.forEach((chunk, i) => {
        chunks.push({
          id: `${doc.id}-chunk-${i}`,
          text: chunk,
          metadata: {
            type: 'simulation',
            title: doc.name,
            file_id: doc.id
          }
        });
      });
    });
    
    // For technical and general docs (smaller chunks)
    [...technicalDocs, ...generalDocs].forEach(doc => {
      const textChunks = chunkText(doc.content, 512, 50);
      textChunks.forEach((chunk, i) => {
        chunks.push({
          id: `${doc.id}-chunk-${i}`,
          text: chunk,
          metadata: {
            type: doc.type,
            title: doc.name,
            file_id: doc.id
          }
        });
      });
    });
    
    res.json({
      message: `Successfully processed ${chunks.length} document chunks`,
      documentCounts: {
        simulation: simulationDocs.length,
        technical: technicalDocs.length,
        general: generalDocs.length
      },
      chunkCount: chunks.length
    });
  } catch (error) {
    console.error('Error processing documents:', error);
    res.status(500).json({ error: error.message });
  }
});

// Simple text chunking function (not as sophisticated as in LlamaIndex)
function chunkText(text, chunkSize, overlap) {
  const chunks = [];
  let start = 0;
  
  while (start < text.length) {
    const end = Math.min(start + chunkSize, text.length);
    chunks.push(text.substring(start, end));
    start = end - overlap;
  }
  
  return chunks;
}

// Query the vector store
router.post('/query', async (req, res) => {
  try {
    const { 
      query, 
      mode,
      pineconeApiKey, 
      pineconeEnvironment, 
      pineconeIndexName,
      voyageApiKey,
      topK = 5
    } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }
    
    if (!pineconeApiKey || !pineconeEnvironment) {
      return res.status(400).json({ error: 'Pinecone credentials are required' });
    }
    
    if (!voyageApiKey) {
      return res.status(400).json({ error: 'VoyageAI API key is required' });
    }
    
    // Initialize Pinecone
    const index = await initPinecone(
      pineconeApiKey, 
      pineconeEnvironment, 
      pineconeIndexName || 'sales-simulator'
    );
    
    // In a real implementation, this would:
    // 1. Generate query embedding with VoyageAI
    // 2. Query Pinecone with the embedding
    // 3. Apply filters based on mode
    // 4. Return the most relevant document chunks
    
    // Placeholder for now
    const context = "This is placeholder context that would be retrieved from Pinecone.";
    
    res.json({
      context
    });
  } catch (error) {
    console.error('Error querying vector store:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;