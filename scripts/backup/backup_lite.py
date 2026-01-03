#!/usr/bin/env python3
"""
Make Decodables - 数据库备份脚本 (简化版)
每天运行一次，备份到 Cloudflare R2

Usage:
    python backup_lite.py [--dry-run] [--verbose]
"""

import os
import sys
import gzip
import shutil
import logging
import argparse
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# ============ 配置 ============

BACKUP_PREFIX = "backup_prod_"
RETENTION_DAYS = 7
TEMP_DIR = Path("/tmp/db_backup")

# ============ 日志配置 ============

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ 环境变量 ============

def get_env(name: str, required: bool = True) -> str:
    """获取环境变量"""
    value = os.getenv(name)
    if required and not value:
        logger.error(f"环境变量 {name} 未设置")
        sys.exit(1)
    return value or ""

# ============ 工具函数 ============

def find_command(name: str, search_paths: list = None) -> str:
    """查找命令的完整路径"""
    # 常见路径
    default_paths = [
        f"/usr/bin/{name}",
        f"/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/lib/postgresql/17/bin/{name}",
        f"/usr/lib/postgresql/16/bin/{name}",
    ]
    
    paths = (search_paths or []) + default_paths
    
    for path in paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    # 尝试 which 命令
    try:
        result = subprocess.run(
            ["which", name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    # 最后返回命令名称，让系统 PATH 处理
    return name

# ============ 核心函数 ============

def create_temp_dir():
    """创建临时目录"""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"临时目录: {TEMP_DIR}")

def cleanup_temp_dir():
    """清理临时目录"""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        logger.info("已清理临时文件")

def run_pg_dump(database_url: str, output_file: Path) -> int:
    """执行 pg_dump 导出数据库"""
    logger.info("开始导出数据库...")
    
    pg_dump_path = find_command("pg_dump")
    logger.info(f"使用 pg_dump: {pg_dump_path}")
    
    cmd = [
        pg_dump_path,
        database_url,
        "--format=plain",
        "--no-owner",
        "--no-privileges",
    ]
    
    try:
        with open(output_file, 'w') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=600  # 10 分钟超时
            )
        
        if result.returncode != 0:
            logger.error(f"pg_dump 失败: {result.stderr}")
            return 0
        
        size = output_file.stat().st_size
        logger.info(f"pg_dump 完成: {size / 1024 / 1024:.2f} MB")
        return size
        
    except subprocess.TimeoutExpired:
        logger.error("pg_dump 超时")
        return 0
    except Exception as e:
        logger.error(f"pg_dump 错误: {e}")
        return 0

def compress_file(input_file: Path, output_file: Path) -> int:
    """使用 gzip 压缩文件"""
    logger.info("压缩备份文件...")
    
    try:
        with open(input_file, 'rb') as f_in:
            with gzip.open(output_file, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        original_size = input_file.stat().st_size
        compressed_size = output_file.stat().st_size
        reduction = (1 - compressed_size / original_size) * 100
        
        logger.info(f"压缩完成: {compressed_size / 1024 / 1024:.2f} MB ({reduction:.0f}% 压缩率)")
        return compressed_size
        
    except Exception as e:
        logger.error(f"压缩失败: {e}")
        return 0

def encrypt_file(input_file: Path, output_file: Path, passphrase: str) -> int:
    """使用 GPG 对称加密"""
    logger.info("加密备份文件...")
    
    gpg_path = find_command("gpg")
    logger.info(f"使用 gpg: {gpg_path}")
    
    cmd = [
        gpg_path,
        "--symmetric",
        "--cipher-algo", "AES256",
        "--batch",
        "--yes",
        "--passphrase", passphrase,
        "--output", str(output_file),
        str(input_file)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"加密失败: {result.stderr}")
            return 0
        
        size = output_file.stat().st_size
        logger.info(f"加密完成: {size / 1024 / 1024:.2f} MB")
        return size
        
    except FileNotFoundError:
        logger.error(f"加密错误: gpg 命令未找到，尝试路径: {gpg_path}")
        return 0
    except Exception as e:
        logger.error(f"加密错误: {e}")
        return 0

def get_s3_client():
    """创建 S3 客户端 (用于 R2)"""
    return boto3.client(
        's3',
        endpoint_url=get_env('R2_ENDPOINT'),
        aws_access_key_id=get_env('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=get_env('R2_SECRET_ACCESS_KEY')
    )

def upload_to_r2(file_path: Path, object_key: str) -> bool:
    """上传文件到 R2"""
    logger.info(f"上传到 R2: {object_key}")
    
    try:
        s3 = get_s3_client()
        bucket = get_env('R2_BUCKET')
        
        s3.upload_file(str(file_path), bucket, object_key)
        logger.info(f"上传成功: {object_key}")
        return True
        
    except ClientError as e:
        logger.error(f"上传失败: {e}")
        return False

def cleanup_old_backups() -> int:
    """清理超过保留期的旧备份"""
    logger.info(f"清理 {RETENTION_DAYS} 天前的旧备份...")
    
    try:
        s3 = get_s3_client()
        bucket = get_env('R2_BUCKET')
        
        response = s3.list_objects_v2(Bucket=bucket, Prefix=BACKUP_PREFIX)
        
        if 'Contents' not in response:
            logger.info("没有找到旧备份")
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
        deleted_count = 0
        
        for obj in response['Contents']:
            if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                s3.delete_object(Bucket=bucket, Key=obj['Key'])
                logger.info(f"已删除: {obj['Key']}")
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"共清理 {deleted_count} 个旧备份")
        else:
            logger.info("没有需要清理的旧备份")
            
        return deleted_count
        
    except ClientError as e:
        logger.error(f"清理失败: {e}")
        return 0

def calculate_checksum(file_path: Path) -> str:
    """计算文件 SHA256"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description='Make Decodables 数据库备份')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际执行')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    start_time = datetime.now()
    timestamp = start_time.strftime('%Y%m%d_%H%M%S')
    
    logger.info("=" * 50)
    logger.info("Make Decodables 数据库备份开始")
    logger.info("=" * 50)
    
    if args.dry_run:
        logger.info("[DRY RUN] 模拟模式，不会实际执行备份")
        logger.info("[DRY RUN] 检查环境变量...")
        
        env_vars = ['DATABASE_URL', 'R2_ENDPOINT', 'R2_ACCESS_KEY_ID', 
                    'R2_SECRET_ACCESS_KEY', 'R2_BUCKET', 'GPG_PASSPHRASE']
        
        all_set = True
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # 只显示前几个字符
                masked = value[:8] + '...' if len(value) > 8 else value
                logger.info(f"  ✅ {var}: {masked}")
            else:
                logger.error(f"  ❌ {var}: 未设置")
                all_set = False
        
        # 检查命令是否可用
        logger.info("[DRY RUN] 检查命令...")
        pg_dump_path = find_command("pg_dump")
        gpg_path = find_command("gpg")
        logger.info(f"  pg_dump: {pg_dump_path}")
        logger.info(f"  gpg: {gpg_path}")
        
        if all_set:
            logger.info("[DRY RUN] ✅ 所有环境变量已配置")
        else:
            logger.error("[DRY RUN] ❌ 部分环境变量缺失")
            sys.exit(1)
        
        logger.info("[DRY RUN] 完成")
        return
    
    # 获取环境变量
    database_url = get_env('DATABASE_URL')
    gpg_passphrase = get_env('GPG_PASSPHRASE')
    
    # 文件路径
    sql_file = TEMP_DIR / f"{BACKUP_PREFIX}{timestamp}.sql"
    gz_file = TEMP_DIR / f"{BACKUP_PREFIX}{timestamp}.sql.gz"
    gpg_file = TEMP_DIR / f"{BACKUP_PREFIX}{timestamp}.sql.gz.gpg"
    object_key = f"{BACKUP_PREFIX}{timestamp}.sql.gz.gpg"
    
    try:
        # 1. 创建临时目录
        create_temp_dir()
        
        # 2. 导出数据库
        if not run_pg_dump(database_url, sql_file):
            raise Exception("pg_dump 失败")
        
        # 3. 压缩
        if not compress_file(sql_file, gz_file):
            raise Exception("压缩失败")
        
        # 删除原始 SQL 文件，节省空间
        sql_file.unlink()
        
        # 4. 加密
        if not encrypt_file(gz_file, gpg_file, gpg_passphrase):
            raise Exception("加密失败")
        
        # 删除压缩文件
        gz_file.unlink()
        
        # 5. 计算 checksum
        checksum = calculate_checksum(gpg_file)
        logger.info(f"SHA256: {checksum[:16]}...")
        
        # 6. 上传到 R2
        if not upload_to_r2(gpg_file, object_key):
            raise Exception("上传失败")
        
        # 7. 清理旧备份
        cleanup_old_backups()
        
        # 完成
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 50)
        logger.info(f"✅ 备份成功完成！耗时: {duration:.1f}s")
        logger.info(f"   文件: {object_key}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ 备份失败: {e}")
        sys.exit(1)
        
    finally:
        cleanup_temp_dir()

if __name__ == "__main__":
    main()