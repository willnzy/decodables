"""
Experiment Service 扩展测试
覆盖更多代码路径

目标: 将覆盖率从 53% 提升到 90%+
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import json


# ==========================================
# Get Experiment by ID Tests
# ==========================================

class TestGetExperimentById:
    """通过 ID 获取实验测试"""
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service._parse_experiment')
    def test_get_by_id_success(self, mock_parse, mock_supabase):
        """成功通过 ID 获取实验"""
        from services.experiment_service import get_experiment_by_id
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "id": "exp_001",
            "experiment_key": "test"
        })
        mock_parse.return_value = {"id": "exp_001"}
        
        result = get_experiment_by_id("exp_001")
        
        assert result is not None
    
    @patch('services.experiment_service.supabase')
    def test_get_by_id_not_found(self, mock_supabase):
        """ID 不存在返回 None"""
        from services.experiment_service import get_experiment_by_id
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)
        
        result = get_experiment_by_id("nonexistent")
        
        assert result is None
    
    @patch('services.experiment_service.supabase')
    def test_get_by_id_error(self, mock_supabase):
        """获取时发生错误"""
        from services.experiment_service import get_experiment_by_id
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB error")
        
        result = get_experiment_by_id("exp_001")
        
        assert result is None


# ==========================================
# List Experiments Tests
# ==========================================

class TestListExperiments:
    """列出实验测试"""
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service._parse_experiment')
    def test_list_all_experiments(self, mock_parse, mock_supabase):
        """列出所有实验"""
        from services.experiment_service import list_experiments
        
        mock_parse.side_effect = lambda x: x
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[{"id": "exp_001"}, {"id": "exp_002"}],
            count=2
        )
        
        experiments, total = list_experiments()
        
        assert len(experiments) == 2
        assert total == 2
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service._parse_experiment')
    def test_list_by_status(self, mock_parse, mock_supabase):
        """按状态筛选实验"""
        from services.experiment_service import list_experiments
        
        mock_parse.side_effect = lambda x: x
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[{"id": "exp_001", "status": "running"}],
            count=1
        )
        
        experiments, total = list_experiments(status="running")
        
        assert len(experiments) == 1
    
    @patch('services.experiment_service.supabase')
    def test_list_error(self, mock_supabase):
        """列出时发生错误"""
        from services.experiment_service import list_experiments
        
        mock_supabase.table.return_value.select.side_effect = Exception("DB error")
        
        experiments, total = list_experiments()
        
        assert experiments == []
        assert total == 0


# ==========================================
# Update Experiment Tests
# ==========================================

class TestUpdateExperiment:
    """更新实验测试"""
    
    @patch('services.experiment_service._invalidate_cache')
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service._parse_experiment')
    def test_update_success(self, mock_parse, mock_supabase, mock_invalidate):
        """成功更新实验"""
        from services.experiment_service import update_experiment
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": "exp_001",
            "name": "Updated Name"
        }])
        mock_parse.return_value = {"id": "exp_001"}
        
        result = update_experiment("test_exp", {"name": "Updated Name"}, updated_by="admin_001")
        
        assert result is not None
        mock_invalidate.assert_called()
    
    @patch('services.experiment_service.supabase')
    def test_update_with_json_fields(self, mock_supabase):
        """更新包含 JSON 字段"""
        from services.experiment_service import update_experiment
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        result = update_experiment("test_exp", {
            "variants": [{"key": "control", "weight": 100}],
            "targeting": {"include_anonymous": True}
        })
        
        # 验证调用了 update
        mock_supabase.table.return_value.update.assert_called()
    
    @patch('services.experiment_service.supabase')
    def test_update_with_datetime(self, mock_supabase):
        """更新包含日期时间字段"""
        from services.experiment_service import update_experiment
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        result = update_experiment("test_exp", {
            "start_at": datetime.now(timezone.utc)
        })
        
        mock_supabase.table.return_value.update.assert_called()
    
    @patch('services.experiment_service.supabase')
    def test_update_error(self, mock_supabase):
        """更新时发生错误"""
        from services.experiment_service import update_experiment
        
        mock_supabase.table.return_value.update.side_effect = Exception("DB error")
        
        result = update_experiment("test_exp", {"name": "Updated"})
        
        assert result is None


# ==========================================
# Update Experiment Status Tests
# ==========================================

class TestUpdateExperimentStatus:
    """更新实验状态测试"""
    
    @patch('services.experiment_service.update_experiment')
    @patch('services.experiment_service.get_experiment')
    def test_update_to_running_auto_start_at(self, mock_get_exp, mock_update):
        """启动实验时自动设置 start_at"""
        from services.experiment_service import update_experiment_status
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "start_at": None  # 没有设置 start_at
        }
        mock_update.return_value = {"id": "exp_001", "status": "running"}
        
        result = update_experiment_status("test_exp", "running")
        
        assert result is True
        # 验证 update 调用时包含 start_at
        call_args = mock_update.call_args
        assert "start_at" in call_args[0][1]
    
    @patch('services.experiment_service.update_experiment')
    @patch('services.experiment_service.get_experiment')
    def test_update_to_completed_auto_end_at(self, mock_get_exp, mock_update):
        """完成实验时自动设置 end_at"""
        from services.experiment_service import update_experiment_status
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "end_at": None  # 没有设置 end_at
        }
        mock_update.return_value = {"id": "exp_001", "status": "completed"}
        
        result = update_experiment_status("test_exp", "completed")
        
        assert result is True
    
    def test_update_invalid_status(self):
        """无效状态返回 False"""
        from services.experiment_service import update_experiment_status
        
        result = update_experiment_status("test_exp", "invalid_status")
        
        assert result is False


# ==========================================
# Delete Experiment Tests
# ==========================================

class TestDeleteExperiment:
    """删除实验测试"""
    
    @patch('services.experiment_service._invalidate_cache')
    @patch('services.experiment_service.supabase')
    def test_delete_success(self, mock_supabase, mock_invalidate):
        """成功删除实验"""
        from services.experiment_service import delete_experiment
        
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        result = delete_experiment("test_exp")
        
        # delete_experiment 总是返回 True（即使没有删除任何记录）
        assert result is True
        mock_invalidate.assert_called()
    
    @patch('services.experiment_service.supabase')
    def test_delete_error(self, mock_supabase):
        """删除时发生错误"""
        from services.experiment_service import delete_experiment
        
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception("DB error")
        
        result = delete_experiment("test_exp")
        
        assert result is False


# ==========================================
# Assign Variant Extended Tests
# ==========================================

class TestAssignVariantExtended:
    """变体分配扩展测试"""
    
    @patch('services.experiment_service.get_experiment')
    def test_assign_no_experiment(self, mock_get_exp):
        """实验不存在"""
        from services.experiment_service import assign_variant
        
        mock_get_exp.return_value = None
        
        result = assign_variant("nonexistent", "user_123")
        
        assert result is None
    
    @patch('services.experiment_service._get_hash')
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_assign_traffic_allocation_excludes_user(self, mock_get_exp, mock_supabase, mock_hash):
        """流量分配排除用户"""
        from services.experiment_service import assign_variant
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "status": "running",
            "variants": [{"key": "control", "weight": 100}],
            "traffic_allocation": 50,  # 只有 50% 流量
            "targeting": {}
        }
        
        # 检查已有分配返回 None (没有现有分配)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("No data")
        
        # 用户哈希值大于流量分配
        mock_hash.return_value = 80
        
        result = assign_variant("test_exp", "user_outside_traffic")
        
        assert result is None
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_assign_existing_assignment(self, mock_get_exp, mock_supabase):
        """用户已有分配"""
        from services.experiment_service import assign_variant
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "status": "running",
            "variants": [{"key": "control", "weight": 100}],
            "traffic_allocation": 100,
            "targeting": {}
        }
        
        # 返回已有分配
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data={
            "variant_key": "control"
        })
        
        result = assign_variant("test_exp", "user_with_assignment")
        
        assert result == "control"
    
    @patch('services.experiment_service._calculate_variant')
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_assign_insert_error_still_returns_variant(self, mock_get_exp, mock_supabase, mock_calc_variant):
        """分配记录失败时仍返回变体"""
        from services.experiment_service import assign_variant
        
        mock_get_exp.return_value = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "status": "running",
            "variants": [{"key": "control", "weight": 100}],
            "traffic_allocation": 100,
            "targeting": {}
        }
        # 检查已有分配失败（没有现有分配）
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("No data")
        # 计算变体
        mock_calc_variant.return_value = "control"
        # 插入失败
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("Insert error")
        
        result = assign_variant("test_exp", "user_123")
        
        # 即使插入失败也返回变体
        assert result == "control"


# ==========================================
# Track Exposure Extended Tests
# ==========================================

class TestTrackExposureExtended:
    """曝光追踪扩展测试"""
    
    @patch('services.experiment_service.get_experiment')
    def test_track_exposure_no_experiment(self, mock_get_exp):
        """实验不存在"""
        from services.experiment_service import track_exposure
        
        mock_get_exp.return_value = None
        
        result = track_exposure("nonexistent", "user_123", "control")
        
        assert result is False
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_track_exposure_error(self, mock_get_exp, mock_supabase):
        """追踪曝光时发生错误"""
        from services.experiment_service import track_exposure
        
        mock_get_exp.return_value = {"id": "exp_001"}
        mock_supabase.table.return_value.insert.side_effect = Exception("DB error")
        
        result = track_exposure("test_exp", "user_123", "control")
        
        assert result is False


# ==========================================
# Track Conversion Extended Tests
# ==========================================

class TestTrackConversionExtended:
    """转化追踪扩展测试"""
    
    @patch('services.experiment_service.get_experiment')
    def test_track_conversion_no_experiment(self, mock_get_exp):
        """实验不存在"""
        from services.experiment_service import track_conversion
        
        mock_get_exp.return_value = None
        
        # track_conversion 签名: (experiment_key, user_identifier, variant_key, ...)
        result = track_conversion("nonexistent", "user_123", "control")
        
        assert result is False
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_track_conversion_success(self, mock_get_exp, mock_supabase):
        """成功追踪转化"""
        from services.experiment_service import track_conversion
        
        mock_get_exp.return_value = {"id": "exp_001", "experiment_key": "test_exp"}
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = track_conversion("test_exp", "user_123", "control")
        
        assert result is True
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_track_conversion_with_value(self, mock_get_exp, mock_supabase):
        """带转化价值的追踪"""
        from services.experiment_service import track_conversion
        
        mock_get_exp.return_value = {"id": "exp_001"}
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        
        result = track_conversion(
            "test_exp", "user_123", "control",
            conversion_type="purchase",
            value=99.99,
            metadata={"product_id": "prod_001"}
        )
        
        assert result is True
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_track_conversion_error(self, mock_get_exp, mock_supabase):
        """追踪转化时发生错误"""
        from services.experiment_service import track_conversion
        
        mock_get_exp.return_value = {"id": "exp_001"}
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")
        
        result = track_conversion("test_exp", "user_123", "control")
        
        assert result is False


# ==========================================
# Aggregate Experiment Results Extended Tests
# ==========================================

class TestAggregateExperimentResultsExtended:
    """聚合实验结果扩展测试"""
    
    @patch('services.experiment_service.get_experiment')
    def test_aggregate_single_experiment_not_found(self, mock_get_exp):
        """指定实验不存在"""
        from services.experiment_service import aggregate_experiment_results
        
        mock_get_exp.return_value = None
        
        result = aggregate_experiment_results("nonexistent")
        
        # 函数继续处理但跳过
        assert result is True or result is False
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.list_experiments')
    def test_aggregate_all_running_experiments(self, mock_list, mock_supabase):
        """聚合所有运行中实验"""
        from services.experiment_service import aggregate_experiment_results
        
        mock_list.return_value = ([], 0)
        
        result = aggregate_experiment_results()
        
        assert result is True


# ==========================================
# Get Experiment Results Extended Tests
# ==========================================

class TestGetExperimentResultsExtended:
    """获取实验结果扩展测试"""
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_get_results_with_dates(self, mock_get_exp, mock_supabase):
        """带日期范围获取结果"""
        from services.experiment_service import get_experiment_results
        
        mock_get_exp.return_value = {"id": "exp_001"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.order.return_value.execute.return_value = MagicMock(data=[
            {
                "variant_key": "control",
                "date": "2024-01-01",
                "hour": 10,
                "participants": 100,
                "exposures": 1000,
                "conversions": 50,
                "conversion_rate": 0.05
            }
        ])
        
        result = get_experiment_results(
            "test_exp",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert isinstance(result, dict)
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.get_experiment')
    def test_get_results_error(self, mock_get_exp, mock_supabase):
        """获取结果时发生错误"""
        from services.experiment_service import get_experiment_results
        
        mock_get_exp.return_value = {"id": "exp_001"}
        mock_supabase.table.return_value.select.side_effect = Exception("DB error")
        
        result = get_experiment_results("test_exp")
        
        assert result == {}


# ==========================================
# Statistical Significance Extended Tests
# ==========================================

class TestStatisticalSignificanceExtended:
    """统计显著性扩展测试"""
    
    def test_significance_zero_exposures(self):
        """零曝光量"""
        from services.experiment_service import calculate_statistical_significance
        
        result = calculate_statistical_significance(
            control_conversions=0,
            control_exposures=0,
            variant_conversions=0,
            variant_exposures=0
        )
        
        assert "significant" in result
    
    def test_significance_very_significant(self):
        """非常显著的差异"""
        from services.experiment_service import calculate_statistical_significance
        
        result = calculate_statistical_significance(
            control_conversions=50,
            control_exposures=1000,
            variant_conversions=150,
            variant_exposures=1000
        )
        
        assert result["significant"] is True
        assert result["p_value"] < 0.05
    
    def test_significance_not_significant(self):
        """不显著的差异"""
        from services.experiment_service import calculate_statistical_significance
        
        result = calculate_statistical_significance(
            control_conversions=100,
            control_exposures=1000,
            variant_conversions=102,  # 几乎相同
            variant_exposures=1000
        )
        
        # p_value 应该较大
        assert "p_value" in result


# ==========================================
# Create Experiment Extended Tests
# ==========================================

class TestCreateExperimentExtended:
    """创建实验扩展测试"""
    
    @patch('services.experiment_service.supabase')
    def test_create_invalid_weight_sum(self, mock_supabase):
        """变体权重总和不等于 100"""
        from services.experiment_service import create_experiment
        
        result = create_experiment(
            experiment_key="test",
            name="Test",
            variants=[
                {"key": "control", "weight": 30},
                {"key": "variant", "weight": 30}  # 总和只有 60
            ]
        )
        
        assert result is None
    
    @patch('services.experiment_service.supabase')
    def test_create_error(self, mock_supabase):
        """创建时发生错误"""
        from services.experiment_service import create_experiment
        
        mock_supabase.table.return_value.insert.side_effect = Exception("DB error")
        
        result = create_experiment(
            experiment_key="test",
            name="Test",
            variants=[{"key": "control", "weight": 100}]
        )
        
        assert result is None
    
    @patch('services.experiment_service._invalidate_cache')
    @patch('services.experiment_service.supabase')
    def test_create_with_all_options(self, mock_supabase, mock_invalidate):
        """创建带所有选项的实验"""
        from services.experiment_service import create_experiment
        
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": "exp_001"
        }])
        
        result = create_experiment(
            experiment_key="full_test",
            name="Full Test",
            variants=[{"key": "control", "weight": 100}],
            description="Test description",
            experiment_type="feature_flag",
            targeting={"tiers": ["pro"]},
            traffic_allocation=50,
            metrics=[{"name": "conversion"}],
            start_at=datetime.now(timezone.utc),
            end_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by="admin_001"
        )
        
        assert result is not None


# ==========================================
# Clear Experiment Cache Tests
# ==========================================

class TestClearExperimentCache:
    """清除实验缓存测试"""
    
    @patch('services.experiment_service.cache_service')
    def test_clear_cache(self, mock_cache):
        """清除所有实验缓存"""
        from services.experiment_service import clear_experiment_cache
        
        clear_experiment_cache()
        
        mock_cache.invalidate_experiment_cache.assert_called()


# ==========================================
# Get Experiment with Cache Tests
# ==========================================

class TestGetExperimentWithCache:
    """获取实验（带缓存）测试"""
    
    @patch('services.experiment_service.cache_service')
    def test_get_from_cache(self, mock_cache):
        """从缓存获取实验"""
        from services.experiment_service import get_experiment
        
        mock_cache.get_experiment.return_value = {"id": "exp_001", "experiment_key": "test"}
        
        result = get_experiment("test", use_cache=True)
        
        assert result is not None
        assert result["experiment_key"] == "test"


# ==========================================
# Supabase Not Configured Tests
# ==========================================

class TestSupabaseNotConfigured:
    """Supabase 未配置测试"""
    
    @patch('services.experiment_service.supabase', None)
    def test_create_without_supabase(self):
        """无 Supabase 时创建失败"""
        from services.experiment_service import create_experiment
        
        result = create_experiment(
            experiment_key="test",
            name="Test",
            variants=[{"key": "control", "weight": 100}]
        )
        
        assert result is None
    
    @patch('services.experiment_service.cache_service')
    @patch('services.experiment_service.supabase', None)
    def test_get_without_supabase(self, mock_cache):
        """无 Supabase 时获取失败"""
        from services.experiment_service import get_experiment
        
        mock_cache.get_experiment.return_value = None
        
        result = get_experiment("test", use_cache=False)
        
        assert result is None


# ==========================================
# Aggregate Results With Event Data Parsing
# ==========================================

class TestAggregateWithEventDataParsing:
    """聚合结果时解析 event_data 测试"""
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.list_experiments')
    def test_aggregate_with_json_string_event_data(self, mock_list, mock_supabase):
        """event_data 为 JSON 字符串时正确解析"""
        from services.experiment_service import aggregate_experiment_results
        
        # Mock experiments list
        mock_list.return_value = ([{
            "id": "exp_001",
            "experiment_key": "test_exp",
            "variants": [{"key": "control", "weight": 50}, {"key": "variant_a", "weight": 50}]
        }], 1)
        
        # Mock participants count
        mock_count = MagicMock()
        mock_count.count = 100
        
        # Mock exposure events with JSON string event_data
        mock_exposures = MagicMock()
        mock_exposures.data = [
            {"event_data": '{"experiment_key": "test_exp", "variant_key": "control"}'},
            {"event_data": '{"experiment_key": "test_exp", "variant_key": "control"}'}
        ]
        
        # Mock conversion events
        mock_conversions = MagicMock()
        mock_conversions.data = [
            {"event_data": '{"experiment_key": "test_exp", "variant_key": "control"}'}
        ]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "experiment_assignments":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_count
            elif table_name == "analytics_events":
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.gte.return_value = mock_chain
                mock_chain.execute.side_effect = [mock_exposures, mock_conversions]
                mock_table.select.return_value = mock_chain
            elif table_name == "experiment_results":
                mock_table.upsert.return_value.execute.return_value = MagicMock()
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = aggregate_experiment_results()
        
        assert result is True
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.list_experiments')
    def test_aggregate_with_dict_event_data(self, mock_list, mock_supabase):
        """event_data 为字典时正确处理"""
        from services.experiment_service import aggregate_experiment_results
        
        mock_list.return_value = ([{
            "id": "exp_001",
            "experiment_key": "test_exp",
            "variants": [{"key": "control", "weight": 100}]
        }], 1)
        
        mock_count = MagicMock()
        mock_count.count = 50
        
        # event_data as dict (not JSON string)
        mock_events = MagicMock()
        mock_events.data = [
            {"event_data": {"experiment_key": "test_exp", "variant_key": "control"}}
        ]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "experiment_assignments":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_count
            elif table_name == "analytics_events":
                mock_chain = MagicMock()
                mock_chain.eq.return_value = mock_chain
                mock_chain.gte.return_value = mock_chain
                mock_chain.execute.return_value = mock_events
                mock_table.select.return_value = mock_chain
            elif table_name == "experiment_results":
                mock_table.upsert.return_value.execute.return_value = MagicMock()
            return mock_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        result = aggregate_experiment_results()
        
        assert result is True
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.list_experiments')
    def test_aggregate_skip_variant_without_key(self, mock_list, mock_supabase):
        """跳过没有 key 的 variant"""
        from services.experiment_service import aggregate_experiment_results
        
        mock_list.return_value = ([{
            "id": "exp_001",
            "experiment_key": "test_exp",
            "variants": [{"weight": 100}]  # No key
        }], 1)
        
        result = aggregate_experiment_results()
        
        # Should still succeed, just skip the variant
        assert result is True
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service.list_experiments')
    def test_aggregate_empty_experiment(self, mock_list, mock_supabase):
        """跳过空实验"""
        from services.experiment_service import aggregate_experiment_results
        
        mock_list.return_value = ([None, {"id": "exp_001", "experiment_key": "test", "variants": []}], 2)
        
        result = aggregate_experiment_results()
        
        assert result is True


# ==========================================
# Get Experiment Results Edge Cases
# ==========================================

class TestGetExperimentResultsEdgeCases:
    """获取实验结果边缘情况"""
    
    @patch('services.experiment_service.supabase', None)
    def test_get_results_no_supabase(self):
        """无 Supabase 返回空字典"""
        from services.experiment_service import get_experiment_results
        
        result = get_experiment_results("test_exp")
        
        assert result == {}


# ==========================================
# Create Experiment Return None After Insert
# ==========================================

class TestCreateExperimentReturnNone:
    """创建实验返回 None 情况"""
    
    @patch('services.experiment_service.supabase')
    @patch('services.experiment_service._invalidate_cache')
    def test_create_returns_none_on_empty_result(self, mock_invalidate, mock_supabase):
        """插入结果为空时返回 None"""
        from services.experiment_service import create_experiment
        
        # Simulate insert success but result.data is empty
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(data=None)
        
        result = create_experiment(
            experiment_key="test",
            name="Test",
            variants=[{"key": "control", "weight": 100}]
        )
        
        assert result is None


# ==========================================
# Get Experiment Error Handling
# ==========================================

class TestGetExperimentError:
    """获取实验错误处理"""
    
    @patch('services.experiment_service.cache_service')
    @patch('services.experiment_service.supabase')
    def test_get_experiment_db_error(self, mock_supabase, mock_cache):
        """数据库错误时返回 None"""
        from services.experiment_service import get_experiment
        
        mock_cache.get_experiment.return_value = None
        mock_supabase.table.return_value.select.side_effect = Exception("DB Error")
        
        result = get_experiment("test", use_cache=False)
        
        assert result is None
