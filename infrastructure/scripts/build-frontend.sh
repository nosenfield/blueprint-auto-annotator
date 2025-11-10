#!/bin/bash
# Build Frontend for Production
# Installs dependencies and builds React app for production

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/../../frontend"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Frontend Build Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}Error: Frontend directory not found: $FRONTEND_DIR${NC}"
    exit 1
fi

cd "$FRONTEND_DIR"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: package.json not found in frontend directory${NC}"
    exit 1
fi

# Step 1: Install dependencies
echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
if [ ! -d "node_modules" ]; then
    npm install
    echo "  ✓ Dependencies installed"
else
    echo "  ✓ Dependencies already installed (skipping)"
fi
echo ""

# Step 2: Build for production
echo -e "${YELLOW}Step 2: Building for production...${NC}"
npm run build

if [ $? -eq 0 ]; then
    echo "  ✓ Build completed successfully"
else
    echo -e "${RED}  ✗ Build failed${NC}"
    exit 1
fi
echo ""

# Step 3: Verify build output
echo -e "${YELLOW}Step 3: Verifying build output...${NC}"
if [ ! -d "dist" ]; then
    echo -e "${RED}  ✗ Build output directory 'dist' not found${NC}"
    exit 1
fi

if [ ! -f "dist/index.html" ]; then
    echo -e "${RED}  ✗ Build output 'dist/index.html' not found${NC}"
    exit 1
fi

echo "  ✓ Build output verified"
echo "  Build directory: $FRONTEND_DIR/dist"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Build output: $FRONTEND_DIR/dist"
echo "Ready for deployment to S3"
echo ""

