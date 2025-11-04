#!/bin/bash

# Trade Analysis Dashboard Setup Script
echo "🏈 Setting up Trade Analysis Dashboard..."

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

# Install root dependencies
echo "📦 Installing root dependencies..."
npm install

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd dashboard/backend
npm install
cd ../..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd dashboard/frontend
npm install
cd ../..

# Create environment files if they don't exist
echo "⚙️ Setting up environment files..."

# Backend .env
if [ ! -f "dashboard/backend/.env" ]; then
    cat > dashboard/backend/.env << ENVEOF
PORT=3001
NODE_ENV=development
CORS_ORIGIN=http://localhost:5173
ENVEOF
    echo "✅ Created backend .env file"
fi

# Frontend .env
if [ ! -f "dashboard/frontend/.env" ]; then
    cat > dashboard/frontend/.env << ENVEOF
VITE_API_BASE_URL=http://localhost:3001/api
ENVEOF
    echo "✅ Created frontend .env file"
fi

# Build the applications
echo "🔨 Building applications..."
npm run build

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📊 To start the dashboard:"
echo "  npm run dev"
echo ""
echo "🌐 The dashboard will be available at:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:3001"
echo ""
echo "📁 Add your CSV files to the pipeline_outputs/ directory:"
echo "  - trades.csv (your trade data)"
echo "  - teams.csv (your team data)"
echo ""
echo "📖 See README.md for detailed usage instructions"
echo ""
echo "Happy trading! 🏈📈"
