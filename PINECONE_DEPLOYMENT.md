# Pinecone Integration Testing Results and AWS Deployment Guide

## Current Status

We have successfully:
- Created a Pinecone index named `sales-simulator` in the `us-east-1-aws` environment
- Verified basic connectivity to the Pinecone API
- Tested the VoyageAI embedding generation API

However, we encountered some issues:
- Connection resets when trying to upsert vectors to or query from Pinecone
- Memory limitations when processing large transcript files

## AWS Deployment Recommendations

### 1. Fix Pinecone Connection Issues

Before deploying to AWS, we recommend:

- Verify Pinecone API access from AWS by running a simple test script on an EC2 instance
- Check if there are IP restrictions or firewall rules blocking connections
- Consider creating a new index specifically for the AWS deployment
- Verify Pinecone service status through their support channels

### 2. Optimize Memory Usage

To handle large document collections:

- Process documents in smaller batches (10-20 at a time)
- Implement streaming for large file reads
- Add checkpointing to track indexing progress
- Consider using AWS Lambda for parallel processing of documents

### 3. Setup Instructions for AWS

1. **EC2 Instance Setup**:
   - Recommend t3.medium or larger for adequate memory
   - Install Node.js 18+ and Python 3.9+
   - Configure environment variables in a `.env` file

2. **Environment Variables**:
   Create a `.env` file with the following variables:
   ```
   REACT_APP_PINECONE_API_KEY=
   REACT_APP_PINECONE_ENVIRONMENT=us-east-1-aws
   REACT_APP_PINECONE_INDEX_NAME=sales-simulator
   REACT_APP_VOYAGE_API_KEY=
   REACT_APP_ANTHROPIC_API_KEY=
   ```

3. **Startup Script**:
   ```bash
   # Install dependencies
   npm install
   cd api && npm install
   cd ..
   
   # Start server with increased memory limit
   NODE_OPTIONS=--max-old-space-size=4096 npm run api &
   npm start
   ```

## Code Modifications Required

1. **Fix VoyageAI API Integration**:
   - Remove `truncate: 'END'` parameter from requests to VoyageAI

2. **Implement Batch Processing**:
   - Modify the indexing logic to process documents in smaller batches
   - Add progress tracking and error recovery

3. **Improve Error Handling**:
   - Add exponential backoff for API requests
   - Implement proper error logging
   - Add circuit breakers for failing services

## Testing Plan for AWS

1. Run the debug script on the AWS instance to verify connectivity:
   ```
   python3 debug_pinecone.py
   ```

2. Test with a small batch of documents first:
   ```
   node test_indexing.js --limit=5
   ```

3. Monitor memory usage during processing:
   ```
   watch -n 1 "ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n 10"
   ```

4. After successful testing, enable full indexing.

## Troubleshooting

If connection issues persist in AWS:
1. Try a different region for Pinecone (e.g., us-west-2-aws)
2. Switch to a managed Pinecone account with dedicated resources
3. Consider running your application directly in the Pinecone VPC
4. As a fallback, implement a local vector database option