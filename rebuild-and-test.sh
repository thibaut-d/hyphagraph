#!/bin/bash

echo "========================================="
echo "Entity CRUD - Rebuild and Test Script"
echo "========================================="
echo ""

# Step 1: Stop containers
echo "[1/6] Stopping existing containers..."
docker compose -f docker-compose.e2e.yml down
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to stop containers"
    exit 1
fi
echo "✓ Containers stopped"
echo ""

# Step 2: Rebuild frontend
echo "[2/6] Rebuilding frontend container (no cache)..."
docker compose -f docker-compose.e2e.yml build --no-cache web
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build frontend"
    exit 1
fi
echo "✓ Frontend rebuilt"
echo ""

# Step 3: Start services
echo "[3/6] Starting all services..."
docker compose -f docker-compose.e2e.yml up -d
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start services"
    exit 1
fi
echo "✓ Services started"
echo ""

# Step 4: Wait for services
echo "[4/6] Waiting for services to be ready (30 seconds)..."
sleep 30
echo "✓ Wait complete"
echo ""

# Step 5: Verify services
echo "[5/6] Verifying services..."
API_HEALTH=$(curl -s http://localhost:8001/health)
if [[ $API_HEALTH == *"ok"* ]]; then
    echo "✓ API is healthy: $API_HEALTH"
else
    echo "ERROR: API health check failed"
    exit 1
fi

WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001)
if [ "$WEB_STATUS" == "200" ]; then
    echo "✓ Frontend is responding: HTTP $WEB_STATUS"
else
    echo "ERROR: Frontend health check failed: HTTP $WEB_STATUS"
    exit 1
fi
echo ""

# Step 6: Run tests
echo "[6/6] Running entity CRUD tests..."
echo "========================================="
cd e2e
BASE_URL=http://localhost:3001 API_URL=http://localhost:8001 npx playwright test tests/entities/crud.spec.ts

echo ""
echo "========================================="
echo "Test run complete!"
echo "========================================="
