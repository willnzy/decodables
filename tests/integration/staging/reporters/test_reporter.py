"""
Test Reporter

测试报告生成器,用于生成结构化的测试报告

@module tests.integration.staging.reporters.test_reporter
"""

import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class TestCase:
    """单个测试用例结果"""
    test_id: str
    name: str
    module: str
    passed: bool
    duration_ms: float
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    response_preview: Optional[str] = None


@dataclass
class TestRunSummary:
    """测试运行总结"""
    run_id: str
    timestamp: str
    environment: str
    total: int
    passed: int
    failed: int
    skipped: int
    error: int
    duration_seconds: float
    pass_rate: float = field(init=False)

    def __post_init__(self):
        if self.total > 0:
            self.pass_rate = round(self.passed / self.total * 100, 2)
        else:
            self.pass_rate = 0.0


@dataclass
class FailureDetail:
    """失败详情"""
    test_id: str
    endpoint: str
    method: str
    expected_status: int
    actual_status: int
    error_message: str
    response_body: Optional[str] = None
    category: str = "unknown"
    priority: str = "P1"
    request_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TestReporter:
    """
    测试报告生成器

    功能:
    - 收集测试结果
    - 生成 JSON 报告
    - 生成 Markdown 报告
    - 分类和汇总失败

    Usage:
        reporter = TestReporter(environment="staging")

        # 记录测试结果
        reporter.record_test(TestCase(...))

        # 生成报告
        reporter.generate_json_report("report.json")
        reporter.generate_markdown_report("report.md")
    """

    def __init__(
        self,
        environment: str = "staging",
        run_id: Optional[str] = None,
    ):
        self.environment = environment
        self.run_id = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.utcnow()
        self.test_cases: List[TestCase] = []
        self.failures: List[FailureDetail] = []

    def record_test(self, test_case: TestCase):
        """记录单个测试结果"""
        self.test_cases.append(test_case)

    def record_failure(self, failure: FailureDetail):
        """记录失败详情"""
        self.failures.append(failure)

    def get_summary(self) -> TestRunSummary:
        """获取测试运行总结"""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        passed = sum(1 for tc in self.test_cases if tc.passed)
        failed = sum(1 for tc in self.test_cases if not tc.passed and tc.error_type != "skip")
        skipped = sum(1 for tc in self.test_cases if tc.error_type == "skip")
        error = sum(1 for tc in self.test_cases if tc.error_type == "error")

        return TestRunSummary(
            run_id=self.run_id,
            timestamp=self.start_time.isoformat(),
            environment=self.environment,
            total=len(self.test_cases),
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=error,
            duration_seconds=round(duration, 2),
        )

    def get_failures_by_category(self) -> Dict[str, List[FailureDetail]]:
        """按类别分组失败"""
        categories: Dict[str, List[FailureDetail]] = {}
        for failure in self.failures:
            category = failure.category
            if category not in categories:
                categories[category] = []
            categories[category].append(failure)
        return categories

    def get_failures_by_priority(self) -> Dict[str, List[FailureDetail]]:
        """按优先级分组失败"""
        priorities: Dict[str, List[FailureDetail]] = {"P0": [], "P1": [], "P2": []}
        for failure in self.failures:
            priority = failure.priority
            if priority not in priorities:
                priorities[priority] = []
            priorities[priority].append(failure)
        return priorities

    def generate_json_report(self, output_path: str) -> str:
        """
        生成 JSON 格式报告

        Args:
            output_path: 输出文件路径

        Returns:
            生成的报告路径
        """
        summary = self.get_summary()
        report = {
            "summary": asdict(summary),
            "test_cases": [asdict(tc) for tc in self.test_cases],
            "failures": [asdict(f) for f in self.failures],
            "failures_by_category": {
                cat: [asdict(f) for f in failures]
                for cat, failures in self.get_failures_by_category().items()
            },
        }

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return output_path

    def generate_markdown_report(self, output_path: str) -> str:
        """
        生成 Markdown 格式报告

        Args:
            output_path: 输出文件路径

        Returns:
            生成的报告路径
        """
        summary = self.get_summary()
        lines = []

        # Header
        lines.append(f"# API 测试报告")
        lines.append("")
        lines.append(f"**运行 ID**: {summary.run_id}")
        lines.append(f"**时间**: {summary.timestamp}")
        lines.append(f"**环境**: {summary.environment}")
        lines.append("")

        # Summary
        lines.append("## 总结")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append(f"|------|------|")
        lines.append(f"| 总计 | {summary.total} |")
        lines.append(f"| 通过 | {summary.passed} |")
        lines.append(f"| 失败 | {summary.failed} |")
        lines.append(f"| 跳过 | {summary.skipped} |")
        lines.append(f"| 错误 | {summary.error} |")
        lines.append(f"| 通过率 | {summary.pass_rate}% |")
        lines.append(f"| 耗时 | {summary.duration_seconds}s |")
        lines.append("")

        # Status badge
        if summary.pass_rate == 100:
            status = "✅ 全部通过"
        elif summary.pass_rate >= 90:
            status = "⚠️ 基本通过"
        else:
            status = "❌ 需要关注"
        lines.append(f"**状态**: {status}")
        lines.append("")

        # Failures by priority
        if self.failures:
            lines.append("## 失败详情")
            lines.append("")

            by_priority = self.get_failures_by_priority()

            for priority in ["P0", "P1", "P2"]:
                failures = by_priority.get(priority, [])
                if failures:
                    lines.append(f"### {priority} ({len(failures)})")
                    lines.append("")

                    for f in failures:
                        lines.append(f"#### {f.test_id}")
                        lines.append("")
                        lines.append(f"- **接口**: `{f.method} {f.endpoint}`")
                        lines.append(f"- **期望状态**: {f.expected_status}")
                        lines.append(f"- **实际状态**: {f.actual_status}")
                        lines.append(f"- **分类**: {f.category}")
                        if f.request_id:
                            lines.append(f"- **Request ID**: {f.request_id}")
                        lines.append("")
                        lines.append("**错误信息**:")
                        lines.append("```")
                        lines.append(f.error_message[:500] if f.error_message else "N/A")
                        lines.append("```")
                        lines.append("")

        # All test cases
        lines.append("## 所有测试用例")
        lines.append("")
        lines.append("| 状态 | 模块 | 测试 | 耗时 |")
        lines.append("|------|------|------|------|")

        for tc in self.test_cases:
            status_icon = "✅" if tc.passed else "❌"
            duration = f"{tc.duration_ms:.0f}ms"
            lines.append(f"| {status_icon} | {tc.module} | {tc.name} | {duration} |")

        lines.append("")

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    def print_summary(self):
        """打印简短总结到控制台"""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print(f"📊 测试报告 - {summary.run_id}")
        print("=" * 60)
        print(f"环境: {summary.environment}")
        print(f"总计: {summary.total} | 通过: {summary.passed} | 失败: {summary.failed}")
        print(f"通过率: {summary.pass_rate}% | 耗时: {summary.duration_seconds}s")

        if self.failures:
            print("\n❌ 失败列表:")
            by_priority = self.get_failures_by_priority()
            for priority in ["P0", "P1", "P2"]:
                failures = by_priority.get(priority, [])
                if failures:
                    print(f"\n  [{priority}] ({len(failures)})")
                    for f in failures[:5]:  # Show max 5 per priority
                        print(f"    - {f.method} {f.endpoint}: {f.actual_status}")
                    if len(failures) > 5:
                        print(f"    ... and {len(failures) - 5} more")

        print("=" * 60 + "\n")
