#!/bin/bash

# RAGFlow Landing Page Setup Script
echo "🚀 Setting up RAGFlow Landing Page with Waitlist Integration"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
npm install

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
npm install
cd ..

# Create environment file for backend
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend environment file..."
    cp backend/env.example backend/.env
    echo "⚠️  Please update backend/.env with your database configuration"
fi

# Check if Docker is installed
if command -v docker &> /dev/null; then
    echo "✅ Docker detected"
    
    # Check if docker-compose is available
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        echo "✅ Docker Compose detected"
        echo "🐳 You can run 'docker-compose up -d' to start the full stack"
    fi
else
    echo "⚠️  Docker not detected. You can still run the frontend and backend separately"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update backend/.env with your RAGFlow database credentials"
echo "2. For development:"
echo "   - Frontend: npm run dev"
echo "   - Backend: cd backend && npm run dev"
echo "3. For production with Docker:"
echo "   - docker-compose up -d"
echo "4. For EC2 deployment:"
echo "   - Configure GitHub Secrets"
echo "   - Push to main branch to trigger deployment"
echo ""
echo "📚 See README.md for detailed documentation"

