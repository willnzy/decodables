"""
A/B Testing AI Analysis Service
A/B 测试 AI 分析服务

Features:
- 实验数据智能分析
- 统计显著性解读
- 可执行建议生成
- 风险评估

@module services/experiment_ai_service
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import openai

logger = logging.getLogger(__name__)

# OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = None

if OPENAI_API_KEY:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)


# ============================================================
# Expert System Prompt for A/B Testing Analysis
# ============================================================

EXPERIMENT_ANALYSIS_SYSTEM_PROMPT = """你是一位拥有 10 年经验的增长实验分析专家，曾为多家 SaaS 公司设计和分析 A/B 测试。

你的任务是根据提供的实验数据，提供**深度洞察和可执行建议**。

## 分析原则

1. **严格解读统计数据**
   - 样本量是否足够（每个变体至少需要 100+ 转化）
   - 统计显著性是否达到 95% 置信度
   - 相对提升幅度是否有业务意义（>5% 通常有意义）

2. **关注业务影响**
   - 转化率提升对收入的影响
   - 用户体验的潜在影响
   - 长期效应的考虑

3. **提供可执行建议**
   - 是否可以宣布赢家
   - 需要什么条件才能做出决定
   - 下一步实验建议

## 输出格式要求

请使用 **Markdown** 格式输出，严格按照以下结构：

---

## 📊 实验摘要

简要说明实验目的、当前状态、运行时长。

## 🔬 数据解读

### 统计显著性分析
- 分析置信度和 P-Value 含义
- 判断样本量是否充足
- 指出需要注意的统计问题

### 变体表现对比
- 比较各变体的转化率
- 计算相对提升/下降
- 分析趋势稳定性

## 💡 关键洞察

列出 3-5 个最重要的发现，每个发现包含：
- **发现**: 描述观察到的现象
- **解释**: 可能的原因分析
- **影响**: 对业务的潜在影响

## ✅ 行动建议

### 推荐决策
明确说明：
- 是否可以宣布赢家？
- 如果可以，推荐哪个变体？
- 如果不可以，需要什么条件？

### 下一步行动
1. 具体的下一步行动建议
2. 后续实验方向
3. 需要监控的指标

## ⚠️ 风险提示

列出决策时需要考虑的风险因素：
- 样本量风险
- 季节性因素
- 外部干扰
- 长期效应不确定性

---

## 注意事项

- 引用数据时使用原始数值，不要编造
- 对于显著性不足的结果，明确指出需要更多数据
- 建议必须具体可执行
- 考虑不同利益相关者的视角（产品、运营、管理层）
"""


def analyze_experiment_results(
    experiment: Dict[str, Any],
    results: Dict[str, Any],
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    使用 AI 分析实验结果
    
    Args:
        experiment: 实验配置信息
        results: 实验结果数据
        additional_context: 额外上下文信息
        
    Returns:
        AI 分析报告
    """
    if not openai_client:
        logger.error("OpenAI client not initialized - API key missing")
        return {
            "success": False,
            "error": "AI analysis unavailable - OpenAI API key not configured",
            "analysis_markdown": None
        }
    
    # 构建数据上下文
    data_context = _build_data_context(experiment, results)
    
    # 添加额外上下文
    if additional_context:
        data_context += f"\n\n## 额外上下文\n{additional_context}"
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": EXPERIMENT_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"请分析以下 A/B 测试实验数据：\n\n{data_context}"}
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        
        analysis_markdown = response.choices[0].message.content
        
        return {
            "success": True,
            "analysis_markdown": analysis_markdown,
            "model": "gpt-4o",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tokens_used": response.usage.total_tokens if response.usage else None
        }
        
    except Exception as e:
        logger.error(f"Error calling GPT-4o for experiment analysis: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis_markdown": None
        }


def _build_data_context(
    experiment: Dict[str, Any],
    results: Dict[str, Any]
) -> str:
    """构建 AI 分析的数据上下文"""
    
    # 实验基本信息
    exp_info = f"""
## 实验基本信息

- **实验名称**: {experiment.get('name', 'N/A')}
- **实验标识**: {experiment.get('experiment_key', 'N/A')}
- **实验类型**: {experiment.get('experiment_type', 'ab')}
- **当前状态**: {experiment.get('status', 'N/A')}
- **流量分配**: {experiment.get('traffic_allocation', 100)}%
- **开始时间**: {experiment.get('start_at', 'N/A')}
- **结束时间**: {experiment.get('end_at', '未设置')}
- **描述**: {experiment.get('description', '无')}
"""
    
    # 变体配置
    variants = experiment.get('variants', [])
    variants_info = "\n## 变体配置\n\n"
    for v in variants:
        variants_info += f"- **{v.get('key', 'N/A')}** ({v.get('name', 'N/A')}): 权重 {v.get('weight', 0)}%\n"
    
    # 结果数据
    results_info = "\n## 实验结果数据\n\n"
    
    variants_data = results.get('variants', {})
    if variants_data:
        results_info += "| 变体 | 参与人数 | 曝光次数 | 转化次数 | 转化率 |\n"
        results_info += "|------|----------|----------|----------|--------|\n"
        
        for key, data in variants_data.items():
            participants = data.get('total_participants', 0)
            exposures = data.get('total_exposures', 0)
            conversions = data.get('total_conversions', 0)
            conv_rate = data.get('overall_conversion_rate', 0)
            conv_rate_pct = f"{conv_rate * 100:.2f}%" if conv_rate else "0.00%"
            
            results_info += f"| {key} | {participants:,} | {exposures:,} | {conversions:,} | {conv_rate_pct} |\n"
        
        # 统计显著性
        results_info += "\n### 统计显著性分析\n\n"
        
        for key, data in variants_data.items():
            if key == 'control':
                continue
                
            sig = data.get('significance', {})
            if sig:
                is_significant = "✅ 是" if sig.get('significant') else "❌ 否"
                results_info += f"**{key} vs Control**:\n"
                results_info += f"- 统计显著性: {is_significant}\n"
                results_info += f"- 置信度: {sig.get('confidence_level', 0):.1f}%\n"
                results_info += f"- P-Value: {sig.get('p_value', 1):.4f}\n"
                results_info += f"- 相对提升: {sig.get('relative_uplift', 0):+.2f}%\n\n"
    else:
        results_info += "暂无实验结果数据。\n"
    
    # 目标群体
    targeting = experiment.get('targeting', {})
    targeting_info = "\n## 目标群体配置\n"
    targeting_info += f"- 包含匿名用户: {'是' if targeting.get('include_anonymous', True) else '否'}\n"
    if targeting.get('tiers'):
        targeting_info += f"- 目标等级: {', '.join(targeting['tiers'])}\n"
    
    return exp_info + variants_info + results_info + targeting_info


def get_quick_recommendation(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    快速决策建议（不调用 AI，基于规则）
    
    Returns:
        {
            "recommendation": "wait" | "winner_control" | "winner_variant" | "inconclusive",
            "reason": str,
            "confidence": float  # 0-1
        }
    """
    variants_data = results.get('variants', {})
    
    if not variants_data:
        return {
            "recommendation": "wait",
            "reason": "暂无数据，需要等待实验收集更多流量",
            "confidence": 0
        }
    
    # 检查样本量
    total_conversions = sum(
        v.get('total_conversions', 0) 
        for v in variants_data.values()
    )
    
    if total_conversions < 50:
        return {
            "recommendation": "wait",
            "reason": f"总转化数 {total_conversions} 不足，建议至少收集 100 次转化后再做决策",
            "confidence": 0.2
        }
    
    # 检查统计显著性
    control_data = variants_data.get('control', {})
    control_rate = control_data.get('overall_conversion_rate', 0)
    
    significant_winners = []
    
    for key, data in variants_data.items():
        if key == 'control':
            continue
            
        sig = data.get('significance', {})
        if sig.get('significant'):
            uplift = sig.get('relative_uplift', 0)
            if uplift > 5:  # 至少 5% 提升才有业务意义
                significant_winners.append({
                    "key": key,
                    "uplift": uplift,
                    "confidence": sig.get('confidence_level', 0)
                })
    
    if significant_winners:
        best = max(significant_winners, key=lambda x: x['uplift'])
        return {
            "recommendation": f"winner_{best['key']}",
            "reason": f"{best['key']} 变体显著优于对照组，相对提升 {best['uplift']:.1f}%，置信度 {best['confidence']:.1f}%",
            "confidence": best['confidence'] / 100
        }
    
    # 检查是否有显著较差的变体
    for key, data in variants_data.items():
        if key == 'control':
            continue
            
        sig = data.get('significance', {})
        if sig.get('significant') and sig.get('relative_uplift', 0) < -5:
            return {
                "recommendation": "winner_control",
                "reason": f"对照组显著优于 {key}，后者转化率下降 {abs(sig.get('relative_uplift', 0)):.1f}%",
                "confidence": sig.get('confidence_level', 0) / 100
            }
    
    # 无显著差异
    return {
        "recommendation": "inconclusive",
        "reason": "各变体之间无显著差异，建议继续收集数据或考虑实验假设是否正确",
        "confidence": 0.5
    }


def generate_experiment_summary(
    experiment: Dict[str, Any],
    results: Dict[str, Any]
) -> str:
    """
    生成实验摘要（不使用 AI）
    
    Returns:
        简短的实验状态摘要
    """
    name = experiment.get('name', 'Unknown')
    status = experiment.get('status', 'unknown')
    
    variants_data = results.get('variants', {})
    total_participants = sum(
        v.get('total_participants', 0) 
        for v in variants_data.values()
    )
    total_conversions = sum(
        v.get('total_conversions', 0) 
        for v in variants_data.values()
    )
    
    # 找出表现最好的变体
    best_variant = None
    best_rate = 0
    
    for key, data in variants_data.items():
        rate = data.get('overall_conversion_rate', 0)
        if rate > best_rate:
            best_rate = rate
            best_variant = key
    
    quick_rec = get_quick_recommendation(results)
    
    summary = f"**{name}** ({status})\n"
    summary += f"参与: {total_participants:,} | 转化: {total_conversions:,}\n"
    
    if best_variant:
        summary += f"领先变体: {best_variant} ({best_rate * 100:.2f}%)\n"
    
    summary += f"建议: {quick_rec['reason']}"
    
    return summary
