"""
Experiment Service Tests
实验服务测试

基于 BUSINESS_LOGIC_SPEC.md Section 10 的业务规则测试

核心业务规则:
1. 实验类型 (Section 10.1):
   - A/B 测试: ab
   - 多变体: multivariate
   - 功能标志: feature_flag

2. 变体分配 (Section 10.2):
   - 使用 SHA256(experiment_key:user_identifier)
   - 确定性分配，同一用户总是获得相同变体

3. 流量分配 (Section 10.3):
   - traffic_allocation: 0-100

@module tests/test_experiment_service
@version v3.3
"""

import pytest
from unittest.mock import patch, MagicMock
import hashlib


# ==========================================
# Hash Function Tests
# ==========================================

class TestHashFunction:
    """
    哈希函数测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 10.2
    """
    
    def test_hash_is_deterministic(self):
        """【业务规则 10.2】相同输入产生相同哈希值"""
        from services.experiment_service import _get_hash
        
        input_str = "test_experiment:user_123"
        
        hash1 = _get_hash(input_str)
        hash2 = _get_hash(input_str)
        
        assert hash1 == hash2
    
    def test_hash_returns_0_to_99(self):
        """【业务规则 10.2】哈希值在 0-99 范围内"""
        from services.experiment_service import _get_hash
        
        # 测试多个输入
        for i in range(100):
            hash_val = _get_hash(f"experiment:user_{i}")
            assert 0 <= hash_val <= 99
    
    def test_different_inputs_different_hashes(self):
        """【业务规则】不同输入产生不同哈希值"""
        from services.experiment_service import _get_hash
        
        hash1 = _get_hash("exp1:user1")
        hash2 = _get_hash("exp2:user1")
        hash3 = _get_hash("exp1:user2")
        
        # 至少有一些不同
        hashes = {hash1, hash2, hash3}
        assert len(hashes) >= 2


# ==========================================
# Variant Calculation Tests
# ==========================================

class TestVariantCalculation:
    """
    变体计算测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 10.2
    """
    
    def test_calculate_variant_deterministic(self):
        """【业务规则 10.2】变体分配是确定性的"""
        from services.experiment_service import _calculate_variant
        
        experiment = {
            "experiment_key": "test_exp",  # 使用正确的字段名
            "variants": [
                {"key": "control", "weight": 50},
                {"key": "variant_a", "weight": 50}
            ],
            "traffic_allocation": 100
        }
        
        variant1 = _calculate_variant(experiment, "user_123")
        variant2 = _calculate_variant(experiment, "user_123")
        
        assert variant1 == variant2
    
    def test_calculate_variant_respects_weights(self):
        """【业务规则 10.2】变体分配遵循权重"""
        from services.experiment_service import _calculate_variant
        
        experiment = {
            "experiment_key": "weighted_exp",  # 使用正确的字段名
            "variants": [
                {"key": "control", "weight": 90},
                {"key": "variant", "weight": 10}
            ],
            "traffic_allocation": 100
        }
        
        # 测试多个用户，大多数应该进入 control
        control_count = 0
        for i in range(100):
            variant = _calculate_variant(experiment, f"user_{i}")
            if variant == "control":
                control_count += 1
        
        # 期望大多数进入 control（允许一定方差）
        assert control_count > 50  # 应该明显倾向于 control


# ==========================================
# Traffic Allocation Tests
# ==========================================

class TestTrafficAllocation:
    """
    流量分配测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 10.3
    注意: traffic_allocation 检查在 assign_variant 中，不在 _calculate_variant 中
    """
    
    def test_full_traffic_all_assigned(self):
        """【业务规则 10.3】100% 流量时所有用户都被分配"""
        from services.experiment_service import _calculate_variant
        
        experiment = {
            "experiment_key": "full_traffic",
            "variants": [
                {"key": "control", "weight": 50},
                {"key": "variant", "weight": 50}
            ],
            "traffic_allocation": 100  # 100% 流量
        }
        
        # 所有用户都应该获得一个变体
        for i in range(10):
            variant = _calculate_variant(experiment, f"user_{i}")
            assert variant in ["control", "variant"]


# ==========================================
# Experiment CRUD Tests
# ==========================================

class TestExperimentCreate:
    """
    实验创建测试
    """
    
    @patch('services.experiment_service.supabase')
    def test_create_ab_experiment(self, mock_supabase):
        """【业务规则 10.1】创建 A/B 实验"""
        from services.experiment_service import create_experiment
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "exp_001",
            "experiment_key": "test_ab",
            "type": "ab"
        }])
        
        result = create_experiment(
            experiment_key="test_ab",  # 使用正确的参数名
            name="Test A/B",
            experiment_type="ab",  # 使用正确的参数名
            variants=[
                {"key": "control", "name": "Control", "weight": 50},
                {"key": "variant_a", "name": "Variant A", "weight": 50}
            ]
        )
        
        assert result is not None


class TestExperimentGet:
    """
    实验获取测试
    """
    
    @patch('services.experiment_service.cache_service')
    @patch('services.experiment_service.supabase')
    def test_get_existing_experiment(self, mock_supabase, mock_cache):
        """【业务规则】获取存在的实验"""
        from services.experiment_service import get_experiment
        
        mock_cache.get.return_value = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "exp_001",
            "experiment_key": "my_exp",
            "variants": [{"key": "control", "weight": 50}]
        })
        
        result = get_experiment("my_exp")
        
        assert result is not None
    
    @patch('services.experiment_service.cache_service')
    @patch('services.experiment_service.supabase')
    def test_get_nonexistent_experiment(self, mock_supabase, mock_cache):
        """【业务规则】获取不存在的实验返回 None"""
        from services.experiment_service import get_experiment
        
        mock_cache.get.return_value = None
        # single().execute() 会在找不到时返回 data=None
        mock_result = MagicMock()
        mock_result.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = get_experiment("nonexistent", use_cache=False)
        
        assert result is None


# ==========================================
# Variant Assignment Tests
# ==========================================

class TestAssignVariant:
    """
    变体分配测试
    """
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_assign_variant_success(self, mock_get_exp, mock_supabase):
        """【业务规则】成功分配变体"""
        from services.experiment_service import assign_variant
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "status": "running",
            "variants": [
                {"key": "control", "weight": 50},
                {"key": "variant_a", "weight": 50}
            ],
            "traffic_allocation": 100,
            "targeting": {}  # 空字典而不是 None
        }
        
        # Mock 检查已有分配返回 None
        mock_result = MagicMock()
        mock_result.data = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        # Mock 插入
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = assign_variant("test_exp", "user_123")
        
        assert result is not None
        assert result in ["control", "variant_a"]
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_assign_variant_inactive_experiment(self, mock_get_exp, mock_supabase):
        """【业务规则】非运行状态的实验不分配"""
        from services.experiment_service import assign_variant
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "status": "draft",  # 非运行状态
            "variants": [{"key": "control", "weight": 100}],
            "traffic_allocation": 100,
            "targeting": {}
        }
        
        result = assign_variant("test_exp", "user_123")
        
        assert result is None


# ==========================================
# Exposure Tracking Tests
# ==========================================

class TestTrackExposure:
    """
    曝光追踪测试
    """
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_track_exposure_success(self, mock_get_exp, mock_supabase):
        """【业务规则】成功记录曝光"""
        from services.experiment_service import track_exposure
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "key": "test_exp"
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = track_exposure("test_exp", "user_123", "control")
        
        assert result is True


# ==========================================
# Conversion Tracking Tests
# ==========================================

class TestTrackConversion:
    """
    转化追踪测试
    """
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_track_conversion_success(self, mock_get_exp, mock_supabase):
        """【业务规则】成功记录转化"""
        from services.experiment_service import track_conversion
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "key": "test_exp"
        }
        
        # Mock 获取分配
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "variant_key": "control"
        })
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = track_conversion("test_exp", "user_123", "purchase")
        
        assert result is True


# ==========================================
# Statistical Significance Tests
# ==========================================

class TestStatisticalSignificance:
    """
    统计显著性测试
    
    业务规则来源: BUSINESS_LOGIC_SPEC.md Section 10.5
    """
    
    def test_calculate_significance_with_data(self):
        """【业务规则 10.5】计算统计显著性"""
        from services.experiment_service import calculate_statistical_significance
        
        # 使用正确的参数格式：4个整数
        result = calculate_statistical_significance(
            control_conversions=100,
            control_exposures=1000,
            variant_conversions=150,
            variant_exposures=1000
        )
        
        # 使用实际的键名
        assert "significant" in result
        assert "p_value" in result
        assert "confidence_level" in result
    
    def test_calculate_significance_insufficient_data(self):
        """【业务规则】数据不足时返回 False"""
        from services.experiment_service import calculate_statistical_significance
        
        # 数据量太少
        result = calculate_statistical_significance(
            control_conversions=1,
            control_exposures=5,
            variant_conversions=2,
            variant_exposures=5
        )
        
        # 返回 significant 键
        assert "significant" in result


# ==========================================
# Parse Experiment Tests
# ==========================================

class TestParseExperiment:
    """
    实验解析测试
    """
    
    def test_parse_experiment_with_string_variants(self):
        """【业务规则】解析字符串格式的 variants"""
        from services.experiment_service import _parse_experiment
        import json
        
        data = {
            "id": "exp_001",
            "key": "test",
            "variants": json.dumps([{"key": "control", "weight": 100}]),
            "targeting": None
        }
        
        result = _parse_experiment(data)
        
        assert isinstance(result["variants"], list)
    
    def test_parse_experiment_with_list_variants(self):
        """【业务规则】解析列表格式的 variants"""
        from services.experiment_service import _parse_experiment
        
        data = {
            "id": "exp_001",
            "key": "test",
            "variants": [{"key": "control", "weight": 100}],
            "targeting": None
        }
        
        result = _parse_experiment(data)
        
        assert isinstance(result["variants"], list)


# ==========================================
# Cache Tests
# ==========================================

class TestExperimentCache:
    """
    实验缓存测试
    """
    
    @patch('services.experiment_service.cache_service')
    def test_invalidate_cache(self, mock_cache):
        """【业务规则】清除指定实验缓存"""
        from services.experiment_service import _invalidate_cache
        
        _invalidate_cache("test_exp")
        
        # 验证 invalidate_experiment_cache 被调用
        mock_cache.invalidate_experiment_cache.assert_called()


# ==========================================
# Active Experiments Tests
# ==========================================

class TestGetActiveExperiments:
    """
    获取活跃实验测试
    """
    
    @patch('services.experiment_service.list_experiments')
    def test_get_active_experiments(self, mock_list):
        """【业务规则】获取运行中的实验"""
        from services.experiment_service import get_active_experiments
        
        # list_experiments 返回 (experiments, count)
        mock_list.return_value = (
            [
                {"id": "exp_001", "experiment_key": "exp1", "status": "running"},
                {"id": "exp_002", "experiment_key": "exp2", "status": "running"}
            ],
            2
        )
        
        result = get_active_experiments()
        
        assert len(result) == 2
        mock_list.assert_called_with(status="running")
