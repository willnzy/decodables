#!/usr/bin/env python3
"""
Schema Splitter - 将 refactored_schema_v2.sql 分离为 3 个逻辑文件

输出文件:
1. schema_tables.sql - 表结构定义
2. schema_indexes_functions.sql - 索引和函数
3. schema_data.sql - 初始数据
"""

import re
from pathlib import Path
from typing import List, Tuple

class SchemaSection:
    def __init__(self, name: str):
        self.name = name
        self.lines: List[str] = []

    def add_line(self, line: str):
        self.lines.append(line)

    def get_content(self) -> str:
        return ''.join(self.lines)

def parse_sql_file(file_path: str) -> Tuple[SchemaSection, SchemaSection, SchemaSection]:
    """解析 SQL 文件并分类到 3 个 section"""

    tables_section = SchemaSection("tables")
    indexes_functions_section = SchemaSection("indexes_functions")
    data_section = SchemaSection("data")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 状态机
    current_section = None
    buffer = []
    in_function = False
    in_trigger = False
    in_insert = False
    in_create_table = False

    for i, line in enumerate(lines):
        # 跳过文件头部的注释和 BEGIN/COMMIT (会在每个输出文件中单独添加)
        if i < 30 and (line.startswith('--') or 'BEGIN;' in line or 'SET ' in line):
            continue

        # 检测 CREATE EXTENSION (属于 indexes_functions)
        if 'CREATE EXTENSION' in line:
            current_section = indexes_functions_section
            buffer = [line]
            continue

        # 检测 CREATE FUNCTION (属于 indexes_functions)
        if 'CREATE OR REPLACE FUNCTION' in line or 'CREATE FUNCTION' in line:
            in_function = True
            current_section = indexes_functions_section
            buffer = [line]
            continue

        # 函数结束
        if in_function and ('$$ LANGUAGE plpgsql;' in line or 'END;' in line):
            buffer.append(line)
            # 添加后续的 COMMENT
            if i + 1 < len(lines) and 'COMMENT ON FUNCTION' in lines[i + 1]:
                buffer.append(lines[i + 1])
            current_section.lines.extend(buffer)
            current_section.add_line('\n')
            in_function = False
            buffer = []
            continue

        # 检测 CREATE TABLE
        if re.match(r'^CREATE TABLE ', line):
            in_create_table = True
            current_section = tables_section
            buffer = ['\n', line]
            continue

        # 表定义结束 (遇到分号)
        if in_create_table and ');' in line:
            buffer.append(line)
            buffer.append('\n')
            # 添加后续的 COMMENT ON TABLE/COLUMN (但不包括索引和触发器)
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if next_line.startswith('COMMENT ON TABLE') or next_line.startswith('COMMENT ON COLUMN'):
                    buffer.append(next_line)
                    j += 1
                elif next_line.strip() == '' or next_line.startswith('--'):
                    buffer.append(next_line)
                    j += 1
                else:
                    break

            current_section.lines.extend(buffer)
            in_create_table = False
            buffer = []
            continue

        # 检测 CREATE INDEX
        if re.match(r'^CREATE (UNIQUE )?INDEX', line):
            current_section = indexes_functions_section
            buffer = [line]
            # 添加后续的 COMMENT ON INDEX (如果有)
            if i + 1 < len(lines) and 'COMMENT ON INDEX' in lines[i + 1]:
                buffer.append(lines[i + 1])
            buffer.append('\n')
            current_section.lines.extend(buffer)
            buffer = []
            continue

        # 检测 CREATE TRIGGER
        if re.match(r'^CREATE TRIGGER', line):
            in_trigger = True
            current_section = indexes_functions_section
            buffer = [line]
            continue

        # 触发器结束
        if in_trigger and 'EXECUTE FUNCTION' in line:
            buffer.append(line)
            buffer.append('\n')
            current_section.lines.extend(buffer)
            in_trigger = False
            buffer = []
            continue

        # 检测 ALTER TABLE (属于 tables)
        if re.match(r'^ALTER TABLE', line):
            current_section = tables_section
            buffer = [line]
            # ALTER 可能跨多行
            if ';' in line:
                buffer.append('\n')
                current_section.lines.extend(buffer)
                buffer = []
            continue

        # 检测 INSERT INTO (属于 data)
        if re.match(r'^INSERT INTO', line):
            in_insert = True
            current_section = data_section
            buffer = ['\n', line]
            continue

        # INSERT 结束
        if in_insert and ');' in line:
            buffer.append(line)
            buffer.append('\n')
            current_section.lines.extend(buffer)
            in_insert = False
            buffer = []
            continue

        # 检测 COMMIT (跳过)
        if 'COMMIT;' in line:
            continue

        # 累积当前语句的行
        if buffer:
            buffer.append(line)

    return tables_section, indexes_functions_section, data_section

def write_output_file(section: SchemaSection, output_path: str, header_comment: str):
    """写入输出文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # 文件头
        f.write('-- ============================================================================\n')
        f.write(f'-- {header_comment}\n')
        f.write('-- ============================================================================\n')
        f.write('-- 生成时间: 2026-01-10\n')
        f.write('-- 来源: refactored_schema_v2.sql\n')
        f.write('-- PostgreSQL 版本: 15+\n')
        f.write('-- ============================================================================\n\n')
        f.write('BEGIN;\n\n')

        # 内容
        f.write(section.get_content())

        # 文件尾
        f.write('\nCOMMIT;\n')

def main():
    # 输入文件路径
    base_dir = Path(__file__).parent.parent.parent
    input_file = base_dir / 'migrations' / 'v2' / 'refactored_schema_v2.sql'
    output_dir = base_dir / 'migrations' / 'v2'

    print(f"📖 读取文件: {input_file}")

    # 解析文件
    tables, indexes_functions, data = parse_sql_file(str(input_file))

    # 统计
    print(f"\n📊 分离统计:")
    print(f"  - 表结构: {len(tables.lines)} 行")
    print(f"  - 索引/函数: {len(indexes_functions.lines)} 行")
    print(f"  - 初始数据: {len(data.lines)} 行")

    # 写入文件
    output_files = [
        (tables, output_dir / 'schema_tables.sql', 'Make Decodables - 表结构定义'),
        (indexes_functions, output_dir / 'schema_indexes_functions.sql', 'Make Decodables - 索引和函数'),
        (data, output_dir / 'schema_data.sql', 'Make Decodables - 初始数据'),
    ]

    print(f"\n✍️  写入文件:")
    for section, output_path, header in output_files:
        write_output_file(section, str(output_path), header)
        print(f"  ✅ {output_path.name} ({len(section.lines)} 行)")

    print(f"\n✅ 分离完成！\n")
    print(f"执行顺序:")
    print(f"  1. psql -f schema_tables.sql")
    print(f"  2. psql -f schema_indexes_functions.sql")
    print(f"  3. psql -f schema_data.sql")

if __name__ == '__main__':
    main()
