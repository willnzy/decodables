"""
A/B Testing Experiments Router
A/B 测试实验路由

Public Endpoints:
- POST /api/experiments/{key}/assign - 获取变体分配
- POST /api/experiments/{key}/exposure - 记录曝光
- POST /api/experiments/{key}/conversion - 记录转化
- GET /api/experiments/user/{identifier} - 获取用户所有实验

Admin Endpoints:
- GET /api/admin/experiments - 列出实验
- POST /api/admin/experiments - 创建实验
- GET /api/admin/experiments/{key} - 获取实验详情
- PUT /api/admin/experiments/{key} - 更新实验
- DELETE /api/admin/experiments/{key} - 删除实验
- PUT /api/admin/experiments/{key}/status - 更新状态
- GET /api/admin/experiments/{key}/results - 获取结果
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from dependencies import require_admin
from services import experiment_service

# ==========================================
# Request/Response Models
# ==========================================

class VariantConfig(BaseModel):
    key: str
    name: str
    weight: int = Field(ge=0, le=100)


class TargetingConfig(BaseModel):
    include_anonymous: bool = True
    tiers: Optional[List[str]] = None


class MetricConfig(BaseModel):
    key: str
    event: str
    type: str = "conversion"  # conversion, revenue, count


class ExperimentCreateRequest(BaseModel):
    experiment_key: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    experiment_type: str = "ab"  # ab, multivariate, feature_flag
    variants: List[VariantConfig]
    targeting: Optional[TargetingConfig] = None
    traffic_allocation: int = Field(default=100, ge=0, le=100)
    metrics: Optional[List[MetricConfig]] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class ExperimentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[VariantConfig]] = None
    targeting: Optional[TargetingConfig] = None
    traffic_allocation: Optional[int] = Field(default=None, ge=0, le=100)
    metrics: Optional[List[MetricConfig]] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    fallback_variant: Optional[str] = None
    winning_variant: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str  # draft, running, paused, completed


class AssignmentRequest(BaseModel):
    user_identifier: str
    identifier_type: str = "user"  # user, visitor
    context: Optional[Dict[str, Any]] = None


class ExposureRequest(BaseModel):
    user_identifier: str
    variant_key: str


class ConversionRequest(BaseModel):
    user_identifier: str
    variant_key: str
    conversion_type: str = "primary"
    value: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


# ==========================================
# Public Router
# ==========================================

public_router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@public_router.post("/{experiment_key}/assign")
def assign_variant(experiment_key: str, req: AssignmentRequest):
    """
    为用户分配实验变体
    
    Returns:
        - variant: 分配的变体 key
        - experiment_key: 实验 key
        - assigned: 是否成功分配
    """
    variant = experiment_service.assign_variant(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        identifier_type=req.identifier_type,
        context=req.context
    )
    
    if variant is None:
        return {
            "variant": None,
            "experiment_key": experiment_key,
            "assigned": False,
            "reason": "Not eligible or experiment not running"
        }
        
    return {
        "variant": variant,
        "experiment_key": experiment_key,
        "assigned": True
    }


@public_router.post("/{experiment_key}/exposure")
def track_exposure(experiment_key: str, req: ExposureRequest):
    """
    记录实验曝光事件
    
    当用户实际看到变体内容时调用
    """
    success = experiment_service.track_exposure(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        variant_key=req.variant_key
    )
    
    return {"success": success}


@public_router.post("/{experiment_key}/conversion")
def track_conversion(experiment_key: str, req: ConversionRequest):
    """
    记录实验转化事件
    
    当用户完成目标行为时调用
    """
    success = experiment_service.track_conversion(
        experiment_key=experiment_key,
        user_identifier=req.user_identifier,
        variant_key=req.variant_key,
        conversion_type=req.conversion_type,
        value=req.value,
        metadata=req.metadata
    )
    
    return {"success": success}


@public_router.get("/user/{user_identifier}")
def get_user_experiments(user_identifier: str):
    """
    获取用户参与的所有实验
    
    Returns:
        用户的实验分配列表
    """
    experiments = experiment_service.get_user_experiments(user_identifier)
    return {"experiments": experiments}


# ==========================================
# Admin Router
# ==========================================

admin_router = APIRouter(prefix="/api/admin/experiments", tags=["admin-experiments"])


@admin_router.get("")
def list_experiments(
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(require_admin)
):
    """
    列出所有实验
    
    Args:
        status: 筛选状态 (draft, running, paused, completed)
        page: 页码
        limit: 每页数量
    """
    offset = (page - 1) * limit
    experiments, total = experiment_service.list_experiments(
        status=status,
        limit=limit,
        offset=offset
    )
    
    return {
        "experiments": experiments,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@admin_router.post("")
def create_experiment(req: ExperimentCreateRequest, admin: dict = Depends(require_admin)):
    """
    创建新实验
    """
    # 验证变体权重
    total_weight = sum(v.weight for v in req.variants)
    if total_weight != 100:
        raise HTTPException(400, f"Variants weight must sum to 100, got {total_weight}")
    
    # 转换数据
    variants = [v.model_dump() for v in req.variants]
    targeting = req.targeting.model_dump() if req.targeting else None
    metrics = [m.model_dump() for m in req.metrics] if req.metrics else None
    
    experiment = experiment_service.create_experiment(
        experiment_key=req.experiment_key,
        name=req.name,
        description=req.description,
        experiment_type=req.experiment_type,
        variants=variants,
        targeting=targeting,
        traffic_allocation=req.traffic_allocation,
        metrics=metrics,
        start_at=req.start_at,
        end_at=req.end_at,
        created_by=admin.get("id")
    )
    
    if not experiment:
        raise HTTPException(500, "Failed to create experiment")
        
    return {"status": "created", "experiment": experiment}


@admin_router.get("/{experiment_key}")
def get_experiment(experiment_key: str, admin: dict = Depends(require_admin)):
    """
    获取实验详情
    """
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
        
    return {"experiment": experiment}


@admin_router.put("/{experiment_key}")
def update_experiment(
    experiment_key: str,
    req: ExperimentUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """
    更新实验配置
    """
    updates = {}
    
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.variants is not None:
        total_weight = sum(v.weight for v in req.variants)
        if total_weight != 100:
            raise HTTPException(400, f"Variants weight must sum to 100, got {total_weight}")
        updates["variants"] = [v.model_dump() for v in req.variants]
    if req.targeting is not None:
        updates["targeting"] = req.targeting.model_dump()
    if req.traffic_allocation is not None:
        updates["traffic_allocation"] = req.traffic_allocation
    if req.metrics is not None:
        updates["metrics"] = [m.model_dump() for m in req.metrics]
    if req.start_at is not None:
        updates["start_at"] = req.start_at
    if req.end_at is not None:
        updates["end_at"] = req.end_at
    if req.fallback_variant is not None:
        updates["fallback_variant"] = req.fallback_variant
    if req.winning_variant is not None:
        updates["winning_variant"] = req.winning_variant
        
    if not updates:
        raise HTTPException(400, "No fields to update")
        
    experiment = experiment_service.update_experiment(
        experiment_key=experiment_key,
        updates=updates,
        updated_by=admin.get("id")
    )
    
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found or update failed")
        
    return {"status": "updated", "experiment": experiment}


@admin_router.put("/{experiment_key}/status")
def update_experiment_status(
    experiment_key: str,
    req: StatusUpdateRequest,
    admin: dict = Depends(require_admin)
):
    """
    更新实验状态
    """
    valid_statuses = ["draft", "running", "paused", "completed"]
    if req.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
        
    success = experiment_service.update_experiment_status(
        experiment_key=experiment_key,
        new_status=req.status,
        updated_by=admin.get("id")
    )
    
    if not success:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found or update failed")
        
    return {"status": "updated", "new_status": req.status}


@admin_router.delete("/{experiment_key}")
def delete_experiment(experiment_key: str, admin: dict = Depends(require_admin)):
    """
    删除实验
    """
    # 先检查实验状态
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
        
    if experiment.get("status") == "running":
        raise HTTPException(400, "Cannot delete running experiment. Please pause or complete it first.")
        
    success = experiment_service.delete_experiment(experiment_key)
    
    if not success:
        raise HTTPException(500, "Failed to delete experiment")
        
    return {"status": "deleted", "experiment_key": experiment_key}


def _enrich_results_with_significance(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    为实验结果添加统计显著性分析
    
    Args:
        results: 原始实验结果
        
    Returns:
        添加了统计显著性的结果
    """
    variants_data = results.get("variants", {})
    if "control" in variants_data:
        control_data = variants_data["control"]
        for variant_key, variant_data in variants_data.items():
            if variant_key != "control":
                significance = experiment_service.calculate_statistical_significance(
                    control_conversions=control_data.get("total_conversions", 0),
                    control_exposures=control_data.get("total_exposures", 0),
                    variant_conversions=variant_data.get("total_conversions", 0),
                    variant_exposures=variant_data.get("total_exposures", 0)
                )
                variant_data["significance"] = significance
    return results


@admin_router.get("/{experiment_key}/results")
def get_experiment_results(
    experiment_key: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    """
    获取实验结果
    """
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    results = experiment_service.get_experiment_results(
        experiment_key=experiment_key,
        start_date=start_dt,
        end_date=end_dt
    )
    
    if not results:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    
    return _enrich_results_with_significance(results)


@admin_router.post("/{experiment_key}/aggregate")
def trigger_aggregation(experiment_key: str, admin: dict = Depends(require_admin)):
    """
    手动触发实验结果聚合
    """
    success = experiment_service.aggregate_experiment_results(experiment_key)
    
    if not success:
        raise HTTPException(500, "Failed to aggregate results")
        
    return {"status": "aggregated", "experiment_key": experiment_key}


@admin_router.post("/aggregate-all")
def trigger_all_aggregation(admin: dict = Depends(require_admin)):
    """
    手动触发所有运行中实验的结果聚合
    """
    success = experiment_service.aggregate_experiment_results()
    
    if not success:
        raise HTTPException(500, "Failed to aggregate results")
        
    return {"status": "aggregated"}


@admin_router.post("/cache/clear")
def clear_cache(admin: dict = Depends(require_admin)):
    """
    清除实验缓存
    """
    experiment_service.clear_experiment_cache()
    return {"status": "cache_cleared"}


# ==========================================
# AI Analysis Endpoints
# ==========================================

class AIAnalysisRequest(BaseModel):
    """AI 分析请求"""
    additional_context: Optional[str] = Field(None, description="额外上下文信息")


@admin_router.post("/{experiment_key}/ai-analysis")
async def get_ai_analysis(
    experiment_key: str,
    req: Optional[AIAnalysisRequest] = None,
    admin: dict = Depends(require_admin)
):
    """
    获取实验的 AI 分析报告
    
    使用统一 AI 服务分析实验数据，提供深度洞察和可执行建议
    """
    from services import experiment_ai_service
    
    # 获取实验信息
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    
    # 获取实验结果并计算统计显著性
    results = experiment_service.get_experiment_results(experiment_key)
    if not results:
        results = {"variants": {}}
    results = _enrich_results_with_significance(results)
    
    # 调用 AI 分析 (async)
    additional_context = req.additional_context if req else None
    analysis = await experiment_ai_service.analyze_experiment_results(
        experiment=experiment,
        results=results,
        additional_context=additional_context
    )
    
    if not analysis.get("success"):
        raise HTTPException(500, analysis.get("error", "AI analysis failed"))
    
    return analysis


@admin_router.get("/{experiment_key}/quick-recommendation")
def get_quick_recommendation(experiment_key: str, admin: dict = Depends(require_admin)):
    """
    获取快速决策建议（不使用 AI，基于规则）
    """
    from services import experiment_ai_service
    
    # 获取实验信息
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    
    # 获取实验结果并计算统计显著性
    results = experiment_service.get_experiment_results(experiment_key)
    if not results:
        results = {"variants": {}}
    results = _enrich_results_with_significance(results)
    
    recommendation = experiment_ai_service.get_quick_recommendation(results)
    
    return {
        "experiment_key": experiment_key,
        "recommendation": recommendation
    }


# ==========================================
# Trend Data Endpoints
# ==========================================

@admin_router.get("/{experiment_key}/trend")
def get_experiment_trend(
    experiment_key: str,
    days: int = 30,
    admin: dict = Depends(require_admin)
):
    """
    获取实验的历史趋势数据（用于图表展示）
    
    Args:
        experiment_key: 实验唯一标识
        days: 回溯天数（默认30天，最大90天）
        
    Returns:
        每日的曝光和转化数据，按变体分组
    """
    from services.db_service import supabase
    
    # 限制最大天数
    days = min(days, 90)
    
    # 获取实验信息
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    
    experiment_id = experiment.get("id")
    variants = experiment.get("variants", [])
    variant_keys = [v.get("key") for v in variants]
    
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # 从 experiment_results 获取聚合数据
    # 表使用 date 和 hour 字段
    results_data = supabase.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id)\
        .gte("date", start_date)\
        .order("date").execute()
    
    # 按日期聚合
    daily_data = {}
    
    for result in results_data.data or []:
        date_str = result.get("date", "")
        
        if not date_str:
            continue
            
        if date_str not in daily_data:
            daily_data[date_str] = {vk: {"exposures": 0, "conversions": 0} for vk in variant_keys}
        
        variant_key = result.get("variant_key")
        if variant_key in daily_data[date_str]:
            daily_data[date_str][variant_key]["exposures"] += result.get("exposures", 0)
            daily_data[date_str][variant_key]["conversions"] += result.get("conversions", 0)
    
    # 转换为有序列表
    trend_list = []
    for date_str in sorted(daily_data.keys()):
        day_entry = {"date": date_str}
        for variant_key in variant_keys:
            vdata = daily_data[date_str].get(variant_key, {"exposures": 0, "conversions": 0})
            day_entry[f"{variant_key}_exposures"] = vdata["exposures"]
            day_entry[f"{variant_key}_conversions"] = vdata["conversions"]
            # 计算转化率
            rate = (vdata["conversions"] / vdata["exposures"] * 100) if vdata["exposures"] > 0 else 0
            day_entry[f"{variant_key}_rate"] = round(rate, 2)
        trend_list.append(day_entry)
    
    # 如果没有数据，生成空数据填充
    if not trend_list:
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            day_entry = {"date": date}
            for variant_key in variant_keys:
                day_entry[f"{variant_key}_exposures"] = 0
                day_entry[f"{variant_key}_conversions"] = 0
                day_entry[f"{variant_key}_rate"] = 0
            trend_list.append(day_entry)
    
    return {
        "experiment_key": experiment_key,
        "experiment_name": experiment.get("name"),
        "variants": variant_keys,
        "days": days,
        "trend": trend_list,
    }


@admin_router.get("/{experiment_key}/hourly-trend")
def get_hourly_trend(
    experiment_key: str,
    hours: int = 24,
    admin: dict = Depends(require_admin)
):
    """
    获取实验的小时级趋势数据
    
    Args:
        experiment_key: 实验唯一标识
        hours: 回溯小时数（默认24小时，最大168小时/7天）
        
    Returns:
        每小时的曝光和转化数据
    """
    from services.db_service import supabase
    
    # 限制最大小时数
    hours = min(hours, 168)
    
    # 获取实验信息
    experiment = experiment_service.get_experiment(experiment_key, use_cache=False)
    if not experiment:
        raise HTTPException(404, f"Experiment '{experiment_key}' not found")
    
    experiment_id = experiment.get("id")
    variants = experiment.get("variants", [])
    variant_keys = [v.get("key") for v in variants]
    
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)
    start_date = start_time.strftime("%Y-%m-%d")
    
    # 从 experiment_results 获取小时级数据
    # 表使用 date 和 hour 字段
    results_data = supabase.table("experiment_results").select("*")\
        .eq("experiment_id", experiment_id)\
        .gte("date", start_date)\
        .order("date").order("hour").execute()
    
    # 构建趋势数据
    trend_list = []
    for result in results_data.data or []:
        date_str = result.get("date", "")
        hour = result.get("hour", 0)
        variant_key = result.get("variant_key")
        
        # 构建时间字符串
        time_str = f"{date_str}T{hour:02d}:00:00"
        
        # 过滤掉 start_time 之前的数据
        result_datetime = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if result_datetime.replace(tzinfo=timezone.utc) < start_time:
            continue
        
        # 查找是否已有该时间点的数据
        existing = next((t for t in trend_list if t.get("time") == time_str), None)
        
        if not existing:
            existing = {"time": time_str}
            for vk in variant_keys:
                existing[f"{vk}_exposures"] = 0
                existing[f"{vk}_conversions"] = 0
            trend_list.append(existing)
        
        if variant_key in variant_keys:
            existing[f"{variant_key}_exposures"] = result.get("exposures", 0)
            existing[f"{variant_key}_conversions"] = result.get("conversions", 0)
    
    # 按时间排序
    trend_list.sort(key=lambda x: x.get("time", ""))
    
    return {
        "experiment_key": experiment_key,
        "experiment_name": experiment.get("name"),
        "variants": variant_keys,
        "hours": hours,
        "trend": trend_list,
    }
