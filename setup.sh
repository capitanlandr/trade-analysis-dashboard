#!/bin/bash

# Trade Analysis Dashboard Setup Script
echo "🚀 Setting up Fantasy Football Dashboard"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    echo "Visit: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd dashboard/frontend && npm install

echo ""
echo "✅ Setup complete! Run 'npm run dev' to start development server"
echo ""
echo "🌐 The dashboard will be available at: http://localhost:5173"
echo ""
echo "📖 See README.md for detailed usage instructions"
