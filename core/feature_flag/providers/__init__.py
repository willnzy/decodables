"""
Feature Flag Providers

@module core.feature_flag.providers
@version 1.0.0

支持的Providers:
- SelfHostedProvider: 自建实现 (基于Supabase)
- GrowthBookProvider: 集成GrowthBook (可选)
- UnleashProvider: 集成Unleash (可选)
"""

from .self_hosted import SelfHostedProvider

__all__ = [
    "SelfHostedProvider",
]
