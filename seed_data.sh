#!/bin/bash

# AI Internal Manager - Sample Data Seeding Script
# This script helps you seed the database with sample data for testing and development.

set -e

echo "🌱 AI Internal Manager - Sample Data Seeding"
echo "=============================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "📋 Checking prerequisites..."

if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

# Check if environment file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "   Please create a .env file with database credentials."
    echo "   You can copy from .env.example and update the values."
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"
echo -e "${GREEN}✓ .env file found${NC}"

# Check if Docker containers are running
echo ""
echo "🐳 Checking Docker services..."

check_service() {
    local name=$1
    local port=$2

    if nc -z localhost $port > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name is running on port $port${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $name is not responding on port $port${NC}"
        return 1
    fi
}

services_ok=true

check_service "PostgreSQL" 5432 || services_ok=false
check_service "Redis" 6379 || services_ok=false
check_service "Neo4j" 7687 || services_ok=false
check_service "Qdrant" 6333 || services_ok=false

if [ "$services_ok" = false ]; then
    echo ""
    echo "📦 Some services are not running. Starting Docker services..."
    cd docker
    docker-compose up -d
    cd ..
    echo ""
    echo "⏳ Waiting for services to be ready..."
    sleep 10
    echo -e "${GREEN}✓ Services started${NC}"
fi

# Check Python and dependencies
echo ""
echo "🐍 Checking Python environment..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 is available${NC}"

# Check if dependencies are installed
python3 -c "import sqlalchemy" 2>/dev/null || {
    echo ""
    echo "📦 Installing Python dependencies..."
    pip install -e ".[dev]"
}

# Run the seed script
echo ""
echo "🌾 Running sample data seeding..."
echo ""

python3 seed_sample_data.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Sample data seeding completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start the backend:   uvicorn src.main:app --reload"
    echo "2. Start the frontend:  cd frontend && npm run dev"
    echo "3. Open in browser:     http://localhost:3000"
    echo ""
    echo "Sample users you can query about:"
    echo "  • alice.chen@company.com - Senior Engineer, Platform"
    echo "  • bob.smith@company.com - Product Manager"
    echo "  • carol.williams@company.com - DevOps Engineer"
    echo "  • david.lee@company.com - Data Scientist"
    echo "  • emma.wilson@company.com - Engineering Manager"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Seeding failed. Check error messages above.${NC}"
    exit 1
fi
