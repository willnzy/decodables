#!/usr/bin/env python3
"""
对比 v1 (routers/) 和 v2 (api/) 的 API 端点差异

用途:
1. 提取 routers/ 和 api/ 中的所有 API 端点
2. 对比已知的 17 对重复路由
3. 识别缺失的端点
4. 生成功能差异对比表 (Markdown)

依赖:
- Python 3.13+
- 标准库 (ast, pathlib, re)

使用:
    python scripts/compare_v1_v2_apis.py

输出:
- 终端输出对比结果
- 生成 docs/tmp/019-v1-v2-api-comparison.md
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class APIEndpoint:
    """API 端点信息"""
    method: str  # GET, POST, PUT, DELETE, PATCH
    path: str  # /api/marketplace/listings
    function_name: str  # get_listings
    line_number: int  # 行号
    has_auth: bool = False  # 是否需要认证
    params: List[str] = field(default_factory=list)  # 路径参数


@dataclass
class RouteComparison:
    """路由对比结果"""
    v1_file: str
    v2_file: str
    v1_endpoints: List[APIEndpoint]
    v2_endpoints: List[APIEndpoint]
    missing_in_v2: List[APIEndpoint]
    extra_in_v2: List[APIEndpoint]
    priority: str  # P0, P1, P2, P3


class APIExtractor:
    """提取 Python 文件中的 API 端点"""

    HTTP_METHODS = ["get", "post", "put", "delete", "patch", "options", "head"]

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.source = file_path.read_text(encoding="utf-8")
        try:
            self.tree = ast.parse(self.source)
        except SyntaxError as e:
            print(f"⚠️  无法解析 {file_path}: {e}")
            self.tree = None

    def extract_endpoints(self) -> List[APIEndpoint]:
        """提取所有 API 端点"""
        if not self.tree:
            return []

        endpoints = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                endpoint = self._extract_from_function(node)
                if endpoint:
                    endpoints.append(endpoint)

        return endpoints

    def _extract_from_function(self, node: ast.FunctionDef) -> APIEndpoint | None:
        """从函数定义中提取端点信息"""
        # 查找路由装饰器
        for decorator in node.decorator_list:
            endpoint = self._parse_decorator(decorator, node)
            if endpoint:
                return endpoint
        return None

    def _parse_decorator(
        self, decorator: ast.expr, func_node: ast.FunctionDef
    ) -> APIEndpoint | None:
        """解析装饰器获取端点信息"""
        # 情况 1: @router.get("/path")
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            method = decorator.func.attr.lower()
            if method in self.HTTP_METHODS:
                path = self._extract_path(decorator)
                if path:
                    has_auth = self._check_auth(func_node)
                    params = self._extract_params(path)
                    return APIEndpoint(
                        method=method.upper(),
                        path=path,
                        function_name=func_node.name,
                        line_number=func_node.lineno,
                        has_auth=has_auth,
                        params=params,
                    )

        return None

    def _extract_path(self, decorator: ast.Call) -> str | None:
        """提取路径参数"""
        if decorator.args:
            arg = decorator.args[0]
            if isinstance(arg, ast.Constant):
                return arg.value
        return None

    def _check_auth(self, func_node: ast.FunctionDef) -> bool:
        """检查是否需要认证 (通过查找 Depends(get_current_user) 等)"""
        source_lines = self.source.split("\n")
        func_start = func_node.lineno - 1
        func_end = func_node.end_lineno if func_node.end_lineno else func_start + 10

        func_code = "\n".join(source_lines[func_start:func_end])

        auth_patterns = [
            r"get_current_user",
            r"get_current_admin",
            r"verify_token",
            r"require_auth",
        ]

        for pattern in auth_patterns:
            if re.search(pattern, func_code):
                return True

        return False

    def _extract_params(self, path: str) -> List[str]:
        """提取路径参数 (如 {listing_id})"""
        return re.findall(r"\{(\w+)\}", path)


class APIComparator:
    """对比 v1 和 v2 API"""

    # 已知的 17 对重复路由
    KNOWN_PAIRS = [
        ("analytics.py", "analytics_api.py", "🟡"),
        ("campaigns.py", "campaigns_api.py", "🟠"),
        ("config.py", "config_api.py", "🟡"),
        ("export.py", "export_api.py", "🟢"),
        ("generation.py", "generation_api.py", "🔴"),
        ("generations.py", "generations_api.py", "🔴"),
        ("logs.py", "logs_api.py", "🟢"),
        ("marketplace.py", "marketplace_api.py", "🟠"),
        ("payment.py", "payment_api.py", "🔴"),
        ("projects.py", "projects_api.py", "🟠"),
        ("resources.py", "resources_api.py", "🟡"),
        ("support.py", "support_api.py", "🟢"),
        ("tasks.py", "tasks_api.py", "🟡"),
        ("templates.py", "templates_api.py", "🟠"),
        ("themes.py", "themes_api.py", "🟡"),
        ("tools.py", "tools_api.py", "🟢"),
        ("webhooks.py", "webhooks_api.py", "🔴"),
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.routers_dir = project_root / "routers"
        self.api_dir = project_root / "api"

    def compare_all(self) -> List[RouteComparison]:
        """对比所有已知的路由对"""
        comparisons = []

        for v1_file, v2_file, priority in self.KNOWN_PAIRS:
            comparison = self.compare_pair(v1_file, v2_file, priority)
            if comparison:
                comparisons.append(comparison)

        return comparisons

    def compare_pair(
        self, v1_file: str, v2_file: str, priority: str
    ) -> RouteComparison | None:
        """对比一对路由文件"""
        v1_path = self.routers_dir / v1_file
        v2_path = self.api_dir / v2_file

        # 检查文件是否存在
        if not v1_path.exists():
            print(f"⚠️  v1 文件不存在: {v1_path}")
            return None
        if not v2_path.exists():
            print(f"⚠️  v2 文件不存在: {v2_path}")
            return None

        # 提取端点
        v1_extractor = APIExtractor(v1_path)
        v2_extractor = APIExtractor(v2_path)

        v1_endpoints = v1_extractor.extract_endpoints()
        v2_endpoints = v2_extractor.extract_endpoints()

        # 对比差异
        missing, extra = self._find_differences(v1_endpoints, v2_endpoints)

        return RouteComparison(
            v1_file=v1_file,
            v2_file=v2_file,
            v1_endpoints=v1_endpoints,
            v2_endpoints=v2_endpoints,
            missing_in_v2=missing,
            extra_in_v2=extra,
            priority=priority,
        )

    def _find_differences(
        self, v1_endpoints: List[APIEndpoint], v2_endpoints: List[APIEndpoint]
    ) -> Tuple[List[APIEndpoint], List[APIEndpoint]]:
        """查找差异端点"""
        # 创建端点签名集合 (method + path)
        v1_signatures = {(e.method, self._normalize_path(e.path)): e for e in v1_endpoints}
        v2_signatures = {(e.method, self._normalize_path(e.path)): e for e in v2_endpoints}

        # 找出缺失的端点
        missing_keys = set(v1_signatures.keys()) - set(v2_signatures.keys())
        extra_keys = set(v2_signatures.keys()) - set(v1_signatures.keys())

        missing = [v1_signatures[key] for key in missing_keys]
        extra = [v2_signatures[key] for key in extra_keys]

        return missing, extra

    def _normalize_path(self, path: str) -> str:
        """
        标准化路径用于对比
        - 移除 /api/ 或 /api/v2/ 前缀
        - 保留路径参数
        """
        # 移除常见前缀
        for prefix in ["/api/v2/user/", "/api/v2/admin/", "/api/v2/", "/api/"]:
            if path.startswith(prefix):
                path = "/" + path[len(prefix):]
                break

        return path


class MarkdownReportGenerator:
    """生成 Markdown 对比报告"""

    def __init__(self, comparisons: List[RouteComparison]):
        self.comparisons = comparisons

    def generate(self) -> str:
        """生成完整报告"""
        sections = [
            self._generate_header(),
            self._generate_summary(),
            self._generate_priority_groups(),
            self._generate_detailed_comparison(),
            self._generate_conclusion(),
        ]

        return "\n\n".join(sections)

    def _generate_header(self) -> str:
        return """# v1/v2 API 功能差异对比报告

> **生成时间**: 2026-01-08
> **对比对象**: routers/ (v1) vs api/ (v2)
> **对比数量**: 17 对路由

---"""

    def _generate_summary(self) -> str:
        """生成总结"""
        total_v1 = sum(len(c.v1_endpoints) for c in self.comparisons)
        total_v2 = sum(len(c.v2_endpoints) for c in self.comparisons)
        total_missing = sum(len(c.missing_in_v2) for c in self.comparisons)
        total_extra = sum(len(c.extra_in_v2) for c in self.comparisons)

        return f"""## 📊 总体统计

| 指标 | v1 (routers/) | v2 (api/) | 差异 |
|------|---------------|-----------|------|
| **总端点数** | {total_v1} | {total_v2} | {total_v2 - total_v1:+d} |
| **缺失端点** | - | - | {total_missing} ❌ |
| **新增端点** | - | - | {total_extra} ✨ |
| **覆盖率** | 100% | {(total_v2 / total_v1 * 100):.1f}% | - |

**关键发现**:
- ✅ v2 已实现 {total_v2} 个端点
- ❌ v2 缺失 {total_missing} 个端点
- ✨ v2 新增 {total_extra} 个端点

---"""

    def _generate_priority_groups(self) -> str:
        """按优先级分组"""
        priority_map = defaultdict(list)
        for comp in self.comparisons:
            priority_map[comp.priority].append(comp)

        sections = ["## 🎯 优先级分组\n"]

        priority_order = ["🔴", "🟠", "🟡", "🟢"]
        priority_names = {
            "🔴": "P0 - 核心功能 (极高优先级)",
            "🟠": "P1 - 高频功能 (高优先级)",
            "🟡": "P2 - 常用功能 (中优先级)",
            "🟢": "P3 - 低频功能 (低优先级)",
        }

        for priority in priority_order:
            if priority not in priority_map:
                continue

            comps = priority_map[priority]
            sections.append(f"### {priority} {priority_names[priority]}\n")

            sections.append("| 路由对 | v1 端点 | v2 端点 | 缺失 | 新增 | 状态 |")
            sections.append("|--------|---------|---------|------|------|------|")

            for comp in comps:
                v1_count = len(comp.v1_endpoints)
                v2_count = len(comp.v2_endpoints)
                missing_count = len(comp.missing_in_v2)
                extra_count = len(comp.extra_in_v2)

                status = "✅ 完整" if missing_count == 0 else f"❌ 缺 {missing_count}"

                sections.append(
                    f"| {comp.v1_file.replace('.py', '')} | {v1_count} | {v2_count} | "
                    f"{missing_count} | {extra_count} | {status} |"
                )

            sections.append("")

        return "\n".join(sections) + "\n---"

    def _generate_detailed_comparison(self) -> str:
        """生成详细对比"""
        sections = ["## 📋 详细对比\n"]

        for comp in self.comparisons:
            sections.append(f"### {comp.v1_file.replace('.py', '')} (routers/{comp.v1_file} ↔ api/{comp.v2_file})\n")

            # v1 端点列表
            sections.append("#### v1 端点:\n")
            if comp.v1_endpoints:
                sections.append("| 方法 | 路径 | 函数名 | 认证 |")
                sections.append("|------|------|--------|------|")
                for ep in comp.v1_endpoints:
                    auth = "🔒" if ep.has_auth else "🔓"
                    sections.append(f"| {ep.method} | `{ep.path}` | {ep.function_name} | {auth} |")
            else:
                sections.append("(无端点)\n")

            sections.append("")

            # v2 端点列表
            sections.append("#### v2 端点:\n")
            if comp.v2_endpoints:
                sections.append("| 方法 | 路径 | 函数名 | 认证 |")
                sections.append("|------|------|--------|------|")
                for ep in comp.v2_endpoints:
                    auth = "🔒" if ep.has_auth else "🔓"
                    sections.append(f"| {ep.method} | `{ep.path}` | {ep.function_name} | {auth} |")
            else:
                sections.append("(无端点)\n")

            sections.append("")

            # 缺失端点
            if comp.missing_in_v2:
                sections.append(f"#### ❌ v2 缺失的端点 ({len(comp.missing_in_v2)} 个):\n")
                sections.append("| 方法 | 路径 | 函数名 |")
                sections.append("|------|------|--------|")
                for ep in comp.missing_in_v2:
                    sections.append(f"| {ep.method} | `{ep.path}` | {ep.function_name} |")
                sections.append("")

            # 新增端点
            if comp.extra_in_v2:
                sections.append(f"#### ✨ v2 新增的端点 ({len(comp.extra_in_v2)} 个):\n")
                sections.append("| 方法 | 路径 | 函数名 |")
                sections.append("|------|------|--------|")
                for ep in comp.extra_in_v2:
                    sections.append(f"| {ep.method} | `{ep.path}` | {ep.function_name} |")
                sections.append("")

            sections.append("---\n")

        return "\n".join(sections)

    def _generate_conclusion(self) -> str:
        """生成结论"""
        missing_by_priority = defaultdict(int)
        for comp in self.comparisons:
            missing_by_priority[comp.priority] += len(comp.missing_in_v2)

        total_missing = sum(missing_by_priority.values())

        return f"""## 🎯 下一步行动

### Stage 2: 补全缺失端点 (共 {total_missing} 个)

#### 优先级划分:
- 🔴 P0 (核心功能): {missing_by_priority.get("🔴", 0)} 个端点 - **必须先补全**
- 🟠 P1 (高频功能): {missing_by_priority.get("🟠", 0)} 个端点
- 🟡 P2 (常用功能): {missing_by_priority.get("🟡", 0)} 个端点
- 🟢 P3 (低频功能): {missing_by_priority.get("🟢", 0)} 个端点

#### 补全计划:
1. **Day 1-2**: P0 端点 (payment, webhooks, generation)
2. **Day 3-4**: P1 端点 (projects, marketplace, campaigns, templates)
3. **Day 5-7**: P2 + P3 端点 (其余路由)

---

**生成脚本**: scripts/compare_v1_v2_apis.py
**后续步骤**: 查看 docs/tmp/018-phase-9-10-execution-plan.md"""


def main():
    """主函数"""
    print("🔍 开始对比 v1/v2 API 端点...\n")

    project_root = Path(__file__).parent.parent
    comparator = APIComparator(project_root)

    # 对比所有路由对
    print("📂 分析文件中...")
    comparisons = comparator.compare_all()

    # 生成报告
    print("📝 生成对比报告...\n")
    generator = MarkdownReportGenerator(comparisons)
    report = generator.generate()

    # 输出到文件
    output_path = project_root / "docs/tmp/019-v1-v2-api-comparison.md"
    output_path.write_text(report, encoding="utf-8")

    print(f"✅ 对比报告已生成: {output_path}\n")

    # 终端摘要
    total_missing = sum(len(c.missing_in_v2) for c in comparisons)
    total_extra = sum(len(c.extra_in_v2) for c in comparisons)

    print("=" * 60)
    print("📊 对比摘要")
    print("=" * 60)
    print(f"对比路由对数: {len(comparisons)}")
    print(f"v2 缺失端点:  {total_missing} 个 ❌")
    print(f"v2 新增端点:  {total_extra} 个 ✨")
    print("=" * 60)

    if total_missing > 0:
        print(f"\n⚠️  发现 {total_missing} 个缺失端点，需要在 Stage 2 补全")
    else:
        print("\n✅ v2 功能完整，可以直接进入 Stage 3")

    print(f"\n📄 详细报告: {output_path}")


if __name__ == "__main__":
    main()
