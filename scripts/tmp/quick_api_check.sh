#!/bin/bash
# 快速检查 v1/v2 API 端点对比

echo "=== Payment API ==="
echo "v1 (routers/payment.py):"
grep "@router\." routers/payment.py | sed 's/@router\./  /'

echo -e "\nv2 (api/payment_api.py):"
grep "@router\." api/payment_api.py | sed 's/@router\./  /'

echo -e "\n=== Marketplace API ==="
echo "v1 (routers/marketplace.py):"
grep "@router\." routers/marketplace.py | sed 's/@router\./  /' | head -15

echo -e "\nv2 (api/marketplace_api.py):"
grep "@router\." api/marketplace_api.py | sed 's/@router\./  /' | head -15

echo -e "\n=== Projects API ==="
echo "v1 (routers/projects.py):"
grep "@router\." routers/projects.py | sed 's/@router\./  /' | head -15

echo -e "\nv2 (api/projects_api.py):"
grep "@router\." api/projects_api.py | sed 's/@router\./  /' | head -15
