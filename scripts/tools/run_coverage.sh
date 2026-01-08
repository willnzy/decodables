#!/bin/bash
# 运行测试并生成覆盖率报告
# 用法: ./scripts/run_coverage.sh [module]
# 例如: ./scripts/run_coverage.sh services/db

set -e

MODULE=${1:-"services"}

echo "=== 运行测试覆盖率检查 ==="
echo "目标模块: $MODULE"
echo ""

# 运行测试
python -m pytest tests/ \
    --ignore=tests/test_themes.py \
    --ignore=tests/test_themes_standalone.py \
    --cov=$MODULE \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    -q \
    2>&1 | tee coverage_report.txt

echo ""
echo "=== 覆盖率报告已保存 ==="
echo "- 终端报告: coverage_report.txt"
echo "- HTML 报告: htmlcov/index.html"
