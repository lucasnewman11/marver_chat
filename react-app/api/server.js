require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Welcome route
app.get('/api', (req, res) => {
  res.json({ message: 'API server running' });
});

// Routes
app.use('/api/chat', require('./routes/chat'));
app.use('/api/indexing', require('./routes/indexing'));
app.use('/api/google-drive', require('./routes/googleDrive'));

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    message: 'An error occurred on the server',
    error: process.env.NODE_ENV === 'production' ? {} : err
  });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});