#!/usr/bin/env python3
"""
Foliaz - 本地测试运行器 (Python 版本)

用法:
    python scripts/run_tests.py              # 运行所有测试
    python scripts/run_tests.py ai           # 只运行 AI 测试
    python scripts/run_tests.py payment      # 只运行支付测试
    python scripts/run_tests.py unit         # 只运行单元测试
    python scripts/run_tests.py quick        # 快速测试
    python scripts/run_tests.py coverage     # 带覆盖率
    
特点:
    - 自动设置 Mock 环境变量
    - 无需真实 API Key
    - 跨平台 (Windows/Mac/Linux)
"""

import os
import sys
import subprocess
from pathlib import Path

# 颜色支持
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color
    
    @classmethod
    def disable(cls):
        """Windows 不支持 ANSI 颜色时禁用"""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.NC = ''

# Windows 检测
if sys.platform == 'win32':
    try:
        import colorama
        colorama.init()
    except ImportError:
        Colors.disable()


def setup_test_environment():
    """设置测试环境变量"""
    env_vars = {
        # Testing flag
        "TESTING": "true",
        
        # AI Services (Mock Keys)
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "sk-test-mock-key-for-testing"),
        "FAL_KEY": os.environ.get("FAL_KEY", "test-fal-key"),
        "DASHSCOPE_API_KEY": os.environ.get("DASHSCOPE_API_KEY", "test-dashscope-key"),
        "GOOGLE_AI_KEY": os.environ.get("GOOGLE_AI_KEY", "test-google-key"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "test-anthropic-key"),
        "XAI_API_KEY": os.environ.get("XAI_API_KEY", "test-xai-key"),
        
        # Supabase (Mock)
        "SUPABASE_URL": os.environ.get("SUPABASE_URL", "https://test.supabase.co/"),
        "SUPABASE_KEY": os.environ.get("SUPABASE_KEY", "test-supabase-key"),
        
        # Stripe (Mock)
        "STRIPE_SECRET_KEY": os.environ.get("STRIPE_SECRET_KEY", "sk_test_mock"),
        "STRIPE_WEBHOOK_SECRET": os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test_mock"),
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    return env_vars


def run_pytest(args: list, allow_failure: bool = False) -> int:
    """运行 pytest"""
    cmd = [sys.executable, "-m", "pytest"] + args
    print(f"{Colors.BLUE}$ {' '.join(cmd)}{Colors.NC}\n")
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode != 0 and not allow_failure:
        return result.returncode
    return 0


def print_header():
    """打印标题"""
    print(f"""
{Colors.BLUE}===========================================

 Foliaz - Test Runner

==========================================={Colors.NC}
""")


def print_usage():
    """打印用法"""
    print(f"""
{Colors.RED}用法:{Colors.NC}
    python scripts/run_tests.py              # 运行所有测试
    python scripts/run_tests.py ai           # 只运行 AI 测试
    python scripts/run_tests.py payment      # 只运行支付测试
    python scripts/run_tests.py unit         # 只运行单元测试
    python scripts/run_tests.py quick        # 快速测试 (跳过慢速测试)
    python scripts/run_tests.py integration  # 集成测试
    python scripts/run_tests.py coverage     # 带覆盖率的测试
""")


# 项目根目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


def main():
    # 进入项目目录
    os.chdir(PROJECT_ROOT)
    
    print_header()
    
    # 设置环境
    setup_test_environment()
    print(f"{Colors.GREEN}✓ 测试环境变量已设置{Colors.NC}\n")
    
    # 获取测试模式
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    # 定义测试配置
    test_configs = {
        "ai": {
            "name": "AI 系统测试",
            "args": ["tests/test_ai_base.py", "tests/test_ai_model_config.py", "tests/test_ai_canary.py", "-v", "--tb=short"]
        },
        "payment": {
            "name": "支付测试",
            "args": ["tests/test_payment_service.py", "-v", "--tb=short"]
        },
        "unit": {
            "name": "单元测试",
            "args": ["tests/test_payment_service.py", "tests/test_credits_logic.py", "tests/test_ai_base.py", "-v", "--tb=short"]
        },
        "quick": {
            "name": "快速测试",
            "args": ["tests/", "-v", "--tb=short", "-m", "not slow"]
        },
        "integration": {
            "name": "集成测试",
            "args": ["tests/api/", "tests/services/", "-v", "--tb=short"],
            "allow_failure": True
        },
        "coverage": {
            "name": "覆盖率测试",
            "args": ["tests/", "-v", "--tb=short", "--cov=.", "--cov-report=html", "--cov-report=term-missing"]
        },
    }
    
    if mode == "all":
        # 运行所有测试
        results = {}
        
        print(f"\n{Colors.YELLOW}>>> 单元测试{Colors.NC}")
        results["unit"] = run_pytest(test_configs["unit"]["args"]) == 0
        
        print(f"\n{Colors.YELLOW}>>> AI 系统测试{Colors.NC}")
        results["ai"] = run_pytest(test_configs["ai"]["args"]) == 0
        
        print(f"\n{Colors.YELLOW}>>> 集成测试 (允许失败){Colors.NC}")
        run_pytest(test_configs["integration"]["args"], allow_failure=True)
        
        # 汇总结果
        print(f"""
{Colors.BLUE}===========================================

 测试结果汇总

==========================================={Colors.NC}
""")
        
        if results["unit"]:
            print(f"{Colors.GREEN}✓ 单元测试: 通过{Colors.NC}")
        else:
            print(f"{Colors.RED}✗ 单元测试: 失败{Colors.NC}")
        
        if results["ai"]:
            print(f"{Colors.GREEN}✓ AI 系统测试: 通过{Colors.NC}")
        else:
            print(f"{Colors.RED}✗ AI 系统测试: 失败{Colors.NC}")
        
        print(f"{Colors.YELLOW}ℹ 集成测试: 见上方输出{Colors.NC}")
        
        # 返回结果
        if not all(results.values()):
            sys.exit(1)
    
    elif mode in test_configs:
        config = test_configs[mode]
        print(f"{Colors.BLUE}运行 {config['name']}...{Colors.NC}\n")
        result = run_pytest(config["args"], config.get("allow_failure", False))
        
        if config.get("name") == "覆盖率测试":
            print(f"\n{Colors.GREEN}覆盖率报告已生成: htmlcov/index.html{Colors.NC}")
        
        sys.exit(result)
    
    else:
        print(f"{Colors.RED}未知测试模式: {mode}{Colors.NC}")
        print_usage()
        sys.exit(1)
    
    print(f"\n{Colors.GREEN}✓ 测试完成{Colors.NC}\n")


if __name__ == "__main__":
    main()
