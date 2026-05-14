"""
调候用神 (Climate Adjustment Gods) module.
Queries the 穷通宝鉴 database to determine climate adjustment needs.
"""

import re
import os
from typing import Optional


# Path to the 穷通宝鉴 file
# Try project-local path first, then fall back to original
import os
_QIONGTONG_LOCAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "qiongtong_complete.txt")
QIONGTONG_PATH = _QIONGTONG_LOCAL if os.path.exists(_QIONGTONG_LOCAL) else '/mnt/d/Hermes交流/qiongtong_complete.txt'

# Mapping: heavenly stem name → index
TIAN_GAN_MAP = {'甲': 0, '乙': 1, '丙': 2, '丁': 3, '戊': 4, '己': 5, '庚': 6, '辛': 7, '壬': 8, '癸': 9}
TIAN_GAN_LIST = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

# Month branches
MONTHS = ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑']


def get_tiaohou(day_gan: int, month_zhi: int) -> Optional[dict]:
    """
    Get climate adjustment (调候) information from 穷通宝鉴.
    
    Args:
        day_gan: Day heavenly stem index (0-9)
        month_zhi: Month earthly branch index (0-11, where 子=0, 丑=1, ..., 亥=11)
    
    Returns:
        dict with tiaohou analysis, or None if not found
    """
    gan_char = TIAN_GAN_LIST[day_gan]
    month_char = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'][month_zhi]
    
    return query_qiongtong(gan_char, month_char)


def query_qiongtong(gan_char: str, month_char: str) -> Optional[dict]:
    """
    Query the 穷通宝鉴 file for a specific stem-month combination.
    
    Format in file:
    【甲木寅月】
    穷通宝鉴-甲木寅月
    甲木寅月：調合氣候爲要，丙火爲主，癸水爲佐。
    ...
    
    Args:
        gan_char: Heavenly stem character (甲-癸)
        month_char: Month character (寅-丑)
    
    Returns:
        dict with 'summary', 'details' and 'key_gods'
    """
    if not os.path.exists(QIONGTONG_PATH):
        return None
    
    # Build the section header to search for
    # Format in file: 【甲木寅月】, 【辛金午月】, etc.
    gan_elements = {
        '甲': '木', '乙': '木', '丙': '火', '丁': '火',
        '戊': '土', '己': '土', '庚': '金', '辛': '金',
        '壬': '水', '癸': '水',
    }
    
    header = f'【{gan_char}{gan_elements.get(gan_char, "")}{month_char}月】'
    
    try:
        with open(QIONGTONG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None
    
    # Find the section
    # Sections are separated by 【...】 headers
    lines = content.split('\n')
    section_lines = []
    in_section = False
    for line in lines:
        if header in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.strip().startswith('【') and header not in line:
                break
            section_lines.append(line)
    
    if not section_lines:
        return None
    
    section_text = '\n'.join(section_lines)
    
    # Extract summary (first meaningful line after header)
    summary_lines = []
    for line in section_lines:
        if '：' in line or '。' in line:
            summary_lines.append(line.strip())
    
    summary = summary_lines[1] if len(summary_lines) > 1 else summary_lines[0] if summary_lines else section_text[:200]
    
    # Extract key gods mentioned
    key_gods = extract_key_gods(section_text, gan_char)
    
    return {
        'summary': summary[:500],
        'full_text': section_text[:2000],
        'key_gods': key_gods,
    }


def get_qiongtong_text(day_gan: int, month_zhi: int) -> Optional[str]:
    """
    Get just the 穷通宝鉴 text (without 八字提要) for a given stem-month.
    Returns the original text before the 八字提要 section.
    """
    gan_char = TIAN_GAN_LIST[day_gan]
    month_char = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'][month_zhi]
    
    if not os.path.exists(QIONGTONG_PATH):
        return None
    
    gan_elements = {
        '甲': '木', '乙': '木', '丙': '火', '丁': '火',
        '戊': '土', '己': '土', '庚': '金', '辛': '金',
        '壬': '水', '癸': '水',
    }
    header = f'【{gan_char}{gan_elements.get(gan_char, "")}{month_char}月】'
    
    try:
        with open(QIONGTONG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None
    
    lines = content.split('\n')
    section_lines = []
    in_section = False
    for line in lines:
        if header in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.strip().startswith('【') and header not in line:
                break
            # Stop before 八字提要
            if '八字提要' in line:
                break
            section_lines.append(line)
    
    if not section_lines:
        return None
    
    # Remove the header line and leading/trailing empty lines
    text_lines = [l for l in section_lines[1:] if l.strip()]
    if not text_lines:
        return None
    
    return '\n'.join(text_lines).strip()


def get_bazi_tiyao_for_hour(day_gan: int, month_zhi: int, hour_gan: int, hour_zhi: int) -> Optional[str]:
    """
    Get the 八字提要 entry matching the specific 时柱.
    
    The 八字提要 section contains entries like:
    命理上 :甲日主生 寅月 甲子 時 ...
    甲日主生 寅月 乙丑 時 ...
    
    Returns only the entry matching the given 时柱.
    """
    from backend.data.solar_terms import TIAN_GAN as TG, DI_ZHI as DZ
    
    gan_char = TIAN_GAN_LIST[day_gan]
    month_char = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'][month_zhi]
    hour_char = f"{TG[hour_gan]}{DZ[hour_zhi]}"
    
    if not os.path.exists(QIONGTONG_PATH):
        return None
    
    gan_elements = {
        '甲': '木', '乙': '木', '丙': '火', '丁': '火',
        '戊': '土', '己': '土', '庚': '金', '辛': '金',
        '壬': '水', '癸': '水',
    }
    header = f'【{gan_char}{gan_elements.get(gan_char, "")}{month_char}月】'
    
    try:
        with open(QIONGTONG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None
    
    lines = content.split('\n')
    
    # Find the section
    in_section = False
    in_tiyao = False
    tiyao_lines = []
    
    for line in lines:
        if header in line:
            in_section = True
            continue
        if in_section:
            if line.strip().startswith('【') and header not in line:
                break
            if '八字提要' in line:
                in_tiyao = True
                continue
            if in_tiyao:
                if line.strip().startswith('【') or line.strip().startswith('---'):
                    break
                if line.strip():
                    tiyao_lines.append(line.strip())
    
    if not tiyao_lines:
        return None
    
    # Now find the entry matching our 时柱
    for i, line in enumerate(tiyao_lines):
        if hour_char in line:
            # This line and possibly the next few lines form the entry
            entry = line
            # Some entries span multiple lines
            if i + 1 < len(tiyao_lines) and '時' not in tiyao_lines[i + 1]:
                entry += ' ' + tiyao_lines[i + 1]
            # Clean up
            entry = entry.replace('命理上 :', '').strip()
            return entry
    
    return None


def extract_key_gods(text: str, day_gan_char: str) -> list:
    """
    Extract key gods (用神) mentioned in the 穷通宝鉴 text.
    Looks for patterns like "丙火为主", "癸水为佐", "得丙癸透", etc.
    """
    gods = []
    gan_pattern = re.findall(r'[甲乙丙丁戊己庚辛壬癸]', text)
    
    # Count occurrences of each stem
    from collections import Counter
    counts = Counter(gan_pattern)
    
    # Exclude the day stem itself
    for gan_char in TIAN_GAN_LIST:
        if gan_char != day_gan_char and counts.get(gan_char, 0) > 1:
            mention_count = counts[gan_char]
            if mention_count >= 2:
                gods.append({
                    'gan_char': gan_char,
                    'mention_count': mention_count,
                })
    
    # Sort by mention count
    gods.sort(key=lambda x: x['mention_count'], reverse=True)
    
    return gods
