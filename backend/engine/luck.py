"""
大运 (Luck Cycles) calculation for Ba Zi.
Determines the starting age and 10-year luck cycles.
"""

from backend.data.solar_terms import TIAN_GAN, DI_ZHI


def calculate_dayun(year_gan: int, year_zhi: int, gender: str,
                    birth_year: int, birth_month: int, birth_day: int) -> dict:
    """
    Calculate 大运 (Major Luck Cycles).
    
    Rules:
    1. 阳男阴女 → 顺排 (forward)
    2. 阴男阳女 → 逆排 (backward)
    3. Starting age determined by distance to the next/previous 节 (solar term)
    
    Args:
        year_gan: Year heavenly stem index
        year_zhi: Year earthly branch index (0-11)
        gender: '男' or '女'
        birth_year, birth_month, birth_day: birth date
    
    Returns:
        dict with starting_age, luck_cycles list
    """
    year_yang = year_gan % 2 == 0  # 阳年
    is_male = gender == '男'
    
    # 阳男阴女 → 顺排, 阴男阳女 → 逆排
    forward = (year_yang and is_male) or (not year_yang and not is_male)
    
    # Calculate the first 大运 pillar
    # 顺排: next month pillar + 1, +2, ...
    # 逆排: previous month pillar - 1, -2, ...
    
    # For starting age, we calculate distance to next/previous 节
    # This is a complex calculation involving solar term dates
    # For now, we'll use a standard approximation:
    # 3 days in the calendar = 1 year of luck
    
    # Get the month pillar (月柱 where 寅=2, 卯=3, ..., 丑=1)
    # We need to determine which 节 period the birth date falls in
    # The 节 for the next month is determined by forward/backward direction
    
    from backend.data.solar_terms import get_12_jie_dates, get_lichun_date
    from datetime import date
    
    birth_date = date(birth_year, birth_month, birth_day)
    
    # Get all 节 dates around the birth date
    # We need to check the current year and possibly next/prev year
    jie_dates_this = get_12_jie_dates(birth_year)
    jie_dates_next = get_12_jie_dates(birth_year + 1)
    jie_dates_prev = get_12_jie_dates(birth_year - 1)
    
    # Build a sorted list of all 节 dates
    all_jie = []
    for name, dt in jie_dates_prev:
        all_jie.append((dt, name))
    for name, dt in jie_dates_this:
        all_jie.append((dt, name))
    for name, dt in jie_dates_next:
        all_jie.append((dt, name))
    all_jie.sort(key=lambda x: x[0])
    
    # Find the position of the birth date in the solar term cycle
    if forward:
        # Find the NEXT 节 after birth
        next_jie = None
        for dt, name in all_jie:
            if dt.date() > birth_date:
                next_jie = (dt, name)
                break
        
        if next_jie:
            days_to_next = (next_jie[0].date() - birth_date).days
        else:
            days_to_next = 0
        
        # Starting age: 3 days = 1 year, 1 day = 4 months
        starting_years = days_to_next // 3
        starting_months = (days_to_next % 3) * 4
        starting_days = 0
        # Cap at reasonable values
        if starting_years > 20:
            starting_years = 20
            starting_months = 0
        
        # Starting pillar: find which month the birth is in, then go to the next month
        # Find current month based on birth date vs 节
        # ... (simplified for now)
        
        # First luck cycle pillar = base_month + 1
        base_month_zhi = 2  # Default 寅
        for i, (dt, name) in enumerate(all_jie):
            if i + 1 < len(all_jie) and dt.date() <= birth_date < all_jie[i + 1][0].date():
                # Map 节 to month branch
                jie_to_zhi = {
                    '立春': 2, '惊蛰': 3, '清明': 4, '立夏': 5, '芒种': 6, '小暑': 7,
                    '立秋': 8, '白露': 9, '寒露': 10, '立冬': 11, '大雪': 0, '小寒': 1,
                }
                base_month_zhi = jie_to_zhi.get(name, 2)
                break
        else:
            # Before 立春 = 丑月 of previous year
            base_month_zhi = 1
        
        # First luck cycle month
        if forward:
            start_month_zhi = (base_month_zhi + 1) % 12
        else:
            start_month_zhi = (base_month_zhi - 1) % 12
    else:
        # Backward: find the PREVIOUS 节 before birth
        prev_jie = None
        for dt, name in reversed(all_jie):
            if dt.date() < birth_date:
                prev_jie = (dt, name)
                break
        
        if prev_jie:
            days_to_prev = (birth_date - prev_jie[0].date()).days
        else:
            days_to_prev = 0
        
        # Starting age: 3 days = 1 year, 1 day = 4 months
        starting_years = days_to_prev // 3
        starting_months = (days_to_prev % 3) * 4
        starting_days = 0
        if starting_years > 20:
            starting_years = 20
            starting_months = 0
        
        # Find current month
        base_month_zhi = 2
        jie_to_zhi = {
            '立春': 2, '惊蛰': 3, '清明': 4, '立夏': 5, '芒种': 6, '小暑': 7,
            '立秋': 8, '白露': 9, '寒露': 10, '立冬': 11, '大雪': 0, '小寒': 1,
        }
        for i, (dt, name) in enumerate(all_jie):
            if i + 1 < len(all_jie) and dt.date() <= birth_date < all_jie[i + 1][0].date():
                base_month_zhi = jie_to_zhi.get(name, 2)
                break
        else:
            base_month_zhi = 1
        
        start_month_zhi = (base_month_zhi - 1) % 12
    
    # Cap starting age at reasonable values
    starting_age = starting_years  # for backward compatibility
    
    # Generate 8 luck cycles (80 years)
    luck_cycles = []
    
    # Calculate the month stem (五虎遁 from year stem)
    # Same as wuhudun in pillar calculation
    wuhudun_start = {
        0: 2, 5: 2, 1: 4, 6: 4, 2: 6, 7: 6, 3: 8, 8: 8, 4: 0, 9: 0,
    }
    start_gan = wuhudun_start[year_gan]
    
    # The starting month stem for the first luck cycle
    # The starting month should be either the month after (forward) or before (backward) the birth month
    # Actually, the first 大运 pillar starts from the 月柱 of the next/previous 节 cycle
    
    # Simplified: use base as the start and apply direction
    base_gan = (start_gan + (start_month_zhi - 2) % 12) % 10
    
    age = starting_age
    for i in range(8):
        if forward:
            gan = (base_gan + i) % 10
            zhi = (start_month_zhi + i) % 12
        else:
            gan = (base_gan - i) % 10
            zhi = (start_month_zhi - i) % 12
        
        luck_cycles.append({
            'age_range': f'{age}-{age + 9}岁',
            'start_age': age,
            'gan': gan,
            'zhi': zhi,
            'gan_char': TIAN_GAN[gan],
            'zhi_char': DI_ZHI[zhi],
        })
        age += 10
    
    return {
        'forward': forward,
        'starting_age': starting_age,
        'starting_years': starting_years,
        'starting_months': starting_months,
        'luck_cycles': luck_cycles,
    }
