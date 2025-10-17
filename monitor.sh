#!/bin/bash

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Distributed Log Analyzer Monitor  ${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

while true; do
    # Get metrics from Redis
    TOTAL_LOGS=$(docker exec redis redis-cli HGET metrics total_logs 2>/dev/null || echo "0")
    ERROR_LOGS=$(docker exec redis redis-cli HGET metrics error_logs 2>/dev/null || echo "0")
    ANOMALIES=$(docker exec redis redis-cli HGET metrics anomalies_detected 2>/dev/null || echo "0")
    
    # Calculate error rate
    if [ "$TOTAL_LOGS" -gt 0 ]; then
        ERROR_RATE=$(echo "scale=2; $ERROR_LOGS * 100 / $TOTAL_LOGS" | bc 2>/dev/null || echo "0.00")
    else
        ERROR_RATE="0.00"
    fi
    
    # Calculate throughput
    THROUGHPUT=$((TOTAL_LOGS / 60))
    
    echo -e "${GREEN}System Metrics${NC}"
    echo "======================================"
    echo -e "  Total Logs:       ${YELLOW}$TOTAL_LOGS${NC}"
    echo -e "  Error Logs:       ${RED}$ERROR_LOGS${NC}"
    echo -e "  Error Rate:       ${RED}${ERROR_RATE}%${NC}"
    echo -e "  Anomalies:        ${RED}$ANOMALIES${NC}"
    echo -e "  Throughput:       ${GREEN}~${THROUGHPUT} logs/sec${NC}"
    echo ""
    
    echo -e "${BLUE}Container Status${NC}"
    echo "======================================"
    
    containers=("kafka" "redis" "spark-master" "spark-worker" "log-generator" "log-processor" "dashboard")
    
    for container in "${containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
            STATS=$(docker stats --no-stream --format "{{.CPUPerc}} {{.MemUsage}}" $container 2>/dev/null)
            CPU=$(echo $STATS | awk '{print $1}')
            MEM=$(echo $STATS | awk '{print $2}')
            
            printf "  %-20s ${GREEN}[RUNNING]${NC}  CPU: %-8s Mem: %s\n" "$container" "$CPU" "$MEM"
        else
            printf "  %-20s ${RED}[STOPPED]${NC}\n" "$container"
        fi
    done
    
    echo ""
    echo -e "${YELLOW}Dashboard: http://localhost:8501${NC}"
    echo -e "${YELLOW}Spark UI:  http://localhost:8080${NC}"
    echo ""
    echo "Press Ctrl+C to exit"
    echo ""
    
    sleep 5
    
    # Clear screen for next update
    tput cuu 25
    tput ed
done
```

**Save**

### Step 3: Create .gitignore

1. **Right-click** on root → **New File**
2. Name it: `.gitignore`
3. **Paste:**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker
.dockerignore

# Logs
*.log

# Redis
dump.rdb

# Spark
metastore_db/
spark-warehouse/
derby.log

# Jupyter
.ipynb_checkpoints/

# Environment
.env
.env.local