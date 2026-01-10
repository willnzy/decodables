"""
自动生成 field_mappings.py 映射表

从数据库 Schema (v3 migrations) 自动提取所有表的字段，生成映射骨架。

Usage:
    python scripts/tools/generate_field_mappings.py

Output:
    打印所有 60 张表的映射定义（需人工审查后添加到 field_mappings.py）
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# 特殊映射规则
SPECIAL_MAPPINGS = {
    'id': {
        'profiles': 'user_id',
        'projects': 'project_id',
        'assets': 'asset_id',
        'marketplace_listings': 'listing_id',
        'marketplace_purchases': 'purchase_id',
        'credit_transactions': 'transaction_id',
        'credit_purchases': 'purchase_id',
        'experiments': 'experiment_id',
        'feature_flags': 'flag_id',
        'notifications': 'notification_id',
        'campaigns': 'campaign_id',
        'support_tickets': 'ticket_id',
        'support_replies': 'reply_id',
        'daily_themes': 'theme_id',
        'holidays': 'holiday_id',
        'referrals': 'referral_id',
        'generation_tasks': 'task_id',
        'user_generations': 'generation_id',
        'marketplace_reviews': 'review_id',
        'marketplace_reports': 'report_id',
        'content_reports': 'report_id',
        'payment_records': 'payment_id',
        'asset_categories': 'category_id',
        'asset_prompt_templates': 'template_id',
        'page_prompt_templates': 'template_id',
        'onboarding_steps': 'step_id',
        'project_versions': 'version_id',
        'pricing_plans': 'plan_id',
        'user_discounts': 'discount_id',
        'user_price_overrides': 'override_id',
        'system_assets': 'asset_id',
    },
    'key': {
        'system_configs': 'config_key',  # system_configs 使用 key 作为主键
    },
    'user_id': {
        'marketplace_purchases': 'buyer_id',  # 购买表中 user_id → buyer_id
    }
}

def extract_create_table(sql_content: str) -> List[Tuple[str, str]]:
    """提取所有 CREATE TABLE 语句"""
    pattern = r'CREATE TABLE (\w+) \((.*?)\);'
    matches = re.findall(pattern, sql_content, re.DOTALL | re.MULTILINE)
    return matches

def parse_columns(table_definition: str) -> List[Tuple[str, str]]:
    """解析表定义，提取所有列名和类型"""
    columns = []
    seen_columns = set()  # 防止重复
    lines = table_definition.split('\n')

    for line in lines:
        line = line.strip()

        # 跳过注释、约束、空行
        if not line or line.startswith('--') or line.startswith('CONSTRAINT') or line.startswith('CHECK') or line.startswith('FOREIGN') or line.startswith('PRIMARY') or line.startswith('UNIQUE'):
            continue

        # 匹配列定义: column_name TYPE ...
        # 只取第一个单词(列名)和第二个单词(类型),忽略后续的约束
        match = re.match(r'(\w+)\s+([\w\(\),\[\]]+)', line)
        if match:
            col_name = match.group(1)
            col_type = match.group(2)

            # 防止重复添加(CHECK约束可能被误识别)
            if col_name not in seen_columns:
                columns.append((col_name, col_type))
                seen_columns.add(col_name)

    return columns

def generate_mapping(table_name: str, columns: List[Tuple[str, str]]) -> str:
    """生成映射字典定义"""
    mapping_name = f"{table_name.upper()}_DB_TO_DOMAIN"

    lines = [
        f"# ============================================================",
        f"# {table_name} 表",
        f"# ============================================================",
        f"{mapping_name}: Dict[str, str] = {{",
    ]

    for col_name, col_type in columns:
        # 应用特殊映射规则
        domain_field = col_name

        if col_name == 'id' and table_name in SPECIAL_MAPPINGS['id']:
            domain_field = SPECIAL_MAPPINGS['id'][table_name]
        elif col_name == 'user_id' and table_name in SPECIAL_MAPPINGS['user_id']:
            domain_field = SPECIAL_MAPPINGS['user_id'][table_name]
        elif col_name == 'key' and table_name == 'system_configs':
            domain_field = 'config_key'

        # 添加类型注释
        type_comment = get_type_comment(col_type)
        lines.append(f"    '{col_name}': '{domain_field}',  # {type_comment}")

    lines.append("}")
    lines.append("")

    return '\n'.join(lines)

def get_type_comment(col_type: str) -> str:
    """获取类型注释"""
    if 'TEXT' in col_type or 'VARCHAR' in col_type:
        return col_type.split()[0]
    elif 'INTEGER' in col_type or 'INT' in col_type:
        return 'INTEGER'
    elif 'BOOLEAN' in col_type:
        return 'BOOLEAN'
    elif 'TIMESTAMPTZ' in col_type:
        return 'TIMESTAMPTZ'
    elif 'UUID' in col_type:
        return 'UUID'
    elif 'NUMERIC' in col_type:
        return col_type
    elif 'JSONB' in col_type:
        return 'JSONB'
    elif col_type.startswith('TEXT[]'):
        return 'TEXT[]'
    else:
        return col_type

def main():
    # 读取 v3 migration 文件
    migrations_dir = Path(__file__).parent.parent.parent / 'migrations' / 'v3'

    all_tables = {}

    for sql_file in sorted(migrations_dir.glob('*.sql')):
        print(f"# Reading {sql_file.name}...", file=__import__('sys').stderr)
        content = sql_file.read_text()

        tables = extract_create_table(content)
        for table_name, table_def in tables:
            columns = parse_columns(table_def)
            if columns:
                all_tables[table_name] = columns

    print(f"# Found {len(all_tables)} tables", file=__import__('sys').stderr)
    print()

    # 生成映射
    print('"""')
    print('Auto-generated field mappings (PART 2 - 补充映射)')
    print('Generated by: scripts/tools/generate_field_mappings.py')
    print('Date: 2026-01-10')
    print()
    print('⚠️  请人工审查以下映射，特别注意:')
    print('1. user_id vs buyer_id/seller_id/owner_id 等特殊字段')
    print('2. id → {table_name}_id 的转换是否正确')
    print('3. 是否有嵌套路径 (如 balance.monthly)')
    print('"""')
    print()
    print('from typing import Dict')
    print()

    # 按字母顺序生成(生成所有表,包括之前的6张)
    for table_name in sorted(all_tables.keys()):
        columns = all_tables[table_name]
        mapping = generate_mapping(table_name, columns)
        print(mapping)

    print()
    print('# ============================================================')
    print('# 映射统计')
    print('# ============================================================')
    print(f'# 总表数: {len(all_tables)}')
    print(f'# 已有映射: 6 (profiles, credit_transactions, projects, marketplace_listings, marketplace_purchases, system_configs)')
    print(f'# 新增映射: {len(all_tables) - 6}')

if __name__ == '__main__':
    main()
