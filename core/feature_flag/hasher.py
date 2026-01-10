"""
Hash-based Assignment Algorithm

@module core.feature_flag.hasher
@version 1.0.0

确定性哈希分配算法,确保:
- 同一用户+Flag 始终分配到相同变体
- 均匀分布
- 不可预测
"""

import hashlib


def get_hash_bucket(seed: str, buckets: int = 100) -> int:
    """
    确定性哈希分配

    使用 MD5 哈希算法将种子值映射到 [0, buckets) 范围内的整数。
    同一seed始终返回相同bucket,确保用户体验一致性。

    Args:
        seed: 哈希种子 (通常为 "user_id:flag_key")
        buckets: 桶数量 (默认100,对应百分比)

    Returns:
        0 到 buckets-1 之间的整数

    Example:
        >>> get_hash_bucket("user_123:feat_new_editor", 100)
        42  # 用户123在new_editor实验中被分配到第42个百分位
        >>> get_hash_bucket("user_123:feat_new_editor", 100)
        42  # 再次调用返回相同结果
    """
    # 使用 MD5 哈希 (足够快,分布均匀)
    hash_bytes = hashlib.md5(seed.encode()).digest()

    # 取前4字节转为整数
    hash_int = int.from_bytes(hash_bytes[:4], byteorder='big')

    # 取模映射到桶范围
    return hash_int % buckets
