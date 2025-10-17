#!/bin/bash

echo "Starting Distributed Log Analyzer..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "Docker is running"
echo ""

# Stop any existing containers
echo "Cleaning up existing containers..."
docker-compose down -v
echo ""

# Build and start services
echo "Building and starting services..."
docker-compose up -d --build
echo ""

# Wait for services to be ready
echo "Waiting for services to initialize..."
echo "This may take 30-60 seconds..."
sleep 15

# Check service health
echo ""
echo "Checking service health..."
echo ""

services=("zookeeper" "kafka" "redis" "spark-master" "spark-worker")

for service in "${services[@]}"; do
    if docker ps | grep -q $service; then
        echo "  [OK] $service is running"
    else
        echo "  [FAIL] $service failed to start"
    fi
done

sleep 15

# Check application services
app_services=("log-generator" "log-processor" "dashboard")

for service in "${app_services[@]}"; do
    if docker ps | grep -q $service; then
        echo "  [OK] $service is running"
    else
        echo "  [FAIL] $service failed to start"
    fi
done

echo ""
echo "System is ready!"
echo ""
echo "Access Points:"
echo "   Dashboard:  http://localhost:8501"
echo "   Spark UI:   http://localhost:8080"
echo ""
echo "Useful Commands:"
echo "   View logs:        docker logs -f log-generator"
echo "   View processor:   docker logs -f log-processor"
echo "   Stop system:      docker-compose down"
echo "   View all logs:    docker-compose logs -f"
echo ""
echo "Open http://localhost:8501 in your browser to see the dashboard!"
echo ""