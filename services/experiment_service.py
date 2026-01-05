"""
A/B Testing Experiment Service
A/B 测试实验服务

Features:
- 实验 CRUD 操作
- 确定性变体分配
- 曝光和转化追踪
- 结果聚合
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
import threading

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if SUPABASE_URL and not SUPABASE_URL.endswith('/'):
    SUPABASE_URL = SUPABASE_URL + '/'

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# In-memory cache for active experiments
_experiment_cache: Dict[str, Dict] = {}
_cache_timestamp: Dict[str, datetime] = {}
_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = 60  # 60s TTL

# ==========================================
# Experiment CRUD Operations
# ==========================================

def create_experiment(
    experiment_key: str,
    name: str,
    variants: List[Dict],
    description: str = None,
    experiment_type: str = "ab",
    targeting: Dict = None,
    traffic_allocation: int = 100,
    metrics: List[Dict] = None,
    start_at: datetime = None,
    end_at: datetime = None,
    created_by: str = None
) -> Optional[Dict]:
    """
    创建新实验
    
    Args:
        experiment_key: 实验唯一标识
        name: 实验名称
        variants: 变体配置列表 [{"key": "control", "name": "对照组", "weight": 50}, ...]
        description: 实验描述
        experiment_type: 实验类型 ('ab', 'multivariate', 'feature_flag')
        targeting: 目标群体配置
        traffic_allocation: 流量分配百分比 (0-100)
        metrics: 目标指标配置
        start_at: 开始时间
        end_at: 结束时间
        created_by: 创建者
        
    Returns:
        创建的实验对象
    """
    if not supabase:
        logger.error("[ExperimentService] Supabase not configured")
        return None
        
    try:
        # 验证 variants 权重总和为 100
        total_weight = sum(v.get("weight", 0) for v in variants)
        if total_weight != 100:
            logger.error(f"[ExperimentService] Variants weight sum must be 100, got {total_weight}")
            return None
            
        data = {
            "experiment_key": experiment_key,
            "name": name,
            "description": description,
            "experiment_type": experiment_type,
            "variants": json.dumps(variants),
            "targeting": json.dumps(targeting or {"include_anonymous": True}),
            "traffic_allocation": traffic_allocation,
            "metrics": json.dumps(metrics or []),
            "status": "draft",
            "created_by": created_by,
            "updated_by": created_by,
        }
        
        if start_at:
            data["start_at"] = start_at.isoformat()
        if end_at:
            data["end_at"] = end_at.isoformat()
            
        result = supabase.table("experiments").insert(data).execute()
        
        if result.data:
            _invalidate_cache(experiment_key)
            return result.data[0]
        return None
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error creating experiment: {e}")
        return None


def get_experiment(experiment_key: str, use_cache: bool = True) -> Optional[Dict]:
    """
    获取实验配置
    
    Args:
        experiment_key: 实验唯一标识
        use_cache: 是否使用缓存
        
    Returns:
        实验配置对象
    """
    global _experiment_cache, _cache_timestamp
    
    # 检查缓存
    if use_cache:
        with _cache_lock:
            if experiment_key in _experiment_cache:
                cache_time = _cache_timestamp.get(experiment_key)
                if cache_time and (datetime.now() - cache_time).total_seconds() < CACHE_TTL_SECONDS:
                    return _experiment_cache[experiment_key]
    
    if not supabase:
        return None
        
    try:
        result = supabase.table("experiments")\
            .select("*")\
            .eq("experiment_key", experiment_key)\
            .single()\
            .execute()
            
        if result.data:
            experiment = _parse_experiment(result.data)
            # 更新缓存
            with _cache_lock:
                _experiment_cache[experiment_key] = experiment
                _cache_timestamp[experiment_key] = datetime.now()
            return experiment
        return None
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error getting experiment {experiment_key}: {e}")
        return None


def get_experiment_by_id(experiment_id: str) -> Optional[Dict]:
    """通过 ID 获取实验"""
    if not supabase:
        return None
        
    try:
        result = supabase.table("experiments")\
            .select("*")\
            .eq("id", experiment_id)\
            .single()\
            .execute()
            
        if result.data:
            return _parse_experiment(result.data)
        return None
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error getting experiment by id: {e}")
        return None


def list_experiments(
    status: str = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Dict], int]:
    """
    列出实验
    
    Args:
        status: 筛选状态 ('draft', 'running', 'paused', 'completed')
        limit: 返回数量
        offset: 偏移量
        
    Returns:
        (实验列表, 总数)
    """
    if not supabase:
        return [], 0
        
    try:
        query = supabase.table("experiments").select("*", count="exact")
        
        if status:
            query = query.eq("status", status)
            
        query = query.order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        experiments = [_parse_experiment(exp) for exp in (result.data or [])]
        total = result.count or len(experiments)
        
        return experiments, total
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error listing experiments: {e}")
        return [], 0


def update_experiment(
    experiment_key: str,
    updates: Dict[str, Any],
    updated_by: str = None
) -> Optional[Dict]:
    """
    更新实验配置
    
    Args:
        experiment_key: 实验唯一标识
        updates: 更新字段
        updated_by: 更新者
        
    Returns:
        更新后的实验对象
    """
    if not supabase:
        return None
        
    try:
        # 序列化 JSONB 字段
        data = {"updated_by": updated_by}
        for key, value in updates.items():
            if key in ["variants", "targeting", "metrics"]:
                data[key] = json.dumps(value) if isinstance(value, (list, dict)) else value
            elif key in ["start_at", "end_at"] and value:
                data[key] = value.isoformat() if hasattr(value, 'isoformat') else value
            else:
                data[key] = value
                
        result = supabase.table("experiments")\
            .update(data)\
            .eq("experiment_key", experiment_key)\
            .execute()
            
        if result.data:
            _invalidate_cache(experiment_key)
            return _parse_experiment(result.data[0])
        return None
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error updating experiment: {e}")
        return None


def update_experiment_status(
    experiment_key: str,
    new_status: str,
    updated_by: str = None
) -> bool:
    """
    更新实验状态
    
    Args:
        experiment_key: 实验唯一标识
        new_status: 新状态 ('draft', 'running', 'paused', 'completed')
        updated_by: 更新者
        
    Returns:
        是否成功
    """
    valid_statuses = ["draft", "running", "paused", "completed"]
    if new_status not in valid_statuses:
        logger.error(f"[ExperimentService] Invalid status: {new_status}")
        return False
        
    result = update_experiment(experiment_key, {"status": new_status}, updated_by)
    return result is not None


def delete_experiment(experiment_key: str) -> bool:
    """
    删除实验
    
    Args:
        experiment_key: 实验唯一标识
        
    Returns:
        是否成功
    """
    if not supabase:
        return False
        
    try:
        result = supabase.table("experiments")\
            .delete()\
            .eq("experiment_key", experiment_key)\
            .execute()
            
        _invalidate_cache(experiment_key)
        return True
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error deleting experiment: {e}")
        return False


# ==========================================
# Variant Assignment
# ==========================================

def assign_variant(
    experiment_key: str,
    user_identifier: str,
    identifier_type: str = "user",
    context: Dict = None
) -> Optional[str]:
    """
    为用户分配变体
    
    使用确定性哈希算法确保同一用户在同一实验中始终获得相同变体
    
    Args:
        experiment_key: 实验唯一标识
        user_identifier: 用户标识 (userCode 或 visitor_xxx)
        identifier_type: 标识类型 ('user' 或 'visitor')
        context: 上下文信息 (tier, device, source 等)
        
    Returns:
        分配的变体 key，或 None（如果不参与实验）
    """
    if not supabase:
        return None
        
    # 获取实验配置
    experiment = get_experiment(experiment_key)
    if not experiment:
        logger.warning(f"[ExperimentService] Experiment not found: {experiment_key}")
        return None
        
    # 检查实验状态
    if experiment.get("status") not in ["running"]:
        # 如果实验已结束，返回 fallback 或 winning variant
        if experiment.get("status") == "completed":
            return experiment.get("winning_variant") or experiment.get("fallback_variant", "control")
        return None
        
    # 检查目标群体
    targeting = experiment.get("targeting", {})
    
    # 匿名用户检查
    if identifier_type == "visitor" and not targeting.get("include_anonymous", True):
        return None
        
    # 用户等级检查
    allowed_tiers = targeting.get("tiers", [])
    if allowed_tiers and context:
        user_tier = context.get("tier")
        if user_tier and user_tier not in allowed_tiers:
            return None
            
    # 检查是否已分配
    try:
        existing = supabase.table("experiment_assignments")\
            .select("variant_key")\
            .eq("experiment_key", experiment_key)\
            .eq("user_identifier", user_identifier)\
            .single()\
            .execute()
            
        if existing.data:
            return existing.data["variant_key"]
    except:
        pass  # 未找到现有分配
        
    # 流量分配检查
    traffic_allocation = experiment.get("traffic_allocation", 100)
    if traffic_allocation < 100:
        # 使用哈希判断是否参与
        traffic_hash = _get_hash(f"{experiment_key}:traffic:{user_identifier}")
        if traffic_hash >= traffic_allocation:
            return None  # 不参与实验
            
    # 确定性变体分配
    variant_key = _calculate_variant(experiment, user_identifier)
    
    # 记录分配
    try:
        supabase.table("experiment_assignments").insert({
            "experiment_id": experiment["id"],
            "experiment_key": experiment_key,
            "user_identifier": user_identifier,
            "identifier_type": identifier_type,
            "variant_key": variant_key,
            "context": json.dumps(context or {}),
        }).execute()
    except Exception as e:
        logger.error(f"[ExperimentService] Error recording assignment: {e}")
        # 仍然返回分配的变体，即使记录失败
        
    return variant_key


def get_user_variant(experiment_key: str, user_identifier: str) -> Optional[str]:
    """
    获取用户已分配的变体（不进行新分配）
    
    Args:
        experiment_key: 实验唯一标识
        user_identifier: 用户标识
        
    Returns:
        已分配的变体 key，或 None
    """
    if not supabase:
        return None
        
    try:
        result = supabase.table("experiment_assignments")\
            .select("variant_key")\
            .eq("experiment_key", experiment_key)\
            .eq("user_identifier", user_identifier)\
            .single()\
            .execute()
            
        if result.data:
            return result.data["variant_key"]
        return None
        
    except:
        return None


def get_user_experiments(user_identifier: str) -> List[Dict]:
    """
    获取用户参与的所有实验
    
    Args:
        user_identifier: 用户标识
        
    Returns:
        用户参与的实验分配列表
    """
    if not supabase:
        return []
        
    try:
        result = supabase.table("experiment_assignments")\
            .select("experiment_key, variant_key, assigned_at")\
            .eq("user_identifier", user_identifier)\
            .execute()
            
        return result.data or []
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error getting user experiments: {e}")
        return []


# ==========================================
# Event Tracking
# ==========================================

def track_exposure(
    experiment_key: str,
    user_identifier: str,
    variant_key: str
) -> bool:
    """
    记录实验曝光事件
    
    用于统计实际看到变体的用户数（vs 仅被分配）
    
    Args:
        experiment_key: 实验唯一标识
        user_identifier: 用户标识
        variant_key: 变体 key
        
    Returns:
        是否成功
    """
    if not supabase:
        return False
        
    try:
        experiment = get_experiment(experiment_key)
        if not experiment:
            return False
            
        # 写入 analytics_events
        supabase.table("analytics_events").insert({
            "event_type": "md_experiment_viewed",
            "event_name": "experiment_viewed",
            "event_data": json.dumps({
                "experiment_key": experiment_key,
                "variant_key": variant_key,
            }),
            "user_code": user_identifier if not user_identifier.startswith("visitor_") else None,
            "session_id": user_identifier if user_identifier.startswith("visitor_") else None,
        }).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error tracking exposure: {e}")
        return False


def track_conversion(
    experiment_key: str,
    user_identifier: str,
    variant_key: str,
    conversion_type: str = "primary",
    value: float = None,
    metadata: Dict = None
) -> bool:
    """
    记录实验转化事件
    
    Args:
        experiment_key: 实验唯一标识
        user_identifier: 用户标识
        variant_key: 变体 key
        conversion_type: 转化类型
        value: 转化价值（可选）
        metadata: 元数据（可选）
        
    Returns:
        是否成功
    """
    if not supabase:
        return False
        
    try:
        experiment = get_experiment(experiment_key)
        if not experiment:
            return False
            
        event_data = {
            "experiment_key": experiment_key,
            "variant_key": variant_key,
            "conversion_type": conversion_type,
        }
        if value is not None:
            event_data["value"] = value
        if metadata:
            event_data.update(metadata)
            
        supabase.table("analytics_events").insert({
            "event_type": "md_experiment_converted",
            "event_name": "experiment_converted",
            "event_data": json.dumps(event_data),
            "user_code": user_identifier if not user_identifier.startswith("visitor_") else None,
            "session_id": user_identifier if user_identifier.startswith("visitor_") else None,
        }).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error tracking conversion: {e}")
        return False


# ==========================================
# Results Aggregation
# ==========================================

def aggregate_experiment_results(experiment_key: str = None) -> bool:
    """
    聚合实验结果（定时任务调用）
    
    Args:
        experiment_key: 指定实验，为 None 则聚合所有运行中的实验
        
    Returns:
        是否成功
    """
    if not supabase:
        return False
        
    try:
        # 获取需要聚合的实验
        if experiment_key:
            experiments = [get_experiment(experiment_key)]
        else:
            experiments, _ = list_experiments(status="running")
            
        now = datetime.now(timezone.utc)
        today = now.date()
        current_hour = now.hour
        
        for experiment in experiments:
            if not experiment:
                continue
                
            exp_id = experiment["id"]
            variants = experiment.get("variants", [])
            
            for variant in variants:
                variant_key = variant.get("key")
                if not variant_key:
                    continue
                    
                # 统计参与人数
                participants_result = supabase.table("experiment_assignments")\
                    .select("id", count="exact")\
                    .eq("experiment_id", exp_id)\
                    .eq("variant_key", variant_key)\
                    .execute()
                participants = participants_result.count or 0
                
                # 统计曝光次数（今天）
                # 注意：需要获取 event_data 来过滤特定实验和变体
                exposures_result = supabase.table("analytics_events")\
                    .select("event_data")\
                    .eq("event_type", "md_experiment_viewed")\
                    .gte("created_at", today.isoformat())\
                    .execute()
                # 过滤 event_data 中的 experiment_key 和 variant_key
                exposures = 0
                if exposures_result.data:
                    for event in exposures_result.data:
                        event_data = event.get("event_data", {})
                        if isinstance(event_data, str):
                            event_data = json.loads(event_data)
                        if event_data.get("experiment_key") == experiment["experiment_key"] and \
                           event_data.get("variant_key") == variant_key:
                            exposures += 1
                
                # 统计转化次数（今天）
                conversions = 0
                conversions_result = supabase.table("analytics_events")\
                    .select("event_data")\
                    .eq("event_type", "md_experiment_converted")\
                    .gte("created_at", today.isoformat())\
                    .execute()
                if conversions_result.data:
                    for event in conversions_result.data:
                        event_data = event.get("event_data", {})
                        if isinstance(event_data, str):
                            event_data = json.loads(event_data)
                        if event_data.get("experiment_key") == experiment["experiment_key"] and \
                           event_data.get("variant_key") == variant_key:
                            conversions += 1
                
                # 计算转化率
                conversion_rate = conversions / exposures if exposures > 0 else 0
                
                # Upsert 结果
                supabase.table("experiment_results").upsert({
                    "experiment_id": exp_id,
                    "variant_key": variant_key,
                    "date": today.isoformat(),
                    "hour": current_hour,
                    "participants": participants,
                    "exposures": exposures,
                    "conversions": conversions,
                    "conversion_rate": conversion_rate,
                }, on_conflict="experiment_id,variant_key,date,hour").execute()
                
        return True
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error aggregating results: {e}")
        return False


def get_experiment_results(
    experiment_key: str,
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict:
    """
    获取实验结果
    
    Args:
        experiment_key: 实验唯一标识
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        实验结果数据
    """
    if not supabase:
        return {}
        
    try:
        experiment = get_experiment(experiment_key)
        if not experiment:
            return {}
            
        query = supabase.table("experiment_results")\
            .select("*")\
            .eq("experiment_id", experiment["id"])
            
        if start_date:
            query = query.gte("date", start_date.date().isoformat())
        if end_date:
            query = query.lte("date", end_date.date().isoformat())
            
        query = query.order("date", desc=True).order("hour", desc=True)
        
        result = query.execute()
        
        # 按变体分组
        variants_data = {}
        for row in (result.data or []):
            variant_key = row["variant_key"]
            if variant_key not in variants_data:
                variants_data[variant_key] = {
                    "total_participants": 0,
                    "total_exposures": 0,
                    "total_conversions": 0,
                    "daily_data": [],
                }
            
            variants_data[variant_key]["total_participants"] = max(
                variants_data[variant_key]["total_participants"],
                row.get("participants", 0)
            )
            variants_data[variant_key]["total_exposures"] += row.get("exposures", 0)
            variants_data[variant_key]["total_conversions"] += row.get("conversions", 0)
            variants_data[variant_key]["daily_data"].append({
                "date": row["date"],
                "hour": row["hour"],
                "exposures": row.get("exposures", 0),
                "conversions": row.get("conversions", 0),
                "conversion_rate": row.get("conversion_rate", 0),
            })
            
        # 计算总体转化率
        for variant_key, data in variants_data.items():
            total_exp = data["total_exposures"]
            total_conv = data["total_conversions"]
            data["overall_conversion_rate"] = total_conv / total_exp if total_exp > 0 else 0
            
        return {
            "experiment": experiment,
            "variants": variants_data,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }
        
    except Exception as e:
        logger.error(f"[ExperimentService] Error getting results: {e}")
        return {}


# ==========================================
# Statistical Analysis
# ==========================================

def calculate_statistical_significance(
    control_conversions: int,
    control_exposures: int,
    variant_conversions: int,
    variant_exposures: int
) -> Dict:
    """
    计算统计显著性（Z-Test）
    
    Args:
        control_conversions: 对照组转化数
        control_exposures: 对照组曝光数
        variant_conversions: 变体转化数
        variant_exposures: 变体曝光数
        
    Returns:
        统计分析结果
    """
    import math
    
    if control_exposures == 0 or variant_exposures == 0:
        return {
            "significant": False,
            "z_score": 0,
            "p_value": 1,
            "confidence_level": 0,
            "relative_uplift": 0,
        }
        
    # 计算转化率
    p1 = control_conversions / control_exposures
    p2 = variant_conversions / variant_exposures
    
    # 池化标准误差
    p_pooled = (control_conversions + variant_conversions) / (control_exposures + variant_exposures)
    
    if p_pooled == 0 or p_pooled == 1:
        return {
            "significant": False,
            "z_score": 0,
            "p_value": 1,
            "confidence_level": 0,
            "relative_uplift": 0,
        }
        
    se = math.sqrt(p_pooled * (1 - p_pooled) * (1/control_exposures + 1/variant_exposures))
    
    if se == 0:
        return {
            "significant": False,
            "z_score": 0,
            "p_value": 1,
            "confidence_level": 0,
            "relative_uplift": 0,
        }
        
    # Z-score
    z_score = (p2 - p1) / se
    
    # 近似 p-value（双尾检验）
    # 使用标准正态分布的 CDF 近似
    p_value = 2 * (1 - _normal_cdf(abs(z_score)))
    
    # 置信水平
    confidence_level = (1 - p_value) * 100
    
    # 相对提升
    relative_uplift = ((p2 - p1) / p1 * 100) if p1 > 0 else 0
    
    return {
        "significant": p_value < 0.05,
        "z_score": round(z_score, 4),
        "p_value": round(p_value, 4),
        "confidence_level": round(confidence_level, 2),
        "relative_uplift": round(relative_uplift, 2),
        "control_rate": round(p1 * 100, 4),
        "variant_rate": round(p2 * 100, 4),
    }


def _normal_cdf(x: float) -> float:
    """标准正态分布 CDF 近似"""
    import math
    return (1 + math.erf(x / math.sqrt(2))) / 2


# ==========================================
# Helper Functions
# ==========================================

def _parse_experiment(data: Dict) -> Dict:
    """解析实验数据，反序列化 JSONB 字段"""
    if not data:
        return data
        
    result = dict(data)
    
    for field in ["variants", "targeting", "metrics"]:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except:
                pass
                
    return result


def _get_hash(input_string: str) -> int:
    """获取字符串的哈希值（0-99）"""
    hash_bytes = hashlib.sha256(input_string.encode()).digest()
    return int.from_bytes(hash_bytes[:4], 'big') % 100


def _calculate_variant(experiment: Dict, user_identifier: str) -> str:
    """
    计算用户应分配的变体
    
    使用确定性哈希确保相同用户在相同实验中始终获得相同变体
    """
    variants = experiment.get("variants", [])
    if not variants:
        return "control"
        
    # 计算哈希值 (0-99)
    hash_value = _get_hash(f"{experiment['experiment_key']}:{user_identifier}")
    
    # 根据权重分配
    cumulative_weight = 0
    for variant in variants:
        cumulative_weight += variant.get("weight", 0)
        if hash_value < cumulative_weight:
            return variant.get("key", "control")
            
    # 默认返回最后一个变体
    return variants[-1].get("key", "control")


def _invalidate_cache(experiment_key: str = None):
    """清除缓存"""
    global _experiment_cache, _cache_timestamp
    with _cache_lock:
        if experiment_key:
            _experiment_cache.pop(experiment_key, None)
            _cache_timestamp.pop(experiment_key, None)
        else:
            _experiment_cache.clear()
            _cache_timestamp.clear()


def clear_experiment_cache():
    """清除所有实验缓存（公开接口）"""
    _invalidate_cache()


# ==========================================
# Active Experiments Helper
# ==========================================

def get_active_experiments() -> List[Dict]:
    """获取所有活跃（运行中）的实验"""
    experiments, _ = list_experiments(status="running")
    return experiments
