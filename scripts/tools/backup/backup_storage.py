#!/usr/bin/env python3
"""
Foliaz - Supabase Storage 增量备份脚本
每天运行一次，增量备份到 Cloudflare R2 md-storage bucket

功能：
- 增量同步：只传输新增/更新的文件
- 无状态：每次运行自动对比，无需记录上次状态
- 支持 dry-run 模式

Usage:
    python backup_storage.py [--dry-run] [--verbose]
"""

import os
import sys
import logging
import argparse
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
import httpx

# ============ 配置 ============

# 要备份的 Supabase Storage bucket
BUCKETS_TO_BACKUP = ['make-decodables-s', 'make-decodables-u']

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

# ============ Supabase Storage API ============

class SupabaseStorageClient:
    """Supabase Storage REST API 客户端"""
    
    def __init__(self, url: str, service_key: str):
        self.base_url = url.rstrip('/')
        self.service_key = service_key
        self.headers = {
            'Authorization': f'Bearer {service_key}',
            'apikey': service_key
        }
    
    def list_files(self, bucket: str, path: str = '') -> List[Dict]:
        """
        列出 bucket 中指定路径的文件和文件夹
        
        Returns:
            List of {'name': str, 'id': str|None, 'metadata': dict, ...}
            id=None 表示是文件夹
        """
        url = f"{self.base_url}/storage/v1/object/list/{bucket}"
        
        payload = {
            'prefix': path,
            'limit': 1000,
            'offset': 0
        }
        
        all_items = []
        
        with httpx.Client(timeout=60.0) as client:
            while True:
                response = client.post(url, json=payload, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"列出文件失败: {response.status_code} - {response.text}")
                    break
                
                items = response.json()
                if not items:
                    break
                
                all_items.extend(items)
                
                if len(items) < payload['limit']:
                    break
                
                payload['offset'] += payload['limit']
        
        return all_items
    
    def list_all_files_recursive(self, bucket: str, path: str = '') -> List[Dict]:
        """
        递归列出 bucket 中所有文件
        
        Returns:
            List of {'path': str, 'size': int, 'updated_at': str, ...}
        """
        all_files = []
        
        items = self.list_files(bucket, path)
        
        for item in items:
            item_name = item.get('name')
            if not item_name:
                continue
            
            full_path = f"{path}/{item_name}".lstrip('/')
            
            # id 为 None 表示是文件夹
            if item.get('id') is None:
                # 递归遍历子文件夹
                sub_files = self.list_all_files_recursive(bucket, full_path)
                all_files.extend(sub_files)
            else:
                # 是文件，添加到列表
                all_files.append({
                    'path': full_path,
                    'size': item.get('metadata', {}).get('size', 0),
                    'updated_at': item.get('updated_at'),
                    'created_at': item.get('created_at'),
                    'mimetype': item.get('metadata', {}).get('mimetype', '')
                })
        
        return all_files
    
    def download_file(self, bucket: str, path: str) -> Optional[bytes]:
        """下载文件内容"""
        url = f"{self.base_url}/storage/v1/object/{bucket}/{path}"
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"下载失败 {path}: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"下载错误 {path}: {e}")
            return None


# ============ R2 操作 ============

def get_s3_client():
    """创建 S3 客户端 (用于 R2)"""
    return boto3.client(
        's3',
        endpoint_url=get_env('R2_ENDPOINT'),
        aws_access_key_id=get_env('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=get_env('R2_SECRET_ACCESS_KEY')
    )


def list_r2_files(bucket: str, prefix: str = '') -> Dict[str, Dict]:
    """
    列出 R2 bucket 中的所有文件
    
    Returns:
        Dict: {path: {'size': int, 'last_modified': datetime, 'etag': str}}
    """
    s3 = get_s3_client()
    files = {}
    
    paginator = s3.get_paginator('list_objects_v2')
    
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                files[obj['Key']] = {
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                }
    except ClientError as e:
        logger.error(f"列出 R2 文件失败: {e}")
    
    return files


def upload_to_r2(data: bytes, bucket: str, key: str) -> bool:
    """上传文件到 R2"""
    try:
        s3 = get_s3_client()
        s3.upload_fileobj(BytesIO(data), bucket, key)
        return True
    except ClientError as e:
        logger.error(f"上传失败 {key}: {e}")
        return False


# ============ 同步逻辑 ============

def should_sync_file(
    supabase_file: Dict,
    r2_files: Dict[str, Dict],
    r2_key: str
) -> bool:
    """
    判断文件是否需要同步
    
    判断条件：
    1. R2 中不存在 -> 需要同步
    2. 文件大小不同 -> 需要同步
    3. Supabase 更新时间更新 -> 需要同步
    """
    if r2_key not in r2_files:
        return True
    
    r2_file = r2_files[r2_key]
    
    # 检查大小
    if supabase_file.get('size', 0) != r2_file.get('size', 0):
        return True
    
    # 检查更新时间
    supabase_updated = supabase_file.get('updated_at')
    if supabase_updated:
        try:
            # Supabase 返回的时间格式: 2026-01-05T10:30:00.000Z
            sb_time = datetime.fromisoformat(supabase_updated.replace('Z', '+00:00'))
            r2_time = r2_files[r2_key]['last_modified']
            
            # 如果 Supabase 更新时间晚于 R2，需要同步
            if sb_time > r2_time:
                return True
        except Exception:
            pass
    
    return False


def sync_bucket(
    supabase_client: SupabaseStorageClient,
    supabase_bucket: str,
    r2_bucket: str,
    dry_run: bool = False
) -> Dict:
    """
    同步单个 Supabase bucket 到 R2
    
    Args:
        supabase_client: Supabase Storage 客户端
        supabase_bucket: Supabase bucket 名称
        r2_bucket: R2 bucket 名称
        dry_run: 是否只预览不执行
    
    Returns:
        同步统计信息
    """
    logger.info(f"📦 开始同步 bucket: {supabase_bucket}")
    
    # R2 中的前缀（保持 bucket 名称作为顶级目录）
    r2_prefix = f"{supabase_bucket}/"
    
    # 1. 列出 Supabase 中的所有文件
    logger.info("  📋 扫描 Supabase Storage...")
    supabase_files = supabase_client.list_all_files_recursive(supabase_bucket)
    logger.info(f"  找到 {len(supabase_files)} 个文件")
    
    # 2. 列出 R2 中对应目录的文件
    logger.info("  📋 扫描 R2...")
    r2_files = list_r2_files(r2_bucket, r2_prefix)
    logger.info(f"  R2 中已有 {len(r2_files)} 个文件")
    
    # 3. 对比并同步
    stats = {
        'total': len(supabase_files),
        'synced': 0,
        'skipped': 0,
        'failed': 0,
        'bytes_transferred': 0
    }
    
    for file_info in supabase_files:
        file_path = file_info['path']
        r2_key = f"{supabase_bucket}/{file_path}"
        
        if should_sync_file(file_info, r2_files, r2_key):
            if dry_run:
                logger.info(f"  [DRY RUN] 需要同步: {file_path}")
                stats['synced'] += 1
            else:
                # 下载并上传
                data = supabase_client.download_file(supabase_bucket, file_path)
                if data:
                    if upload_to_r2(data, r2_bucket, r2_key):
                        logger.info(f"  ✅ 已同步: {file_path} ({len(data)} bytes)")
                        stats['synced'] += 1
                        stats['bytes_transferred'] += len(data)
                    else:
                        stats['failed'] += 1
                else:
                    stats['failed'] += 1
        else:
            stats['skipped'] += 1
    
    logger.info(f"  📊 Bucket {supabase_bucket} 统计:")
    logger.info(f"     总文件: {stats['total']}")
    logger.info(f"     已同步: {stats['synced']}")
    logger.info(f"     已跳过: {stats['skipped']}")
    if stats['failed'] > 0:
        logger.info(f"     失败: {stats['failed']}")
    if stats['bytes_transferred'] > 0:
        logger.info(f"     传输: {stats['bytes_transferred'] / 1024 / 1024:.2f} MB")
    
    return stats


# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description='Foliaz Storage 增量备份')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际执行')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    start_time = datetime.now(timezone.utc)
    
    logger.info("=" * 50)
    logger.info("Foliaz Storage 增量备份开始")
    logger.info("=" * 50)
    
    if args.dry_run:
        logger.info("[DRY RUN] 模拟模式，不会实际传输文件")
    
    # 检查环境变量
    supabase_url = get_env('SUPABASE_URL')
    supabase_key = get_env('SUPABASE_SERVICE_ROLE_KEY')
    r2_bucket = get_env('R2_STORAGE_BUCKET')
    
    # 创建 Supabase 客户端
    supabase_client = SupabaseStorageClient(supabase_url, supabase_key)
    
    # 同步所有 bucket
    total_stats = {
        'total': 0,
        'synced': 0,
        'skipped': 0,
        'failed': 0,
        'bytes_transferred': 0
    }
    
    for bucket in BUCKETS_TO_BACKUP:
        try:
            stats = sync_bucket(supabase_client, bucket, r2_bucket, args.dry_run)
            
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)
                
        except Exception as e:
            logger.error(f"❌ 同步 bucket {bucket} 失败: {e}")
            total_stats['failed'] += 1
    
    # 完成
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    logger.info("=" * 50)
    logger.info("📊 总计统计:")
    logger.info(f"   总文件: {total_stats['total']}")
    logger.info(f"   已同步: {total_stats['synced']}")
    logger.info(f"   已跳过: {total_stats['skipped']}")
    if total_stats['failed'] > 0:
        logger.info(f"   失败: {total_stats['failed']}")
    if total_stats['bytes_transferred'] > 0:
        logger.info(f"   传输: {total_stats['bytes_transferred'] / 1024 / 1024:.2f} MB")
    logger.info(f"   耗时: {duration:.1f}s")
    logger.info("=" * 50)
    
    if total_stats['failed'] > 0:
        logger.error("❌ 部分文件同步失败")
        sys.exit(1)
    else:
        if args.dry_run:
            logger.info("✅ [DRY RUN] 检查完成")
        else:
            logger.info("✅ Storage 备份成功完成！")


if __name__ == "__main__":
    main()
