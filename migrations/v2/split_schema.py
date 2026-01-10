#!/usr/bin/env python3
"""
SQL Schema 切分脚本
按业务领域将 refactored_schema_v2.sql 切分为 3 个文件
"""

import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

# 业务分类定义
BUSINESS_CATEGORIES = {
    "core_business": {
        "name": "核心业务",
        "description": "用户、积分、项目、素材、市场",
        "tables": [
            "profiles",
            "credit_transactions",
            "credit_purchases",
            "subscription_history",
            "projects",
            "project_versions",
            "assets",
            "asset_categories",
            "system_assets",
            "asset_prompt_templates",
            "marketplace_listings",
            "marketplace_purchases",
            "marketplace_favorites",
            "marketplace_reviews",
            "listing_usages",
            "marketplace_reports",
            "user_generations",
            "generation_tasks",
            "page_prompt_templates",
            "user_discounts",
        ]
    },
    "platform_services": {
        "name": "平台服务",
        "description": "Feature Flag、Analytics、Webhooks、审计、主题、营销",
        "tables": [
            "feature_flags",
            "experiments",
            "experiment_assignments",
            "experiment_results",
            "experiment_exposures",
            "experiment_conversions",
            "analytics_events",
            "analytics_aggregation",
            "user_events",
            "aggregated_stats",
            "activity_logs",
            "ai_usage_daily",
            "clerk_webhook_events",
            "stripe_webhook_events",
            "config_audit_logs",
            "content_reports",
            "system_resource_audit_logs",
            "daily_themes",
            "holidays",
            "campaigns",
            "campaign_participations",
            "campaign_dismissals",
            "notifications",
            "onboarding_steps",
            "user_onboarding_progress",
            "referrals",
            "daily_metrics",
            "monthly_metrics",
        ]
    },
    "infrastructure": {
        "name": "基础设施",
        "description": "配置、日志、支持、管理、支付记录",
        "tables": [
            "system_configs",
            "pricing_plans",
            "pricing_history",
            "user_price_overrides",
            "api_logs",
            "ai_call_logs",
            "scheduled_task_logs",
            "error_logs",
            "support_tickets",
            "support_replies",
            "admin_operations",
            "payment_records",
        ]
    }
}


class SQLSplitter:
    def __init__(self, input_file: str):
        self.input_file = Path(input_file)
        self.content = self.input_file.read_text(encoding='utf-8')
        self.lines = self.content.split('\n')

        # 存储解析结果
        self.table_blocks: Dict[str, List[str]] = {}  # 表名 -> SQL块
        self.functions: List[str] = []  # 函数定义
        self.header_comments: List[str] = []  # 文件头部注释
        self.insert_statements: Dict[str, List[str]] = {}  # 表名 -> INSERT语句
        self.view_blocks: List[str] = []  # 视图定义

    def parse(self):
        """解析SQL文件"""
        current_block = []
        current_table = None
        in_function = False
        in_header = True
        in_insert = False
        insert_table = None

        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.strip()

            # 收集文件头部注释
            if in_header:
                if stripped.startswith('--') or stripped == '':
                    self.header_comments.append(line)
                    i += 1
                    continue
                else:
                    in_header = False

            # 检测 CREATE TABLE
            if re.match(r'^CREATE TABLE\s+(\w+)', stripped, re.IGNORECASE):
                match = re.match(r'^CREATE TABLE\s+(\w+)', stripped, re.IGNORECASE)
                current_table = match.group(1)
                current_block = [line]
                i += 1
                continue

            # 收集表定义块（直到分号结束）
            if current_table:
                current_block.append(line)
                if stripped.endswith(';'):
                    # 继续收集相关的 ALTER TABLE 和索引
                    i += 1
                    while i < len(self.lines):
                        next_line = self.lines[i]
                        next_stripped = next_line.strip()

                        # 跳过空行
                        if next_stripped == '':
                            current_block.append(next_line)
                            i += 1
                            continue

                        # 收集注释
                        if next_stripped.startswith('--'):
                            current_block.append(next_line)
                            i += 1
                            continue

                        # 收集 ALTER TABLE
                        if re.match(rf'^ALTER TABLE\s+{current_table}\b', next_stripped, re.IGNORECASE):
                            current_block.append(next_line)
                            i += 1
                            if next_stripped.endswith(';'):
                                continue
                            else:
                                # 多行 ALTER TABLE
                                while i < len(self.lines):
                                    alter_line = self.lines[i]
                                    current_block.append(alter_line)
                                    i += 1
                                    if alter_line.strip().endswith(';'):
                                        break
                            continue

                        # 收集 CREATE INDEX
                        if re.match(rf'^CREATE\s+(UNIQUE\s+)?INDEX\s+\w+\s+ON\s+{current_table}\b',
                                   next_stripped, re.IGNORECASE):
                            current_block.append(next_line)
                            i += 1
                            if next_stripped.endswith(';'):
                                continue
                            else:
                                # 多行 CREATE INDEX
                                while i < len(self.lines):
                                    idx_line = self.lines[i]
                                    current_block.append(idx_line)
                                    i += 1
                                    if idx_line.strip().endswith(';'):
                                        break
                            continue

                        # 收集 CREATE TRIGGER
                        if re.match(rf'^CREATE\s+TRIGGER\s+\w+', next_stripped, re.IGNORECASE):
                            # 检查是否是当前表的触发器
                            trigger_block = [next_line]
                            i += 1
                            while i < len(self.lines):
                                trigger_line = self.lines[i]
                                trigger_block.append(trigger_line)
                                i += 1
                                if trigger_line.strip().endswith('$$;') or trigger_line.strip().endswith(';'):
                                    break
                            # 检查触发器是否关联当前表
                            trigger_text = '\n'.join(trigger_block)
                            if re.search(rf'\bON\s+{current_table}\b', trigger_text, re.IGNORECASE):
                                current_block.extend(trigger_block)
                            else:
                                # 不是当前表的触发器，放回去
                                i -= len(trigger_block)
                                break
                            continue

                        # 其他情况，表定义结束
                        break

                    # 保存表块
                    self.table_blocks[current_table] = current_block
                    current_table = None
                    current_block = []
                    continue
                else:
                    i += 1
                    continue

            # 检测 CREATE FUNCTION
            if re.match(r'^CREATE\s+(OR\s+REPLACE\s+)?FUNCTION', stripped, re.IGNORECASE):
                function_block = [line]
                i += 1
                in_function = True
                while i < len(self.lines) and in_function:
                    func_line = self.lines[i]
                    function_block.append(func_line)
                    if func_line.strip().endswith('$$;') or \
                       (func_line.strip().endswith(';') and 'LANGUAGE' in func_line.upper()):
                        in_function = False
                    i += 1
                self.functions.append('\n'.join(function_block))
                continue

            # 检测 CREATE VIEW
            if re.match(r'^CREATE\s+(OR\s+REPLACE\s+)?VIEW', stripped, re.IGNORECASE):
                view_block = [line]
                i += 1
                while i < len(self.lines):
                    view_line = self.lines[i]
                    view_block.append(view_line)
                    i += 1
                    if view_line.strip().endswith(';'):
                        break
                self.view_blocks.append('\n'.join(view_block))
                continue

            # 检测 INSERT INTO
            if re.match(r'^INSERT INTO\s+(\w+)', stripped, re.IGNORECASE):
                match = re.match(r'^INSERT INTO\s+(\w+)', stripped, re.IGNORECASE)
                insert_table = match.group(1)
                insert_block = [line]
                i += 1

                # 收集完整的 INSERT 语句
                while i < len(self.lines):
                    insert_line = self.lines[i]
                    insert_block.append(insert_line)
                    i += 1
                    if insert_line.strip().endswith(';'):
                        break

                if insert_table not in self.insert_statements:
                    self.insert_statements[insert_table] = []
                self.insert_statements[insert_table].append('\n'.join(insert_block))
                continue

            i += 1

    def categorize_tables(self) -> Dict[str, List[str]]:
        """将表按业务分类"""
        categorized = defaultdict(list)
        uncategorized = []

        for table_name in self.table_blocks.keys():
            found = False
            for category, config in BUSINESS_CATEGORIES.items():
                if table_name in config["tables"]:
                    categorized[category].append(table_name)
                    found = True
                    break
            if not found:
                uncategorized.append(table_name)

        if uncategorized:
            print(f"⚠️  未分类的表: {uncategorized}")
            # 默认放到 infrastructure
            categorized["infrastructure"].extend(uncategorized)

        return categorized

    def generate_file_header(self, category: str, file_number: int) -> str:
        """生成文件头部"""
        config = BUSINESS_CATEGORIES[category]
        header = [
            "-- ============================================================================",
            f"-- Make Decodables - 数据库架构 (文件 {file_number}/3)",
            "-- ============================================================================",
            f"-- 分类: {config['name']}",
            f"-- 说明: {config['description']}",
            f"-- 执行顺序: 第 {file_number} 个执行",
            "-- 生成时间: 2026-01-10",
            "-- ============================================================================",
            "",
            "-- 开始事务",
            "BEGIN;",
            "",
        ]
        return '\n'.join(header)

    def generate_file_footer(self) -> str:
        """生成文件尾部"""
        footer = [
            "",
            "-- ============================================================================",
            "-- 提交事务",
            "-- ============================================================================",
            "COMMIT;",
            "",
        ]
        return '\n'.join(footer)

    def write_split_files(self):
        """生成切分后的文件"""
        categorized = self.categorize_tables()

        # 生成报告
        report_lines = [
            "# SQL Schema 切分报告",
            "",
            f"**原始文件**: {self.input_file.name}",
            f"**总表数**: {len(self.table_blocks)}",
            f"**总函数数**: {len(self.functions)}",
            f"**总视图数**: {len(self.view_blocks)}",
            f"**生成时间**: 2026-01-10",
            "",
            "## 文件分类",
            "",
        ]

        # 1. 核心业务
        category = "core_business"
        filename = "01_core_business.sql"
        self._write_category_file(filename, category, categorized[category], 1)
        report_lines.extend([
            f"### 文件 1: {filename}",
            f"**分类**: {BUSINESS_CATEGORIES[category]['name']}",
            f"**表数量**: {len(categorized[category])}",
            "**包含的表**:",
            ""
        ])
        for table in sorted(categorized[category]):
            report_lines.append(f"- `{table}`")
        report_lines.append("")

        # 2. 平台服务
        category = "platform_services"
        filename = "02_platform_services.sql"
        self._write_category_file(filename, category, categorized[category], 2)
        report_lines.extend([
            f"### 文件 2: {filename}",
            f"**分类**: {BUSINESS_CATEGORIES[category]['name']}",
            f"**表数量**: {len(categorized[category])}",
            "**包含的表**:",
            ""
        ])
        for table in sorted(categorized[category]):
            report_lines.append(f"- `{table}`")
        report_lines.append("")

        # 3. 基础设施
        category = "infrastructure"
        filename = "03_infrastructure.sql"
        self._write_category_file(filename, category, categorized[category], 3,
                                 include_functions=True, include_views=True,
                                 include_inserts=True)
        report_lines.extend([
            f"### 文件 3: {filename}",
            f"**分类**: {BUSINESS_CATEGORIES[category]['name']}",
            f"**表数量**: {len(categorized[category])}",
            f"**函数数量**: {len(self.functions)}",
            f"**视图数量**: {len(self.view_blocks)}",
            f"**初始数据**: 包含所有 INSERT 语句",
            "**包含的表**:",
            ""
        ])
        for table in sorted(categorized[category]):
            report_lines.append(f"- `{table}`")
        report_lines.append("")

        # 写入报告
        report_path = self.input_file.parent / "SPLIT_REPORT.md"
        report_path.write_text('\n'.join(report_lines), encoding='utf-8')
        print(f"✅ 生成报告: {report_path}")

        return report_lines

    def _write_category_file(self, filename: str, category: str, tables: List[str],
                            file_number: int, include_functions=False,
                            include_views=False, include_inserts=False):
        """写入单个分类文件"""
        output_path = self.input_file.parent / filename

        lines = []

        # 头部
        lines.append(self.generate_file_header(category, file_number))

        # 表列表注释
        lines.append("-- ============================================================================")
        lines.append(f"-- 包含的表 ({len(tables)})")
        lines.append("-- ============================================================================")
        for table in sorted(tables):
            lines.append(f"-- {table}")
        lines.append("")
        lines.append("")

        # 表定义
        for i, table in enumerate(sorted(tables), 1):
            if table in self.table_blocks:
                lines.append("-- ----------------------------------------------------------------------------")
                lines.append(f"-- {i}. {table}")
                lines.append("-- ----------------------------------------------------------------------------")
                lines.append('\n'.join(self.table_blocks[table]))
                lines.append("")
                lines.append("")

        # 函数
        if include_functions and self.functions:
            lines.append("-- ============================================================================")
            lines.append(f"-- 数据库函数 ({len(self.functions)})")
            lines.append("-- ============================================================================")
            lines.append("")
            for i, func in enumerate(self.functions, 1):
                lines.append(f"-- 函数 {i}")
                lines.append(func)
                lines.append("")
                lines.append("")

        # 视图
        if include_views and self.view_blocks:
            lines.append("-- ============================================================================")
            lines.append(f"-- 视图定义 ({len(self.view_blocks)})")
            lines.append("-- ============================================================================")
            lines.append("")
            for i, view in enumerate(self.view_blocks, 1):
                lines.append(f"-- 视图 {i}")
                lines.append(view)
                lines.append("")
                lines.append("")

        # 初始数据
        if include_inserts and self.insert_statements:
            lines.append("-- ============================================================================")
            lines.append("-- 初始数据")
            lines.append("-- ============================================================================")
            lines.append("")
            for table, inserts in sorted(self.insert_statements.items()):
                lines.append(f"-- {table} 表初始数据")
                for insert in inserts:
                    lines.append(insert)
                    lines.append("")

        # 尾部
        lines.append(self.generate_file_footer())

        output_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"✅ 生成文件: {output_path} ({len(tables)} 表)")


def main():
    input_file = "/Users/zhangyi/Code_all/AI-WEB/decodables/migrations/v2/refactored_schema_v2.sql"

    print("=" * 80)
    print("SQL Schema 切分工具")
    print("=" * 80)
    print(f"输入文件: {input_file}")
    print()

    splitter = SQLSplitter(input_file)

    print("正在解析 SQL 文件...")
    splitter.parse()

    print(f"✅ 解析完成:")
    print(f"   - 表: {len(splitter.table_blocks)}")
    print(f"   - 函数: {len(splitter.functions)}")
    print(f"   - 视图: {len(splitter.view_blocks)}")
    print(f"   - INSERT 语句: {sum(len(v) for v in splitter.insert_statements.values())}")
    print()

    print("正在生成切分文件...")
    report = splitter.write_split_files()
    print()

    print("=" * 80)
    print("切分完成!")
    print("=" * 80)
    print()
    print('\n'.join(report))


if __name__ == "__main__":
    main()
