#!/bin/bash
# Start local development server
# Reads from static JSON files (same as production)

# Check if port 5173 is already in use
if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 5173 is already in use!"
    echo ""
    echo "A development server is likely already running at http://localhost:5173"
    echo "Please use that instance instead of starting a new one."
    echo ""
    echo "To stop the existing server, run: kill \$(lsof -t -i:5173)"
    exit 1
fi

cd "$(dirname "$0")/dashboard"
npm run dev
