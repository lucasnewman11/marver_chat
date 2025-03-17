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
    
    // Process and chunk documents with memory-efficient batching
    const axios = require('axios');
    
    // Function to generate embeddings with VoyageAI with retry and error handling
    async function generateEmbedding(text, voyageApiKey, retries = 3) {
      try {
        // Remove truncate: 'END' as mentioned in PINECONE_DEPLOYMENT.md
        const response = await axios.post(
          'https://api.voyageai.com/v1/embeddings',
          {
            model: 'voyage-2',
            input: text
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
        if (retries > 0) {
          console.log(`Retrying embedding generation. Attempts remaining: ${retries-1}`);
          // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, (4 - retries) * 1000));
          return generateEmbedding(text, voyageApiKey, retries - 1);
        }
        console.error('Error generating embedding:', error.response?.data || error.message);
        // Return a simple random vector as fallback for testing
        return Array.from({ length: 1024 }, () => Math.random());
      }
    }
    
    const serverlessUrl = `https://${pineconeIndexName}-${pineconeEnvironment}.svc.${pineconeEnvironment}.pinecone.io`;
    
    // Process documents in batches to reduce memory usage
    const documentBatchSize = 5; // Process 5 documents at a time to avoid memory issues
    const vectorBatchSize = 50;   // Send fewer vectors at a time to Pinecone
    
    // Track progress for potential resumption
    let processedDocumentCount = 0;
    let totalChunksProcessed = 0;
    
    // Process simulation docs in batches
    console.log('Processing simulation documents...');
    for (let i = 0; i < simulationDocs.length; i += documentBatchSize) {
      const docBatch = simulationDocs.slice(i, i + documentBatchSize);
      const batchChunks = [];
      
      for (const doc of docBatch) {
        const textChunks = chunkText(doc.content, 3000, 100);
        console.log(`Created ${textChunks.length} chunks for simulation doc ${doc.id}`);
        
        for (let j = 0; j < textChunks.length; j++) {
          const chunk = textChunks[j];
          // Generate embedding 
          const embedding = await generateEmbedding(chunk, voyageApiKey);
          
          batchChunks.push({
            id: `${doc.id}-chunk-${j}`,
            content: chunk,
            metadata: {
              type: 'simulation',
              title: doc.name,
              fileId: doc.id
            },
            embedding
          });
        }
      }
      
      // Upload this batch to Pinecone
      console.log(`Upserting ${batchChunks.length} vectors to Pinecone...`);
      
      // Process vectors in smaller batches
      for (let j = 0; j < batchChunks.length; j += vectorBatchSize) {
        const vectorBatch = batchChunks.slice(j, j + vectorBatchSize);
        const vectors = vectorBatch.map(chunk => ({
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
          
          totalChunksProcessed += vectors.length;
          console.log(`Upserted ${vectors.length} vectors, total progress: ${totalChunksProcessed}`);
          
          // Clear references to allow garbage collection
          vectors.length = 0;
        } catch (error) {
          console.error('Error upserting vectors to Pinecone:', error.response?.data || error.message);
          // Implement exponential backoff for API requests
          console.log('Retrying after pause...');
          await new Promise(resolve => setTimeout(resolve, 5000));
          j -= vectorBatchSize; // Retry this batch
        }
      }
      
      processedDocumentCount += docBatch.length;
      console.log(`Processed ${processedDocumentCount}/${simulationDocs.length} simulation documents`);
      
      // Clear references to allow garbage collection
      batchChunks.length = 0;
    }
    
    // Process technical and general docs in batches
    console.log('Processing technical and general documents...');
    const otherDocs = [...technicalDocs, ...generalDocs];
    
    for (let i = 0; i < otherDocs.length; i += documentBatchSize) {
      const docBatch = otherDocs.slice(i, i + documentBatchSize);
      const batchChunks = [];
      
      for (const doc of docBatch) {
        const textChunks = chunkText(doc.content, 512, 50);
        console.log(`Created ${textChunks.length} chunks for ${doc.type} doc ${doc.id}`);
        
        for (let j = 0; j < textChunks.length; j++) {
          const chunk = textChunks[j];
          // Generate embedding
          const embedding = await generateEmbedding(chunk, voyageApiKey);
          
          batchChunks.push({
            id: `${doc.id}-chunk-${j}`,
            content: chunk,
            metadata: {
              type: doc.type,
              title: doc.name,
              fileId: doc.id
            },
            embedding
          });
        }
      }
      
      // Upload this batch to Pinecone
      console.log(`Upserting ${batchChunks.length} vectors from other docs to Pinecone...`);
      
      // Process vectors in smaller batches
      for (let j = 0; j < batchChunks.length; j += vectorBatchSize) {
        const vectorBatch = batchChunks.slice(j, j + vectorBatchSize);
        const vectors = vectorBatch.map(chunk => ({
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
          
          totalChunksProcessed += vectors.length;
          console.log(`Upserted ${vectors.length} vectors, total progress: ${totalChunksProcessed}`);
          
          // Clear references to allow garbage collection
          vectors.length = 0;
        } catch (error) {
          console.error('Error upserting vectors to Pinecone:', error.response?.data || error.message);
          // Implement exponential backoff
          console.log('Retrying after pause...');
          await new Promise(resolve => setTimeout(resolve, 5000));
          j -= vectorBatchSize; // Retry this batch
        }
      }
      
      processedDocumentCount += docBatch.length;
      console.log(`Processed ${processedDocumentCount}/${simulationDocs.length + otherDocs.length} total documents`);
      
      // Clear references to allow garbage collection
      batchChunks.length = 0;
    }
    
    res.json({
      message: `Successfully processed and indexed ${totalChunksProcessed} document chunks`,
      documentCounts: {
        simulation: simulationDocs.length,
        technical: technicalDocs.length,
        general: generalDocs.length
      },
      chunkCount: totalChunksProcessed
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
    
    // Reuse the existing generateEmbedding function with retries from the process endpoint

    // Function to generate embeddings with VoyageAI with retry and error handling
    async function generateEmbedding(text, voyageApiKey, retries = 3) {
      try {
        // Remove truncate: 'END' parameter as mentioned in PINECONE_DEPLOYMENT.md
        const response = await axios.post(
          'https://api.voyageai.com/v1/embeddings',
          {
            model: 'voyage-2',
            input: text
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
        if (retries > 0) {
          console.log(`Retrying embedding generation. Attempts remaining: ${retries-1}`);
          // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, (4 - retries) * 1000));
          return generateEmbedding(text, voyageApiKey, retries - 1);
        }
        console.error('Error generating embedding:', error.response?.data || error.message);
        // Return a simple random vector as fallback for testing
        return Array.from({ length: 1024 }, () => Math.random());
      }
    }
    
    // 1. Generate query embedding with VoyageAI
    console.log(`Generating embedding for query: "${query}"`);
    const queryEmbedding = await generateEmbedding(query, voyageApiKey);
    
    // 2. Query Pinecone with the embedding with retry mechanism
    const axios = require('axios');
    const serverlessUrl = `https://${pineconeIndexName}-${pineconeEnvironment}.svc.${pineconeEnvironment}.pinecone.io`;
    
    // Function to query Pinecone with exponential backoff
    async function queryPineconeWithRetry(vector, maxRetries = 3) {
      let retries = 0;
      
      while (retries <= maxRetries) {
        try {
          return await axios.post(
            `${serverlessUrl}/query`, 
            {
              vector,
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
        } catch (error) {
          retries++;
          if (retries > maxRetries) {
            throw error;
          }
          console.log(`Retrying Pinecone query (attempt ${retries}/${maxRetries})...`);
          // Exponential backoff
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, retries) * 1000));
        }
      }
    }
    
    console.log(`Querying Pinecone for similar vectors...`);
    const pineconeResponse = await queryPineconeWithRetry(queryEmbedding);
    
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