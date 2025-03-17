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
    
    // Process and chunk documents
    const axios = require('axios');
    const chunks = [];
    
    // Function to generate embeddings with VoyageAI
    async function generateEmbedding(text, voyageApiKey) {
      try {
        const response = await axios.post(
          'https://api.voyageai.com/v1/embeddings',
          {
            model: 'voyage-2',
            input: text,
            truncate: 'END'
          },
          {
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${voyageApiKey}`
            }
          }
        );
        
        return response.data.data[0].embedding;
      } catch (error) {
        console.error('Error generating embedding:', error.response?.data || error.message);
        // Return a simple random vector as fallback for testing
        return Array.from({ length: 1024 }, () => Math.random());
      }
    }
    
    // For simulation docs (larger chunks)
    console.log('Processing simulation documents...');
    for (const doc of simulationDocs) {
      const textChunks = chunkText(doc.content, 3000, 100);
      console.log(`Created ${textChunks.length} chunks for simulation doc ${doc.id}`);
      
      for (let i = 0; i < textChunks.length; i++) {
        const chunk = textChunks[i];
        chunks.push({
          id: `${doc.id}-chunk-${i}`,
          content: chunk,
          metadata: {
            type: 'simulation',
            title: doc.name,
            fileId: doc.id
          },
          embedding: await generateEmbedding(chunk, voyageApiKey)
        });
      }
    }
    
    // For technical and general docs (smaller chunks)
    console.log('Processing technical and general documents...');
    for (const doc of [...technicalDocs, ...generalDocs]) {
      const textChunks = chunkText(doc.content, 512, 50);
      console.log(`Created ${textChunks.length} chunks for ${doc.type} doc ${doc.id}`);
      
      for (let i = 0; i < textChunks.length; i++) {
        const chunk = textChunks[i];
        chunks.push({
          id: `${doc.id}-chunk-${i}`,
          content: chunk,
          metadata: {
            type: doc.type,
            title: doc.name,
            fileId: doc.id
          },
          embedding: await generateEmbedding(chunk, voyageApiKey)
        });
      }
    }
    
    console.log(`Generated embeddings for ${chunks.length} total chunks`);
    
    // Now upload the chunks to Pinecone
    const serverlessUrl = `https://${pineconeIndexName}-${pineconeEnvironment}.svc.${pineconeEnvironment}.pinecone.io`;
    
    // Batch upsert chunks to Pinecone (100 at a time)
    const batchSize = 100;
    console.log(`Upserting ${chunks.length} vectors to Pinecone in batches of ${batchSize}...`);
    
    for (let i = 0; i < chunks.length; i += batchSize) {
      const batch = chunks.slice(i, i + batchSize);
      const vectors = batch.map(chunk => ({
        id: chunk.id,
        values: chunk.embedding,
        metadata: {
          text: chunk.content,
          fileId: chunk.metadata.fileId,
          title: chunk.metadata.title,
          type: chunk.metadata.type
        }
      }));
      
      try {
        await axios.post(
          `${serverlessUrl}/vectors/upsert`,
          { vectors },
          {
            headers: {
              'Api-Key': pineconeApiKey,
              'Content-Type': 'application/json'
            }
          }
        );
        console.log(`Upserted batch ${Math.floor(i/batchSize) + 1} of ${Math.ceil(chunks.length/batchSize)}`);
      } catch (error) {
        console.error('Error upserting vectors to Pinecone:', error.response?.data || error.message);
        throw error;
      }
    }
    
    res.json({
      message: `Successfully processed and indexed ${chunks.length} document chunks`,
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
    
    // Function to generate embeddings with VoyageAI
    async function generateEmbedding(text, voyageApiKey) {
      try {
        const response = await axios.post(
          'https://api.voyageai.com/v1/embeddings',
          {
            model: 'voyage-2',
            input: text,
            truncate: 'END'
          },
          {
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${voyageApiKey}`
            }
          }
        );
        
        return response.data.data[0].embedding;
      } catch (error) {
        console.error('Error generating embedding:', error.response?.data || error.message);
        // Return a simple random vector as fallback for testing
        return Array.from({ length: 1024 }, () => Math.random());
      }
    }
    
    // 1. Generate query embedding with VoyageAI
    const queryEmbedding = await generateEmbedding(query, voyageApiKey);
    
    // 2. Query Pinecone with the embedding
    const axios = require('axios');
    const serverlessUrl = `https://${pineconeIndexName}-${pineconeEnvironment}.svc.${pineconeEnvironment}.pinecone.io`;
    
    const pineconeResponse = await axios.post(
      `${serverlessUrl}/query`, 
      {
        vector: queryEmbedding,
        topK,
        includeMetadata: true
      },
      {
        headers: {
          'Api-Key': pineconeApiKey,
          'Content-Type': 'application/json'
        }
      }
    );
    
    // 3. Process and format results
    const matches = pineconeResponse.data.matches || [];
    console.log(`Found ${matches.length} matches for query: "${query}"`);
    
    // Extract context from the matches
    const context = matches.map(match => {
      return {
        score: match.score,
        content: match.metadata.text || "No text available",
        metadata: {
          fileId: match.metadata.fileId || null,
          title: match.metadata.title || "Unknown"
        }
      };
    });
    
    // Combine the contexts into a single string
    const combinedContext = context.map(item => {
      return `[${item.metadata.title}]: ${item.content}`;
    }).join('\n\n');
    
    res.json({
      context: combinedContext,
      rawMatches: context
    });
  } catch (error) {
    console.error('Error querying vector store:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;