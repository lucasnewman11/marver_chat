const express = require('express');
const router = express.Router();
const { Anthropic } = require('@anthropic-ai/sdk');

// Initialize chat with specified parameters
router.post('/message', async (req, res) => {
  try {
    const { 
      message, 
      context, 
      mode, 
      anthropicApiKey 
    } = req.body;
    
    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }
    
    if (!anthropicApiKey) {
      return res.status(400).json({ error: 'Anthropic API key is required' });
    }
    
    const anthropic = new Anthropic({
      apiKey: anthropicApiKey
    });
    
    // Set the system prompt based on mode
    let systemPrompt;
    if (mode === 'simulation') {
      systemPrompt = (
        "You are simulating a solar panel salesperson based on real sales call transcripts. " +
        "Maintain the tone, style, objection handling techniques, and approach used in these transcripts. " +
        "Answer as if you are the salesperson in a live call. Use the same language patterns, " +
        "terminology, and conversational approach seen in the transcripts."
      );
    } else {
      systemPrompt = (
        "You are a helpful assistant that provides factual information about solar panels, " +
        "sales processes, and technical specifications. Provide clear, accurate information " +
        "based on the documents available to you."
      );
    }
    
    // Get response from Claude
    const response = await anthropic.messages.create({
      model: "claude-3-7-sonnet-20250219",
      max_tokens: 1000,
      system: systemPrompt,
      messages: [
        { role: "user", content: `Context from documents:\n${context}\n\nUser question: ${message}` }
      ]
    });
    
    res.json({
      message: response.content[0].text
    });
  } catch (error) {
    console.error('Error in chat:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;