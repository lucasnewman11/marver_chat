#!/bin/bash

# Start the API server in the background
cd api
npm start &
API_PID=$!

# Give the API server a moment to start
sleep 2

# Start the frontend
cd ..
npm start

# When the frontend is stopped, also stop the API server
kill $API_PID