#!/bin/bash
# ===========================================
# Make Decodables - 本地测试运行脚本
# ===========================================
#
# 用法:
#   ./scripts/run_tests.sh              # 运行所有测试
#   ./scripts/run_tests.sh ai           # 只运行 AI 测试
#   ./scripts/run_tests.sh payment      # 只运行支付测试
#   ./scripts/run_tests.sh unit         # 只运行单元测试
#   ./scripts/run_tests.sh quick        # 快速测试（跳过慢速测试）
#
# 特点:
#   - 自动设置 Mock 环境变量
#   - 无需真实 API Key
#   - 支持在不完整环境下运行
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 进入项目根目录
cd "$PROJECT_ROOT"

echo -e "${BLUE}===========================================\n"
echo -e " Make Decodables - Test Runner"
echo -e "\n===========================================${NC}\n"

# ===========================================
# 设置测试环境变量
# ===========================================
export TESTING=true

# AI Services (Mock Keys)
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-mock-key-for-testing}"
export FAL_KEY="${FAL_KEY:-test-fal-key}"
export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-test-dashscope-key}"
export GOOGLE_AI_KEY="${GOOGLE_AI_KEY:-test-google-key}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-test-anthropic-key}"
export XAI_API_KEY="${XAI_API_KEY:-test-xai-key}"

# Supabase (Mock)
export SUPABASE_URL="${SUPABASE_URL:-https://test.supabase.co/}"
export SUPABASE_KEY="${SUPABASE_KEY:-test-supabase-key}"

# Stripe (Mock)
export STRIPE_SECRET_KEY="${STRIPE_SECRET_KEY:-sk_test_mock}"
export STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-whsec_test_mock}"

echo -e "${GREEN}✓ 测试环境变量已设置${NC}\n"

# ===========================================
# 检查 pytest 是否安装
# ===========================================
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠ pytest 未安装，正在安装...${NC}"
    pip install pytest pytest-asyncio pytest-cov
fi

# ===========================================
# 运行测试
# ===========================================
TEST_MODE="${1:-all}"

case "$TEST_MODE" in
    ai)
        echo -e "${BLUE}运行 AI 系统测试...${NC}\n"
        pytest tests/test_ai_base.py tests/test_ai_model_config.py tests/test_ai_canary.py -v --tb=short
        ;;
    
    payment)
        echo -e "${BLUE}运行支付测试...${NC}\n"
        pytest tests/test_payment_service.py -v --tb=short
        ;;
    
    unit)
        echo -e "${BLUE}运行单元测试...${NC}\n"
        pytest tests/test_payment_service.py tests/test_credits_logic.py tests/test_ai_base.py -v --tb=short
        ;;
    
    quick)
        echo -e "${BLUE}快速测试 (跳过慢速测试)...${NC}\n"
        pytest tests/ -v --tb=short -m "not slow"
        ;;
    
    integration)
        echo -e "${BLUE}运行集成测试...${NC}\n"
        pytest tests/api/ tests/services/ -v --tb=short || true
        ;;
    
    coverage)
        echo -e "${BLUE}运行测试并生成覆盖率报告...${NC}\n"
        pytest tests/ -v --tb=short --cov=. --cov-report=html --cov-report=term-missing
        echo -e "\n${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"
        ;;
    
    all)
        echo -e "${BLUE}运行所有测试...${NC}\n"
        
        echo -e "\n${YELLOW}>>> 单元测试${NC}"
        pytest tests/test_payment_service.py tests/test_credits_logic.py -v --tb=short || UNIT_FAILED=1
        
        echo -e "\n${YELLOW}>>> AI 系统测试${NC}"
        pytest tests/test_ai_base.py tests/test_ai_model_config.py tests/test_ai_canary.py -v --tb=short || AI_FAILED=1
        
        echo -e "\n${YELLOW}>>> 集成测试 (允许失败)${NC}"
        pytest tests/api/ tests/services/ -v --tb=short || true
        
        # 汇总结果
        echo -e "\n${BLUE}===========================================\n"
        echo -e " 测试结果汇总"
        echo -e "\n===========================================${NC}\n"
        
        if [ -z "$UNIT_FAILED" ]; then
            echo -e "${GREEN}✓ 单元测试: 通过${NC}"
        else
            echo -e "${RED}✗ 单元测试: 失败${NC}"
        fi
        
        if [ -z "$AI_FAILED" ]; then
            echo -e "${GREEN}✓ AI 系统测试: 通过${NC}"
        else
            echo -e "${RED}✗ AI 系统测试: 失败${NC}"
        fi
        
        echo -e "${YELLOW}ℹ 集成测试: 见上方输出${NC}"
        
        # 如果核心测试失败，返回非零退出码
        if [ -n "$UNIT_FAILED" ] || [ -n "$AI_FAILED" ]; then
            exit 1
        fi
        ;;
    
    *)
        echo -e "${RED}未知测试模式: $TEST_MODE${NC}"
        echo -e "\n用法:"
        echo "  ./scripts/run_tests.sh              # 运行所有测试"
        echo "  ./scripts/run_tests.sh ai           # 只运行 AI 测试"
        echo "  ./scripts/run_tests.sh payment      # 只运行支付测试"
        echo "  ./scripts/run_tests.sh unit         # 只运行单元测试"
        echo "  ./scripts/run_tests.sh quick        # 快速测试"
        echo "  ./scripts/run_tests.sh integration  # 集成测试"
        echo "  ./scripts/run_tests.sh coverage     # 带覆盖率的测试"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✓ 测试完成${NC}\n"
