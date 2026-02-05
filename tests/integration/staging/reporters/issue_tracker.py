"""
Issue Tracker

问题追踪器,用于记录和管理测试发现的问题

@module tests.integration.staging.reporters.issue_tracker
"""

import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum


class IssueStatus(Enum):
    """问题状态"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    VERIFIED = "verified"
    CLOSED = "closed"
    WONT_FIX = "wont_fix"


class IssuePriority(Enum):
    """问题优先级"""
    P0 = "P0"  # Critical - 立即处理
    P1 = "P1"  # High - 尽快处理
    P2 = "P2"  # Medium - 正常处理
    P3 = "P3"  # Low - 有空处理


class IssueCategory(Enum):
    """问题分类"""
    SERVER_ERROR = "server_error"      # 5xx 错误
    AUTH_FAILURE = "auth_failure"      # 认证问题
    PERMISSION_DENIED = "permission_denied"  # 权限问题
    VALIDATION_ERROR = "validation_error"    # 参数验证
    NOT_FOUND = "not_found"            # 资源不存在
    RATE_LIMIT = "rate_limit"          # 限流
    TIMEOUT = "timeout"                # 超时
    SCHEMA_MISMATCH = "schema_mismatch"  # 响应格式错误
    BUSINESS_LOGIC = "business_logic"  # 业务逻辑错误
    SECURITY = "security"              # 安全问题
    UNKNOWN = "unknown"


@dataclass
class Issue:
    """问题记录"""
    issue_id: str
    title: str
    endpoint: str
    method: str
    category: str
    priority: str
    status: str = "open"
    description: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    request_id: Optional[str] = None
    test_id: Optional[str] = None
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    occurrence_count: int = 1
    root_cause: Optional[str] = None
    fix_commit: Optional[str] = None
    fix_notes: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_markdown(self) -> str:
        """生成 Markdown 格式的问题描述"""
        lines = [
            f"# {self.issue_id}: {self.title}",
            "",
            "## 基本信息",
            f"- **发现时间**: {self.first_seen}",
            f"- **最后出现**: {self.last_seen}",
            f"- **出现次数**: {self.occurrence_count}",
            f"- **优先级**: {self.priority}",
            f"- **分类**: {self.category}",
            f"- **状态**: {self.status}",
            "",
            "## 问题描述",
            self.description or "(无描述)",
            "",
            "## 请求信息",
            f"- **接口**: `{self.method} {self.endpoint}`",
            f"- **测试用例**: {self.test_id or 'N/A'}",
            "",
            "## 响应信息",
            f"- **状态码**: {self.response_status or 'N/A'}",
            f"- **Request ID**: {self.request_id or 'N/A'}",
            "",
            "**响应体**:",
            "```json",
            (self.response_body or "N/A")[:1000],
            "```",
            "",
            "## 期望行为",
            self.expected_behavior or "(未定义)",
            "",
            "## 实际行为",
            self.actual_behavior or "(未记录)",
            "",
        ]

        if self.root_cause:
            lines.extend([
                "## 根因分析",
                self.root_cause,
                "",
            ])

        if self.fix_notes:
            lines.extend([
                "## 修复说明",
                self.fix_notes,
                "",
            ])
            if self.fix_commit:
                lines.append(f"**修复提交**: {self.fix_commit}")
                lines.append("")

        return "\n".join(lines)


class IssueTracker:
    """
    问题追踪器

    功能:
    - 自动创建问题记录
    - 去重 (相同问题不重复创建)
    - 问题分类和优先级
    - 生成问题报告
    - 持久化存储

    Usage:
        tracker = IssueTracker(storage_dir="issues/")

        # 记录问题
        issue = tracker.create_issue(
            title="GET /resources 返回 500",
            endpoint="/api/v2/user/resources",
            method="GET",
            category="server_error",
            response_status=500,
            response_body='{"code": "server_error"}',
        )

        # 更新问题状态
        tracker.update_status(issue.issue_id, "in_progress")

        # 保存
        tracker.save()
    """

    def __init__(self, storage_dir: str = "issues"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.issues: Dict[str, Issue] = {}
        self._counter = 0
        self._load_existing()

    def _load_existing(self):
        """加载已有问题"""
        index_file = self.storage_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for issue_data in data.get("issues", []):
                        issue = Issue(**issue_data)
                        self.issues[issue.issue_id] = issue
                    self._counter = data.get("counter", len(self.issues))
            except Exception as e:
                print(f"Warning: Failed to load issues: {e}")

    def _generate_id(self) -> str:
        """生成问题 ID"""
        self._counter += 1
        return f"ISSUE-{self._counter:03d}"

    def _find_existing(self, endpoint: str, method: str, category: str) -> Optional[Issue]:
        """查找已存在的相同问题"""
        for issue in self.issues.values():
            if (issue.endpoint == endpoint and
                issue.method == method and
                issue.category == category and
                issue.status in ["open", "in_progress"]):
                return issue
        return None

    def create_issue(
        self,
        title: str,
        endpoint: str,
        method: str,
        category: str,
        priority: Optional[str] = None,
        description: str = "",
        expected_behavior: str = "",
        actual_behavior: str = "",
        response_status: Optional[int] = None,
        response_body: Optional[str] = None,
        request_id: Optional[str] = None,
        test_id: Optional[str] = None,
    ) -> Issue:
        """
        创建或更新问题

        如果已存在相同问题,则增加出现次数而不是创建新问题

        Returns:
            创建或更新的 Issue 对象
        """
        # Auto-determine priority from category
        if priority is None:
            priority = self._auto_priority(category, response_status)

        # Check for existing issue
        existing = self._find_existing(endpoint, method, category)
        if existing:
            existing.occurrence_count += 1
            existing.last_seen = datetime.now(timezone.utc).isoformat()
            if response_body:
                existing.response_body = response_body
            return existing

        # Create new issue
        issue_id = self._generate_id()
        issue = Issue(
            issue_id=issue_id,
            title=title,
            endpoint=endpoint,
            method=method,
            category=category,
            priority=priority,
            description=description,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            response_status=response_status,
            response_body=response_body[:2000] if response_body else None,
            request_id=request_id,
            test_id=test_id,
        )
        self.issues[issue_id] = issue
        return issue

    def _auto_priority(self, category: str, status_code: Optional[int]) -> str:
        """根据分类和状态码自动确定优先级"""
        if category == "server_error" or (status_code and status_code >= 500):
            return "P0"
        elif category in ["auth_failure", "security"]:
            return "P0"
        elif category in ["permission_denied", "validation_error"]:
            return "P1"
        elif category in ["not_found", "rate_limit"]:
            return "P2"
        else:
            return "P1"

    def update_status(self, issue_id: str, status: str, notes: str = ""):
        """更新问题状态"""
        if issue_id not in self.issues:
            raise ValueError(f"Issue not found: {issue_id}")
        self.issues[issue_id].status = status
        if notes:
            self.issues[issue_id].fix_notes = notes

    def update_root_cause(self, issue_id: str, root_cause: str):
        """更新根因分析"""
        if issue_id not in self.issues:
            raise ValueError(f"Issue not found: {issue_id}")
        self.issues[issue_id].root_cause = root_cause

    def mark_fixed(self, issue_id: str, commit: str, notes: str = ""):
        """标记问题已修复"""
        if issue_id not in self.issues:
            raise ValueError(f"Issue not found: {issue_id}")
        self.issues[issue_id].status = "fixed"
        self.issues[issue_id].fix_commit = commit
        if notes:
            self.issues[issue_id].fix_notes = notes

    def get_open_issues(self) -> List[Issue]:
        """获取所有未解决的问题"""
        return [i for i in self.issues.values() if i.status in ["open", "in_progress"]]

    def get_issues_by_priority(self) -> Dict[str, List[Issue]]:
        """按优先级分组问题"""
        result: Dict[str, List[Issue]] = {"P0": [], "P1": [], "P2": [], "P3": []}
        for issue in self.get_open_issues():
            result[issue.priority].append(issue)
        return result

    def get_issues_by_category(self) -> Dict[str, List[Issue]]:
        """按分类分组问题"""
        result: Dict[str, List[Issue]] = {}
        for issue in self.issues.values():
            if issue.category not in result:
                result[issue.category] = []
            result[issue.category].append(issue)
        return result

    def save(self):
        """保存问题到存储"""
        # Save index
        index_data = {
            "counter": self._counter,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "issues": [issue.to_dict() for issue in self.issues.values()],
        }
        index_file = self.storage_dir / "index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        # Save individual issue files
        for issue in self.issues.values():
            issue_file = self.storage_dir / f"{issue.issue_id}.md"
            with open(issue_file, "w", encoding="utf-8") as f:
                f.write(issue.to_markdown())

    def generate_summary_report(self, output_path: str) -> str:
        """生成问题总结报告"""
        open_issues = self.get_open_issues()
        by_priority = self.get_issues_by_priority()

        lines = [
            "# 问题追踪报告",
            "",
            f"**生成时间**: {datetime.now(timezone.utc).isoformat()}",
            f"**未解决问题**: {len(open_issues)}",
            "",
            "## 按优先级统计",
            "",
            "| 优先级 | 数量 | 状态 |",
            "|--------|------|------|",
        ]

        for priority in ["P0", "P1", "P2", "P3"]:
            count = len(by_priority.get(priority, []))
            status = "🔴 紧急" if priority == "P0" and count > 0 else "✅"
            lines.append(f"| {priority} | {count} | {status} |")

        lines.append("")

        # List P0 issues
        if by_priority.get("P0"):
            lines.append("## P0 问题 (需立即处理)")
            lines.append("")
            for issue in by_priority["P0"]:
                lines.append(f"### {issue.issue_id}: {issue.title}")
                lines.append(f"- 接口: `{issue.method} {issue.endpoint}`")
                lines.append(f"- 状态码: {issue.response_status}")
                lines.append(f"- 出现次数: {issue.occurrence_count}")
                lines.append("")

        # List P1 issues
        if by_priority.get("P1"):
            lines.append("## P1 问题 (尽快处理)")
            lines.append("")
            for issue in by_priority["P1"]:
                lines.append(f"- **{issue.issue_id}**: {issue.title} ({issue.method} {issue.endpoint})")
            lines.append("")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    def print_summary(self):
        """打印问题总结"""
        open_issues = self.get_open_issues()
        by_priority = self.get_issues_by_priority()

        print("\n" + "=" * 60)
        print("📋 问题追踪总结")
        print("=" * 60)
        print(f"未解决问题: {len(open_issues)}")

        for priority in ["P0", "P1", "P2"]:
            issues = by_priority.get(priority, [])
            if issues:
                print(f"\n[{priority}] ({len(issues)})")
                for issue in issues[:3]:
                    print(f"  - {issue.issue_id}: {issue.title}")
                if len(issues) > 3:
                    print(f"  ... 还有 {len(issues) - 3} 个")

        print("=" * 60 + "\n")
