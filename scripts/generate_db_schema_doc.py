#!/usr/bin/env python3
"""
生成数据库 Schema 完整文档

从 migrations/v2/ 的 SQL 文件中提取：
- 所有表结构（字段、类型、约束）
- 所有函数签名（参数、返回值）
- 所有视图定义

输出 Markdown 格式，追加到 database-guide.md
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone


def extract_tables_from_sql(sql_content: str, filename: str) -> List[Dict[str, Any]]:
    """提取表结构"""
    tables = []
    
    # 匹配 CREATE TABLE ... (字段定义)
    pattern = r'CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)\s*\((.*?)\);'
    matches = re.findall(pattern, sql_content, re.DOTALL | re.IGNORECASE)
    
    for table_name, fields_str in matches:
        # 解析字段
        lines = [line.strip() for line in fields_str.split('\n') if line.strip()]
        fields = []
        constraints = []
        
        for line in lines:
            # 跳过注释
            if line.startswith('--'):
                continue
            
            # 移除尾部逗号
            line = line.rstrip(',')
            
            # 判断是否是约束
            if line.upper().startswith('CONSTRAINT') or line.upper().startswith('CHECK') or line.upper().startswith('UNIQUE'):
                constraints.append(line)
            else:
                # 提取字段名和类型
                parts = line.split()
                if len(parts) >= 2 and not parts[0].upper() in ['PRIMARY', 'FOREIGN', 'CHECK', 'CONSTRAINT', 'UNIQUE']:
                    field_name = parts[0]
                    field_type = parts[1]
                    # 提取注释（如果有）
                    comment = ''
                    if '--' in line:
                        comment = line.split('--', 1)[1].strip()
                    
                    fields.append({
                        'name': field_name,
                        'type': field_type,
                        'comment': comment,
                        'full': line
                    })
        
        tables.append({
            'name': table_name,
            'fields': fields,
            'constraints': constraints,
            'file': filename
        })
    
    return tables


def extract_functions_from_sql(sql_content: str, filename: str) -> List[Dict[str, Any]]:
    """提取函数定义"""
    functions = []
    
    # 匹配 CREATE OR REPLACE FUNCTION ... RETURNS ...
    pattern = r'CREATE OR REPLACE FUNCTION\s+(\w+)\s*\((.*?)\)\s*RETURNS\s+(.*?)\s+(?:AS|LANGUAGE)'
    matches = re.findall(pattern, sql_content, re.DOTALL | re.IGNORECASE)
    
    for func_name, params_str, returns_str in matches:
        # 清理参数
        params = []
        if params_str.strip():
            for param_line in params_str.split(','):
                param_line = param_line.strip()
                if param_line and not param_line.startswith('--'):
                    params.append(param_line)
        
        functions.append({
            'name': func_name,
            'params': params,
            'returns': returns_str.strip(),
            'file': filename
        })
    
    return functions


def extract_views_from_sql(sql_content: str, filename: str) -> List[Dict[str, Any]]:
    """提取视图定义"""
    views = []
    
    # 匹配 CREATE OR REPLACE VIEW
    pattern = r'CREATE(?:\s+OR REPLACE)?\s+VIEW\s+(\w+)\s+AS'
    matches = re.findall(pattern, sql_content, re.IGNORECASE)
    
    for view_name in matches:
        views.append({
            'name': view_name,
            'file': filename
        })
    
    return views


def generate_markdown_doc() -> str:
    """生成 Markdown 文档"""
    base_dir = Path(__file__).parent.parent
    migrations_dir = base_dir / 'migrations' / 'v2'
    
    sql_files = [
        '01_core_business.sql',
        '02_platform_services.sql',
        '03_infrastructure.sql'
    ]
    
    all_tables = []
    all_functions = []
    all_views = []
    
    # 读取所有 SQL 文件
    for sql_file in sql_files:
        filepath = migrations_dir / sql_file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_tables.extend(extract_tables_from_sql(content, sql_file))
        all_functions.extend(extract_functions_from_sql(content, sql_file))
        all_views.extend(extract_views_from_sql(content, sql_file))
    
    # 生成 Markdown
    md_lines = []
    md_lines.append('')
    md_lines.append('---')
    md_lines.append('')
    md_lines.append('## 附录 A: 数据库对象完整清单')
    md_lines.append('')
    md_lines.append(f'> **自动生成时间**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC')
    md_lines.append('> **生成脚本**: `scripts/generate_db_schema_doc.py`')
    md_lines.append('> **数据源**: `migrations/v2/*.sql`')
    md_lines.append('')
    md_lines.append(f'**统计**: {len(all_tables)} 张表 + {len(all_functions)} 个函数 + {len(all_views)} 个视图 = **{len(all_tables) + len(all_functions) + len(all_views)} 个数据库对象**')
    md_lines.append('')
    
    # 按文件分组
    for sql_file in sql_files:
        file_num = sql_file.split('_')[0]
        if file_num == '01':
            file_title = '核心业务层 (Core Business)'
        elif file_num == '02':
            file_title = '平台服务层 (Platform Services)'
        else:
            file_title = '基础设施层 (Infrastructure)'
        
        md_lines.append(f'### {file_num.upper()}. {file_title}')
        md_lines.append('')
        md_lines.append(f'**文件**: `{sql_file}`')
        md_lines.append('')
        
        # 表
        file_tables = [t for t in all_tables if t['file'] == sql_file]
        if file_tables:
            md_lines.append(f'#### 📋 表 ({len(file_tables)} 张)')
            md_lines.append('')
            
            for table in file_tables:
                md_lines.append(f'##### `{table["name"]}` ({len(table["fields"])} 个字段)')
                md_lines.append('')
                md_lines.append('| 字段名 | 类型 | 说明 |')
                md_lines.append('|--------|------|------|')
                
                for field in table['fields'][:15]:  # 只显示前15个字段，避免文档过长
                    md_lines.append(f'| `{field["name"]}` | {field["type"]} | {field["comment"] or "-"} |')
                
                if len(table['fields']) > 15:
                    md_lines.append(f'| ... | ... | *(共 {len(table["fields"])} 个字段，完整定义见 SQL 文件)* |')
                
                md_lines.append('')
        
        # 函数
        file_functions = [f for f in all_functions if f['file'] == sql_file]
        if file_functions:
            md_lines.append(f'#### ⚙️ 函数 ({len(file_functions)} 个)')
            md_lines.append('')
            
            for func in file_functions:
                param_count = len(func['params'])
                md_lines.append(f'##### `{func["name"]}()` ({param_count} 个参数)')
                md_lines.append('')
                md_lines.append(f'**返回**: `{func["returns"]}`')
                md_lines.append('')
                
                if func['params']:
                    md_lines.append('**参数**:')
                    md_lines.append('```sql')
                    for param in func['params'][:10]:  # 最多显示10个参数
                        md_lines.append(param)
                    if len(func['params']) > 10:
                        md_lines.append(f'... (共 {len(func["params"])} 个参数)')
                    md_lines.append('```')
                    md_lines.append('')
        
        # 视图
        file_views = [v for v in all_views if v['file'] == sql_file]
        if file_views:
            md_lines.append(f'#### 👁️ 视图 ({len(file_views)} 个)')
            md_lines.append('')
            
            for view in file_views:
                md_lines.append(f'- `{view["name"]}`')
            
            md_lines.append('')
        
        md_lines.append('---')
        md_lines.append('')
    
    return '\n'.join(md_lines)


if __name__ == '__main__':
    print('🔍 正在提取数据库对象...')
    
    markdown_content = generate_markdown_doc()
    
    # 写入到临时文件
    output_file = Path(__file__).parent.parent / 'docs' / 'main' / 'DATABASE_SCHEMA_APPENDIX.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f'✅ 已生成文档: {output_file}')
    print(f'📝 包含 {len(markdown_content.splitlines())} 行')
    print('')
    print('📌 下一步：手动将内容追加到 docs/main/database-guide.md 末尾')
