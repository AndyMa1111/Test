"""
八字分析结果缓存模块。
当用户输入相同八字和大运时，直接返回缓存结果，不重复调用 DeepSeek。
"""
import json
import os
import time
from typing import Optional

CACHE_FILE = os.path.expanduser("~/.hermes/bazi_cache.json")
MAX_ENTRIES = 200  # 最多缓存200条


def _load_cache() -> dict:
    """加载缓存文件，不存在则返回空字典。"""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def _save_cache(cache: dict):
    """保存缓存到文件。"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _build_cache_key(bazi: dict, dayun: dict, gender: str) -> str:
    """
    构建缓存唯一键。
    基于八字字符串 + 性别 + 大运特征。
    """
    # 八字字符串：年月日时干支
    bazi_str = ""
    for k in ["year", "month", "day", "hour"]:
        p = bazi.get(k, {})
        bazi_str += f"{p.get('gan', '')}{p.get('zhi', '')}"
    
    # 大运特征：起运年月 + 前两步运的干支
    luck_cycles = dayun.get("luck_cycles", [])
    dayun_str = f"{dayun.get('starting_years', 0)}_{dayun.get('starting_months', 0)}"
    for i, c in enumerate(luck_cycles[:2]):
        dayun_str += f"_{c.get('gan_char', '')}{c.get('zhi_char', '')}"
    
    return f"{bazi_str}_{gender}_{dayun_str}"


def get_cached_result(bazi: dict, dayun: dict, gender: str) -> Optional[dict]:
    """
    查找缓存。
    
    Args:
        bazi: 八字数据（含年/月/日/时柱的 gan/zhi）
        dayun: 大运数据（含 starting_years/starting_months/luck_cycles）
        gender: 性别
    
    Returns:
        缓存的完整结果，或 None
    """
    cache = _load_cache()
    key = _build_cache_key(bazi, dayun, gender)
    entry = cache.get(key)
    if entry:
        entry["_from_cache"] = True
        entry["_cached_at"] = entry.get("timestamp", "")
        return entry.get("result")
    return None


def save_to_cache(bazi: dict, dayun: dict, gender: str, result: dict):
    """
    保存分析结果到缓存。
    """
    cache = _load_cache()
    key = _build_cache_key(bazi, dayun, gender)
    
    cache[key] = {
        "bazi_str": "".join([f"{bazi[k]['gan']}{bazi[k]['zhi']}" for k in ["year", "month", "day", "hour"]]),
        "gender": gender,
        "dayun_start": f"{dayun.get('starting_years')}岁{dayun.get('starting_months')}个月",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "result": result,
    }
    
    # 限制缓存数量
    if len(cache) > MAX_ENTRIES:
        # 删除最早的条目
        sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("timestamp", ""))
        for k in sorted_keys[:len(cache) - MAX_ENTRIES]:
            del cache[k]
    
    _save_cache(cache)
