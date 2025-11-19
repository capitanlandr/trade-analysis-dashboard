#!/bin/bash
# Kill all dev servers and restart fresh

echo "🛑 Killing dev servers on ports 5173, 5174, 3001..."

# Kill processes on common dev ports
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null
lsof -ti:3001 | xargs kill -9 2>/dev/null

echo "✅ Ports cleared"
echo ""
echo "🚀 Starting fresh dev server..."
echo ""

cd "$(dirname "$0")/dashboard"
npm run dev
