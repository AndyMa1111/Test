"""
24 solar terms calculation and related utilities for Ba Zi (Four Pillars) calculation.

Uses astronomical algorithms to compute solar term dates with high accuracy.
"""

import math
from datetime import date, datetime, timedelta
from typing import List, Tuple

# Heavenly Stems (天干)
TIAN_GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
TIAN_GAN_YIN_YANG = ['阳', '阴', '阳', '阴', '阳', '阴', '阳', '阴', '阳', '阴']

# Earthly Branches (地支)
DI_ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
DI_ZHI_ZANG_GAN = {
    '子': ['癸'],
    '丑': ['己', '癸', '辛'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'],
    '未': ['己', '丁', '乙'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['戊', '辛', '丁'],
    '亥': ['壬', '甲'],
}

# 地支对应的月份（节气月）
DI_ZHI_MONTH = {
    '寅': 1,   # 立春~惊蛰
    '卯': 2,   # 惊蛰~清明
    '辰': 3,   # 清明~立夏
    '巳': 4,   # 立夏~芒种
    '午': 5,   # 芒种~小暑
    '未': 6,   # 小暑~立秋
    '申': 7,   # 立秋~白露
    '酉': 8,   # 白露~寒露
    '戌': 9,   # 寒露~立冬
    '亥': 10,  # 立冬~大雪
    '子': 11,  # 大雪~小寒
    '丑': 12,  # 小寒~立春
}

MONTH_TO_DI_ZHI = {v: k for k, v in DI_ZHI_MONTH.items()}

# 24节气名称（按顺序）
JIE_QI_NAMES = [
    '立春', '雨水', '惊蛰', '春分', '清明', '谷雨',
    '立夏', '小满', '芒种', '夏至', '小暑', '大暑',
    '立秋', '处暑', '白露', '秋分', '寒露', '霜降',
    '立冬', '小雪', '大雪', '冬至', '小寒', '大寒',
]

# 用于月柱的"节"（月令分界点）
# 每个月令从某个"节"开始
MONTH_JIE = ['立春', '惊蛰', '清明', '立夏', '芒种', '小暑',
             '立秋', '白露', '寒露', '立冬', '大雪', '小寒']


def _julian_day_number(year: int, month: int, day: int) -> int:
    """Calculate Julian Day Number for a Gregorian date."""
    if month <= 2:
        year -= 1
        month += 12
    A = year // 100
    B = 2 - A + A // 4
    JDN = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    return int(JDN + 0.5)


def _jdn_to_datetime(jdn: float) -> datetime:
    """Convert Julian Day Number to datetime (UTC)."""
    jdn = jdn + 0.5
    Z = int(jdn)
    F = jdn - Z
    A = Z
    if Z >= 2299161:
        alpha = (Z - 1867216.25) // 36524.25
        A = Z + 1 + alpha - alpha // 4
    B = A + 1524
    C = (B - 122.1) // 365.25
    D = int(365.25 * C)
    E = (B - D) // 30.6001
    day = B - D - int(30.6001 * E) + F
    month = E - 1 if E < 14 else E - 13
    year = C - 4716 if month > 2 else C - 4715
    # Time
    frac = day - int(day)
    hours = int(frac * 24)
    minutes = int((frac * 24 - hours) * 60)
    seconds = int(((frac * 24 - hours) * 60 - minutes) * 60)
    return datetime(int(year), int(month), int(day), hours, minutes, seconds)


def _sun_longitude(jdn: float) -> float:
    """
    Calculate the sun's ecliptic longitude at a given Julian Day Number.
    Returns degrees (0-360).
    """
    D = jdn - 2451545.0  # Days from J2000.0
    
    # Mean anomaly (degrees)
    M = 357.5291 + 0.98560028 * D
    M = M % 360
    
    # Mean longitude (degrees)
    L0 = 280.46646 + 0.98564736 * D
    L0 = L0 % 360
    
    # Equation of center
    C = (1.914602 - 0.004817 * D / 36525 - 0.000014 * (D / 36525) ** 2) * math.sin(math.radians(M))
    C += (0.019993 - 0.000101 * D / 36525) * math.sin(math.radians(2 * M))
    C += 0.000289 * math.sin(math.radians(3 * M))
    
    # True longitude
    sun_lon = L0 + C
    
    # Apply nutation correction
    # Omega (Moon's ascending node)
    Omega = 125.04 - 0.052954 * D
    sun_lon -= 0.00569 + 0.00478 * math.sin(math.radians(Omega))
    
    return sun_lon % 360


def _find_solar_term_date(year: int, target_longitude: float) -> datetime:
    """
    Find the date when the sun reaches a specific ecliptic longitude.
    Uses binary search for precision.
    """
    # Approximate: each solar term is about 15.218 days apart
    # Start from vernal equinox of the year (around Mar 20)
    # Use mean anomaly to get approximate JDN
    
    # Start roughly from Jan 1 of the year
    start_jdn = _julian_day_number(year, 1, 1)
    
    # Search forward until we find the right longitude
    # The sun moves ~1 degree per day, so search range is about 365 days
    lo, hi = start_jdn, start_jdn + 370
    
    # First, find a range that brackets the target longitude
    for _ in range(50):
        mid = (lo + hi) / 2
        lon = _sun_longitude(mid)
        diff = (lon - target_longitude) % 360
        
        if diff <= 180:
            # Target is ahead
            hi = mid
        else:
            lo = mid
        
        if hi - lo < 0.001:  # Within ~1.5 minutes
            break
    
    jdn = (lo + hi) / 2
    return _jdn_to_datetime(jdn)


def get_lichun_date(year: int) -> datetime:
    """Get the exact datetime of 立春 (Start of Spring) for a given year.
    立春 = sun at 315° longitude."""
    return _find_solar_term_date(year, 315)


def get_12_jie_dates(year: int) -> List[Tuple[str, datetime]]:
    """Get the 12 '节' (major solar terms that define month boundaries) for a given year.
    Returns list of (name, datetime) sorted chronologically.
    
    The 12 节:
    立春(315°), 惊蛰(345°), 清明(15°), 立夏(45°),
    芒种(75°), 小暑(105°), 立秋(135°), 白露(165°),
    寒露(195°), 立冬(225°), 大雪(255°), 小寒(285°)
    """
    longitudes = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285]
    results = []
    
    for lon in longitudes:
        dt = _find_solar_term_date(year, lon)
        results.append((dt, lon))
    
    # Sort by datetime
    results.sort(key=lambda x: x[0])
    
    # Map to names
    named = []
    for dt, lon in results:
        idx = [315, 345, 15, 45, 75, 105, 135, 165, 195, 225, 255, 285].index(lon)
        named.append((MONTH_JIE[idx], dt))
    
    return named


def get_year_pillar(year: int, birth_date: date) -> Tuple[int, int]:
    """
    Determine the year pillar (年柱) based on 立春 boundary.
    Returns (gan_index, zhi_index) where 0=甲子, etc.
    
    立春 before birth_date → year stem/branch is for this year
    立春 after birth_date → year stem/branch is for previous year
    """
    lichun = get_lichun_date(year).date()
    
    if birth_date < lichun:
        # Use previous year
        actual_year = year - 1
    else:
        actual_year = year
    
    gan = (actual_year - 4) % 10  # 甲=0
    zhi = (actual_year - 4) % 12  # 子=0
    
    return gan, zhi


def get_month_pillar(year: int, birth_date: date, year_gan: int) -> Tuple[int, int]:
    """
    Determine the month pillar (月柱).
    First find which 节 period the birth date falls in, then calculate month stem with 五虎遁.
    
    Returns (gan_index, zhi_index).
    """
    # Get the 12 节 dates for this year
    # We need dates from both the previous year (小寒 might be in Jan) and current year
    jie_dates = get_12_jie_dates(year)
    
    # Also get 小寒 from next year (it might be in Jan of next year and be the boundary for 丑月)
    # Actually, the 12 节 cycle goes: 立春(寅) → 惊蛰(卯) → ... → 小寒(丑)
    # 小寒 of year Y+1 defines the start of 丑月 which is the 12th month of year Y
    
    # Let's build the full cycle: 小寒(Y) to 小寒(Y+1) defines the 12 months
    # 小寒 of current year marks the start of 丑月 of the PREVIOUS year's cycle
    
    # Get 小寒 of the next year
    jie_dates_next = get_12_jie_dates(year + 1)
    
    # 小寒(285°) comes before 立春(315°) in the cycle, so in get_12_jie_dates for year Y,
    # the first entry is 小寒 (around Jan 5-6 of year Y)
    # But in our 12-month cycle for Ba Zi, 小寒 starts 丑月 (12th month of PREVIOUS year)
    
    # Actually let me reconsider. The 节 cycle in chronological order:
    # 小寒(Jan 5-6), 立春(Feb 4), 惊蛰(Mar 6), 清明(Apr 5), 立夏(May 6),
    # 芒种(Jun 6), 小暑(Jul 7), 立秋(Aug 7), 白露(Sep 8), 寒露(Oct 8),
    # 立冬(Nov 7), 大雪(Dec 7)
    
    # In the 八字 system:
    # 寅月 = 立春~惊蛰, 卯月 = 惊蛰~清明, ..., 丑月 = 小寒~立春
    
    # So for each year, the 12 months of that year's cycle run from:
    # 立春(year) to 立春(year+1)
    
    # Let me get 立春 of the next year as the end boundary
    lichun_next = get_lichun_date(year + 1).date()
    
    # Create month boundary list: (jie_start_date, branch_index)
    # 立春→寅(2), 惊蛰→卯(3), ..., 小寒→丑(1)
    boundaries = []
    for name, dt in jie_dates:
        if name == '立春':
            boundaries.append((dt.date(), 2))  # 寅=2
        elif name == '惊蛰':
            boundaries.append((dt.date(), 3))  # 卯=3
        elif name == '清明':
            boundaries.append((dt.date(), 4))  # 辰=4
        elif name == '立夏':
            boundaries.append((dt.date(), 5))  # 巳=5
        elif name == '芒种':
            boundaries.append((dt.date(), 6))  # 午=6
        elif name == '小暑':
            boundaries.append((dt.date(), 7))  # 未=7
        elif name == '立秋':
            boundaries.append((dt.date(), 8))  # 申=8
        elif name == '白露':
            boundaries.append((dt.date(), 9))  # 酉=9
        elif name == '寒露':
            boundaries.append((dt.date(), 10)) # 戌=10
        elif name == '立冬':
            boundaries.append((dt.date(), 11)) # 亥=11
        elif name == '大雪':
            boundaries.append((dt.date(), 0))  # 子=0
        elif name == '小寒':
            boundaries.append((dt.date(), 1))  # 丑=1
    
    boundaries.sort(key=lambda x: x[0])
    
    # The first 小寒 of the year list actually belongs to the 丑月 of the previous year's cycle
    # We need to find which boundary the birth_date falls between
    # From 立春(year) to 立春(year+1)
    
    if birth_date < boundaries[0][0]:
        # Before 立春 → should be 丑月 of previous year
        # For 丑月, branch = 1 (丑)
        month_zhi = 1
    else:
        month_zhi = 1  # default: 丑
        for i, (bd, zhi) in enumerate(boundaries):
            if i < len(boundaries) - 1:
                if bd <= birth_date < boundaries[i + 1][0]:
                    month_zhi = zhi
                    break
            else:
                if bd <= birth_date < lichun_next:
                    month_zhi = zhi
                    break
    
    # 五虎遁: calculate month stem from year stem
    # 甲己之年丙作首 (year_gan 0 or 5 → month starts with 丙=2)
    # 乙庚之岁戊为头 (year_gan 1 or 6 → month starts with 戊=4)
    # 丙辛之岁寻庚上 (year_gan 2 or 7 → month starts with 庚=6)
    # 丁壬壬寅顺水流 (year_gan 3 or 8 → month starts with 壬=8)
    # 若问戊癸何处起，甲寅之上好追求 (year_gan 4 or 9 → month starts with 甲=0)
    
    wuhudun_start = {
        0: 2,  # 甲年 → 丙
        5: 2,  # 己年 → 丙
        1: 4,  # 乙年 → 戊
        6: 4,  # 庚年 → 戊
        2: 6,  # 丙年 → 庚
        7: 6,  # 辛年 → 庚
        3: 8,  # 丁年 → 壬
        8: 8,  # 壬年 → 壬
        4: 0,  # 戊年 → 甲
        9: 0,  # 癸年 → 甲
    }
    
    start_gan = wuhudun_start[year_gan]
    # 寅月(立春) = start_gan, 卯月 = start_gan+1, ...
    # month_zhi: 寅=2, 卯=3, ..., 丑=1
    # offset from 寅: (month_zhi - 2) % 12
    month_gan = (start_gan + (month_zhi - 2) % 12) % 10
    
    return month_gan, month_zhi


def get_day_pillar(birth_date: date) -> Tuple[int, int]:
    """
    Determine the day pillar (日柱) using a known reference date.
    Reference: 1900-01-01 = 甲戌日 (sexagenary index 10, where 甲子=0)
    
    Returns (gan_index, zhi_index).
    """
    ref_date = date(1900, 1, 1)
    ref_index = 10  # 甲戌日 = index 10
    
    delta = (birth_date - ref_date).days
    day_index = (ref_index + delta) % 60
    # Ensure positive
    day_index = day_index % 60
    
    gan = day_index % 10
    zhi = day_index % 12
    
    return gan, zhi


def get_hour_pillar(hour: int, minute: int, day_gan: int) -> Tuple[int, int]:
    """
    Determine the hour pillar (时柱) based on birth time and 五鼠遁.
    
    时支:
    子时: 23:00-00:59
    丑时: 01:00-02:59
    ...
    亥时: 21:00-22:59
    
    Returns (gan_index, zhi_index).
    """
    # Determine 时支
    if hour == 23:
        hour_zhi = 0  # 子时 (23:00-23:59)
    elif hour >= 0 and hour <= 0:
        hour_zhi = 0  # 子时 (00:00-00:59)
    elif 1 <= hour <= 2:
        hour_zhi = 1  # 丑时
    elif 3 <= hour <= 4:
        hour_zhi = 2  # 寅时
    elif 5 <= hour <= 6:
        hour_zhi = 3  # 卯时
    elif 7 <= hour <= 8:
        hour_zhi = 4  # 辰时
    elif 9 <= hour <= 10:
        hour_zhi = 5  # 巳时
    elif 11 <= hour <= 12:
        hour_zhi = 6  # 午时
    elif 13 <= hour <= 14:
        hour_zhi = 7  # 未时
    elif 15 <= hour <= 16:
        hour_zhi = 8  # 申时
    elif 17 <= hour <= 18:
        hour_zhi = 9  # 酉时
    elif 19 <= hour <= 20:
        hour_zhi = 10 # 戌时
    elif 21 <= hour <= 22:
        hour_zhi = 11 # 亥时
    else:
        hour_zhi = 0  # Default to 子时
    
    # 五鼠遁: calculate hour stem from day stem
    # 甲己还加甲 (day_gan 0 or 5 → hour starts with 甲=0)
    # 乙庚丙作初 (day_gan 1 or 6 → hour starts with 丙=2)
    # 丙辛从戊起 (day_gan 2 or 7 → hour starts with 戊=4)
    # 丁壬庚子居 (day_gan 3 or 8 → hour starts with 庚=6)
    # 戊癸何方发，壬子是真途 (day_gan 4 or 9 → hour starts with 壬=8)
    
    wushudun_start = {
        0: 0,  # 甲日
        5: 0,  # 己日
        1: 2,  # 乙日
        6: 2,  # 庚日
        2: 4,  # 丙日
        7: 4,  # 辛日
        3: 6,  # 丁日
        8: 6,  # 壬日
        4: 8,  # 戊日
        9: 8,  # 癸日
    }
    
    start_gan = wushudun_start[day_gan]
    # 子时(0) = start_gan, 丑时(1) = start_gan+1, ...
    hour_gan = (start_gan + hour_zhi) % 10
    
    return hour_gan, hour_zhi


def calculate_four_pillars(year: int, month: int, day: int, hour: int, minute: int = 0) -> dict:
    """
    Calculate the Four Pillars (四柱八字) for a given birth datetime.
    
    Returns dict with:
        - year: (gan, zhi, gan_char, zhi_char)
        - month: (gan, zhi, gan_char, zhi_char)
        - day: (gan, zhi, gan_char, zhi_char)
        - hour: (gan, zhi, gan_char, zhi_char)
        - day_gan_shi_shen: day heavenly stem as reference for 十神
    """
    birth_date = date(year, month, day)
    
    # Year pillar
    year_gan, year_zhi = get_year_pillar(year, birth_date)
    
    # Month pillar (needs year_gan for 五虎遁)
    month_gan, month_zhi = get_month_pillar(year, birth_date, year_gan)
    
    # Day pillar
    day_gan, day_zhi = get_day_pillar(birth_date)
    
    # Hour pillar (needs day_gan for 五鼠遁)
    hour_gan, hour_zhi = get_hour_pillar(hour, minute, day_gan)
    
    return {
        'year': {
            'gan': year_gan,
            'zhi': year_zhi,
            'gan_char': TIAN_GAN[year_gan],
            'zhi_char': DI_ZHI[year_zhi],
        },
        'month': {
            'gan': month_gan,
            'zhi': month_zhi,
            'gan_char': TIAN_GAN[month_gan],
            'zhi_char': DI_ZHI[month_zhi],
        },
        'day': {
            'gan': day_gan,
            'zhi': day_zhi,
            'gan_char': TIAN_GAN[day_gan],
            'zhi_char': DI_ZHI[day_zhi],
        },
        'hour': {
            'gan': hour_gan,
            'zhi': hour_zhi,
            'gan_char': TIAN_GAN[hour_gan],
            'zhi_char': DI_ZHI[hour_zhi],
        },
        'day_gan': day_gan,
        'day_gan_char': TIAN_GAN[day_gan],
    }


# Quick test
if __name__ == '__main__':
    # Test with a well-known date
    result = calculate_four_pillars(1990, 1, 1, 12, 0)
    print(f"年柱: {result['year']['gan_char']}{result['year']['zhi_char']}")
    print(f"月柱: {result['month']['gan_char']}{result['month']['zhi_char']}")
    print(f"日柱: {result['day']['gan_char']}{result['day']['zhi_char']}")
    print(f"时柱: {result['hour']['gan_char']}{result['hour']['zhi_char']}")
    print(f"日干: {result['day_gan_char']}")
