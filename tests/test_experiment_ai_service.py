"""
Experiment AI Service Tests
实验 AI 分析服务测试

覆盖:
- analyze_experiment_results
- _build_data_context
- get_quick_recommendation
- generate_experiment_summary
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# ==========================================
# Analyze Experiment Results Tests
# ==========================================

class TestAnalyzeExperimentResults:
    """分析实验结果测试"""
    
    @patch('services.experiment_ai_service.openai_client')
    def test_analyze_success(self, mock_openai):
        """成功分析实验结果"""
        from services.experiment_ai_service import analyze_experiment_results
        
        experiment = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "name": "Test Experiment",
            "description": "A test experiment",
            "variants": [
                {"key": "control", "name": "Control"},
                {"key": "variant_a", "name": "Variant A"}
            ],
            "status": "running",
            "start_at": datetime.now(timezone.utc).isoformat()
        }
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_exposures": 5000,
                    "total_conversions": 100,
                    "conversion_rate": 0.02
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_exposures": 5000,
                    "total_conversions": 150,
                    "conversion_rate": 0.03
                }
            },
            "statistical_significance": {
                "significant": True,
                "p_value": 0.01,
                "confidence_level": 0.99
            }
        }
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="## Analysis\n\nTest analysis content"))]
        mock_response.usage = MagicMock(total_tokens=500)
        mock_openai.chat.completions.create.return_value = mock_response
        
        result = analyze_experiment_results(experiment, results)
        
        assert result is not None
        assert result["success"] is True
        assert "analysis_markdown" in result
    
    @patch('services.experiment_ai_service.openai_client', None)
    def test_analyze_no_openai_client(self):
        """OpenAI 客户端未配置"""
        from services.experiment_ai_service import analyze_experiment_results
        
        experiment = {"id": "exp_001"}
        results = {"variants": {}}
        
        result = analyze_experiment_results(experiment, results)
        
        assert result["success"] is False
        assert "error" in result
    
    @patch('services.experiment_ai_service.openai_client')
    def test_analyze_openai_error(self, mock_openai):
        """OpenAI API 调用失败"""
        from services.experiment_ai_service import analyze_experiment_results
        
        experiment = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "variants": [{"key": "control"}],
            "status": "running"
        }
        results = {
            "variants": {
                "control": {"total_conversions": 100, "total_exposures": 1000}
            }
        }
        mock_openai.chat.completions.create.side_effect = Exception("API Error")
        
        result = analyze_experiment_results(experiment, results)
        
        assert result["success"] is False
        assert "error" in result
    
    @patch('services.experiment_ai_service.openai_client')
    def test_analyze_with_additional_context(self, mock_openai):
        """带额外上下文的分析"""
        from services.experiment_ai_service import analyze_experiment_results
        
        experiment = {"id": "exp_001", "name": "Test", "experiment_key": "test"}
        results = {"variants": {}}
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Analysis"))]
        mock_response.usage = None
        mock_openai.chat.completions.create.return_value = mock_response
        
        result = analyze_experiment_results(
            experiment, results,
            additional_context="This experiment is for Q1 product launch."
        )
        
        assert result["success"] is True


# ==========================================
# Build Data Context Tests
# ==========================================

class TestBuildDataContext:
    """构建数据上下文测试"""
    
    def test_build_context_basic(self):
        """基本上下文构建"""
        from services.experiment_ai_service import _build_data_context
        
        experiment = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "name": "Test Experiment",
            "description": "A test",
            "variants": [
                {"key": "control", "name": "Control", "weight": 50},
                {"key": "variant_a", "name": "Variant A", "weight": 50}
            ],
            "status": "running",
            "start_at": "2024-01-01T00:00:00Z"
        }
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 500,
                    "total_exposures": 2500,
                    "total_conversions": 50,
                    "conversion_rate": 0.02
                },
                "variant_a": {
                    "total_participants": 500,
                    "total_exposures": 2500,
                    "total_conversions": 75,
                    "conversion_rate": 0.03
                }
            },
            "statistical_significance": {
                "significant": True,
                "p_value": 0.02
            }
        }
        
        context = _build_data_context(experiment, results)
        
        assert "test_exp" in context
        assert "control" in context
    
    def test_build_context_empty_results(self):
        """空结果上下文"""
        from services.experiment_ai_service import _build_data_context
        
        experiment = {
            "id": "exp_001",
            "experiment_key": "test",
            "name": "Test",
            "variants": [],
            "status": "draft"
        }
        
        results = {"variants": {}}
        
        context = _build_data_context(experiment, results)
        
        assert context is not None
    
    def test_build_context_with_significance_data(self):
        """带显著性数据的上下文"""
        from services.experiment_ai_service import _build_data_context
        
        experiment = {
            "id": "exp_001",
            "experiment_key": "test_exp",
            "name": "Significance Test",
            "variants": [
                {"key": "control", "name": "Control", "weight": 50},
                {"key": "variant_a", "name": "Variant A", "weight": 50}
            ],
            "status": "running"
        }
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_exposures": 5000,
                    "total_conversions": 100,
                    "overall_conversion_rate": 0.02
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_exposures": 5000,
                    "total_conversions": 150,
                    "overall_conversion_rate": 0.03,
                    "significance": {
                        "significant": True,
                        "confidence_level": 95.5,
                        "p_value": 0.045,
                        "relative_uplift": 50.0
                    }
                }
            }
        }
        
        context = _build_data_context(experiment, results)
        
        assert "统计显著性" in context
        assert "95.5" in context
        assert "variant_a vs Control" in context
    
    def test_build_context_with_targeting_tiers(self):
        """带目标等级的上下文"""
        from services.experiment_ai_service import _build_data_context
        
        experiment = {
            "id": "exp_001",
            "experiment_key": "tier_test",
            "name": "Tier Test",
            "variants": [],
            "status": "running",
            "targeting": {
                "include_anonymous": False,
                "tiers": ["pro", "starter"]
            }
        }
        
        results = {"variants": {}}
        
        context = _build_data_context(experiment, results)
        
        assert "目标等级" in context
        assert "pro" in context
        assert "starter" in context


# ==========================================
# Get Quick Recommendation Tests
# ==========================================

class TestGetQuickRecommendation:
    """快速建议测试"""
    
    def test_recommendation_significant_winner(self):
        """有显著赢家"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_exposures": 5000,
                    "total_conversions": 100,
                    "conversion_rate": 0.02
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_exposures": 5000,
                    "total_conversions": 200,
                    "conversion_rate": 0.04
                }
            },
            "statistical_significance": {
                "significant": True,
                "p_value": 0.001,
                "confidence_level": 0.999
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        assert "recommendation" in recommendation or "winner" in recommendation or isinstance(recommendation, dict)
    
    def test_recommendation_not_significant(self):
        """无显著差异"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 100,
                    "total_conversions": 10,
                    "conversion_rate": 0.10
                },
                "variant_a": {
                    "total_participants": 100,
                    "total_conversions": 11,
                    "conversion_rate": 0.11
                }
            },
            "statistical_significance": {
                "significant": False,
                "p_value": 0.8
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        assert recommendation is not None
    
    def test_recommendation_insufficient_data(self):
        """数据不足"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 10,
                    "total_conversions": 1,
                    "conversion_rate": 0.10
                }
            },
            "statistical_significance": {
                "significant": False
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        assert recommendation is not None
    
    def test_recommendation_empty_results(self):
        """空结果"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {"variants": {}}
        
        recommendation = get_quick_recommendation(results)
        
        assert recommendation is not None
    
    def test_recommendation_with_significant_winner_over_5_percent(self):
        """有显著赢家且提升超过 5%"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_conversions": 100,
                    "overall_conversion_rate": 0.10
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_conversions": 200,
                    "overall_conversion_rate": 0.20,
                    "significance": {
                        "significant": True,
                        "confidence_level": 99.0,
                        "p_value": 0.001,
                        "relative_uplift": 100.0  # 100% uplift > 5%
                    }
                }
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        assert recommendation["recommendation"] == "winner_variant_a"
        assert recommendation["confidence"] > 0
        assert "variant_a" in recommendation["reason"]
    
    def test_recommendation_control_wins_variant_significantly_worse(self):
        """对照组赢，变体显著差于对照组"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_conversions": 200,
                    "overall_conversion_rate": 0.20
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_conversions": 100,
                    "overall_conversion_rate": 0.10,
                    "significance": {
                        "significant": True,
                        "confidence_level": 95.0,
                        "p_value": 0.02,
                        "relative_uplift": -50.0  # -50% < -5%, control wins
                    }
                }
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        assert recommendation["recommendation"] == "winner_control"
        assert "对照组" in recommendation["reason"] or "control" in recommendation["reason"].lower()
    
    def test_recommendation_with_multiple_significant_winners(self):
        """多个变体都显著优于对照组，选择最佳"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_conversions": 100,
                    "overall_conversion_rate": 0.10
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_conversions": 150,
                    "overall_conversion_rate": 0.15,
                    "significance": {
                        "significant": True,
                        "confidence_level": 95.0,
                        "p_value": 0.03,
                        "relative_uplift": 50.0
                    }
                },
                "variant_b": {
                    "total_participants": 1000,
                    "total_conversions": 180,
                    "overall_conversion_rate": 0.18,
                    "significance": {
                        "significant": True,
                        "confidence_level": 98.0,
                        "p_value": 0.01,
                        "relative_uplift": 80.0  # 80% > 50%, this is the best
                    }
                }
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        # Should pick variant_b as it has higher uplift
        assert recommendation["recommendation"] == "winner_variant_b"
    
    def test_recommendation_significant_but_low_uplift(self):
        """显著但提升不到 5%，视为不显著"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_conversions": 100,
                    "overall_conversion_rate": 0.10
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_conversions": 103,
                    "overall_conversion_rate": 0.103,
                    "significance": {
                        "significant": True,
                        "confidence_level": 95.0,
                        "p_value": 0.04,
                        "relative_uplift": 3.0  # 3% < 5%, not business meaningful
                    }
                }
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        # Low uplift should result in inconclusive
        assert recommendation["recommendation"] == "inconclusive"


# ==========================================
# Generate Experiment Summary Tests
# ==========================================

class TestGenerateExperimentSummary:
    """生成实验摘要测试"""
    
    def test_summary_basic(self):
        """基本摘要生成"""
        from services.experiment_ai_service import generate_experiment_summary
        
        experiment = {
            "id": "exp_001",
            "name": "Test",
            "status": "running"
        }
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 500,
                    "total_conversions": 50,
                    "overall_conversion_rate": 0.10
                },
                "variant_a": {
                    "total_participants": 500,
                    "total_conversions": 75,
                    "overall_conversion_rate": 0.15
                }
            },
            "statistical_significance": {
                "significant": True,
                "p_value": 0.01
            }
        }
        
        summary = generate_experiment_summary(experiment, results)
        
        assert summary is not None
        assert isinstance(summary, str)
        assert "Test" in summary
    
    def test_summary_empty_results(self):
        """空结果"""
        from services.experiment_ai_service import generate_experiment_summary
        
        experiment = {"name": "Test", "status": "draft"}
        results = {"variants": {}}
        
        summary = generate_experiment_summary(experiment, results)
        
        assert summary is not None
        assert isinstance(summary, str)
    
    def test_summary_with_all_data(self):
        """包含所有数据的摘要"""
        from services.experiment_ai_service import generate_experiment_summary
        
        experiment = {
            "id": "exp_001",
            "name": "Full Test",
            "status": "completed",
            "winning_variant": "variant"
        }
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 10000,
                    "total_conversions": 1000,
                    "overall_conversion_rate": 0.10
                },
                "variant": {
                    "total_participants": 10000,
                    "total_conversions": 1500,
                    "overall_conversion_rate": 0.15
                }
            },
            "statistical_significance": {
                "significant": True,
                "p_value": 0.0001
            }
        }
        
        summary = generate_experiment_summary(experiment, results)
        
        assert summary is not None
        assert "variant" in summary.lower() or "领先" in summary


# ==========================================
# Edge Cases Tests
# ==========================================

class TestEdgeCases:
    """边界情况测试"""
    
    def test_recommendation_missing_significance(self):
        """缺少显著性数据"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {"total_conversions": 100}
            }
            # 没有 statistical_significance
        }
        
        recommendation = get_quick_recommendation(results)
        
        assert recommendation is not None
    
    def test_recommendation_negative_conversion_rate(self):
        """对照组更好"""
        from services.experiment_ai_service import get_quick_recommendation
        
        results = {
            "variants": {
                "control": {
                    "total_participants": 1000,
                    "total_conversions": 200,
                    "conversion_rate": 0.20
                },
                "variant_a": {
                    "total_participants": 1000,
                    "total_conversions": 100,
                    "conversion_rate": 0.10
                }
            },
            "statistical_significance": {
                "significant": True,
                "p_value": 0.001
            }
        }
        
        recommendation = get_quick_recommendation(results)
        
        assert recommendation is not None
