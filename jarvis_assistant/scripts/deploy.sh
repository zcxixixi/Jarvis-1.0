#!/bin/bash
# Jarvis Deployment Script
# Syncs code to Raspberry Pi using rsync

set -e

# Configuration
PI_USER="shumeipai"
PI_HOST="192.168.31.150"
PI_PATH="~/jarvis"
LOCAL_PATH="."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "🚀 Jarvis Deployment Script"
echo "=========================================="

# Check connectivity
echo -e "${YELLOW}📡 Checking Pi connectivity...${NC}"
if ! ping -c 1 -W 2 $PI_HOST > /dev/null 2>&1; then
    echo "❌ Cannot reach Pi at $PI_HOST"
    exit 1
fi
echo -e "${GREEN}✅ Pi is reachable${NC}"

# Sync files
echo -e "${YELLOW}📦 Syncing files to Pi...${NC}"
rsync -avz --progress \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv' \
    --exclude '.venv' \
    --exclude '*.wav' \
    --exclude '*.whl' \
    --exclude '.DS_Store' \
    --exclude '*.MOV' \
    $LOCAL_PATH/ $PI_USER@$PI_HOST:$PI_PATH/

echo -e "${GREEN}✅ Sync complete!${NC}"

# Run tests on Pi
echo -e "${YELLOW}🧪 Running tests on Pi...${NC}"
ssh $PI_USER@$PI_HOST "cd $PI_PATH && bash run_all_tests.sh" || true

echo ""
echo "=========================================="
echo "📋 Deployment Summary"
echo "=========================================="
echo "Target: $PI_USER@$PI_HOST:$PI_PATH"
echo ""
echo "Next steps:"
echo "  ssh $PI_USER@$PI_HOST"
echo "  cd $PI_PATH && python hybrid_jarvis.py"
