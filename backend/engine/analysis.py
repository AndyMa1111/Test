"""
综合分析模块 - 整合排盘、十神、大运、调候、旺衰等分析结果。
"""

from backend.data.solar_terms import (
    calculate_four_pillars, TIAN_GAN, DI_ZHI, DI_ZHI_ZANG_GAN,
)
from backend.engine.tenshen import (
    calculate_all_shi_shen, get_zanggan_shi_shen, get_shi_shen_for_gan,
)
from backend.engine.luck import calculate_dayun
from backend.engine.tiaohou import get_tiaohou


# 旺相休囚死 table: [month_index][element_index] -> status
# Elements: 0=木, 1=火, 2=土, 3=金, 4=水
# Months: 0=子(冬), 1=丑(冬末), 2=寅(春), 3=卯(春), 4=辰(春末),
#          5=巳(夏), 6=午(夏), 7=未(夏末), 8=申(秋), 9=酉(秋),
#          10=戌(秋末), 11=亥(冬)
# Status: 0=旺, 1=相, 2=休, 3=囚, 4=死
WANG_XIANG_TABLE = {
    # 寅卯(春): 木旺, 火相, 水休, 金囚, 土死
    2: [0, 1, 4, 3, 2],  # 寅月 - 木旺
    3: [0, 1, 4, 3, 2],  # 卯月 - 木旺
    # 辰(春末土旺): 土旺, 金相, 火休, 木囚, 水死
    4: [3, 2, 0, 1, 4],  # 辰月 - 土旺 (四土月)
    # 巳午(夏): 火旺, 土相, 木休, 水囚, 金死
    5: [2, 0, 1, 4, 3],  # 巳月 - 火旺
    6: [2, 0, 1, 4, 3],  # 午月 - 火旺
    # 未(夏末土旺): 土旺, 金相, 火休, 木囚, 水死
    7: [3, 2, 0, 1, 4],  # 未月 - 土旺 (四土月)
    # 申酉(秋): 金旺, 水相, 土休, 火囚, 木死
    8: [4, 3, 2, 0, 1],  # 申月 - 金旺
    9: [4, 3, 2, 0, 1],  # 酉月 - 金旺
    # 戌(秋末土旺): 土旺, 金相, 火休, 木囚, 水死
    10: [3, 2, 0, 1, 4], # 戌月 - 土旺 (四土月)
    # 亥子(冬): 水旺, 木相, 金休, 土囚, 火死
    11: [1, 4, 3, 2, 0], # 亥月 - 水旺
    0: [1, 4, 3, 2, 0],  # 子月 - 水旺
    # 丑(冬末土旺): 土旺, 金相, 火休, 木囚, 水死
    1: [3, 2, 0, 1, 4],  # 丑月 - 土旺 (四土月)
}

WANG_XIANG_NAMES = ['旺', '相', '休', '囚', '死']

# Element names
ELEMENT_NAMES = ['木', '火', '土', '金', '水']

# 天干对应的五行
GAN_ELEMENT = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]  # 甲乙木, 丙丁火, 戊己土, 庚辛金, 壬癸水
# 地支对应的五行
ZHI_ELEMENT = [4, 2, 0, 0, 2, 1, 1, 2, 3, 3, 2, 4]  # 子水, 丑土, 寅木, 卯木, 辰土, 巳火, 午火, 未土, 申金, 酉金, 戌土, 亥水


def _element_index_from_gan(gan_idx: int) -> int:
    return GAN_ELEMENT[gan_idx]


def _element_index_from_zhi(zhi_idx: int) -> int:
    return ZHI_ELEMENT[zhi_idx]


def get_wangxiang(element_idx: int, month_zhi: int) -> str:
    """Get the 旺相休囚死 status for an element in a given month."""
    status_idx = WANG_XIANG_TABLE[month_zhi][element_idx]
    return WANG_XIANG_NAMES[status_idx]


def analyze_full_bazi(year: int, month: int, day: int, hour: int, minute: int = 0,
                      gender: str = '男', calendar: str = '公历') -> dict:
    """
    Full Ba Zi analysis for a birth datetime.
    
    Returns comprehensive analysis dict.
    """
    # 1. Calculate four pillars
    pillars = calculate_four_pillars(year, month, day, hour, minute)
    
    day_gan = pillars['day']['gan']
    day_gan_char = pillars['day']['gan_char']
    month_zhi = pillars['month']['zhi']
    
    # 2. Calculate ten gods for each pillar stem
    shi_shen_result = calculate_all_shi_shen(day_gan, pillars)
    
    # 3. Get 藏干 with ten gods for each pillar
    zanggan_analysis = {}
    for pillar_name in ['year', 'month', 'day', 'hour']:
        zhi = pillars[pillar_name]['zhi']
        zhi_char = pillars[pillar_name]['zhi_char']
        zanggan_list = get_zanggan_shi_shen(day_gan, zhi)
        zanggan_analysis[pillar_name] = {
            'zhi_char': zhi_char,
            'zanggan': zanggan_list,
        }
    
    # 4. Check 月令透干成格
    # Which hidden stems in the month branch are also in the heavenly stems?
    month_zhi_char = pillars['month']['zhi_char']
    month_hidden = DI_ZHI_ZANG_GAN[month_zhi_char]
    month_hidden_indexes = []
    for gan_char in month_hidden:
        for key in ['year', 'month', 'hour']:
            if pillars[key]['gan_char'] == gan_char:
                month_hidden_indexes.append({
                    'gan_char': gan_char,
                    'position': key,
                })
    
    # 月令透出 = month hidden stem appears in year/month/hour stem
    month_tou_chu = []
    for item in month_hidden_indexes:
        gan_idx = {char: i for i, char in enumerate(TIAN_GAN)}[item['gan_char']]
        shi_shen = get_shi_shen_for_gan(day_gan, gan_idx)
        month_tou_chu.append({
            'gan_char': item['gan_char'],
            'position': item['position'],
            'shi_shen': shi_shen,
        })
    
    # 格局分析
    geju = []
    geju_names = {
        '正官': '正官格', '七杀': '七杀格',
        '正印': '正印格', '偏印': '偏印格',
        '正财': '正财格', '偏财': '偏财格',
        '伤官': '伤官格', '食神': '食神格',
        '比肩': '建禄格', '劫财': '建禄格',
    }
    for item in month_tou_chu:
        geju_name = geju_names.get(item['shi_shen'], f"{item['shi_shen']}格")
        geju.append({
            'shi_shen': item['shi_shen'],
            'geju_name': geju_name,
            'gan_char': item['gan_char'],
            'position': item['position'],
        })
    
    if not geju:
        geju.append({'geju_name': '暂无月令透干成格（待进一步分析）', 'shi_shen': '', 'gan_char': '', 'position': ''})
    
    # 5. Calculate 旺相休囚死 for each element
    wangxiang = {}
    for i, elem_name in enumerate(ELEMENT_NAMES):
        status = get_wangxiang(i, month_zhi)
        wangxiang[elem_name] = status
    
    # 6. Calculate 旺衰 for each pillar stem
    stem_wangshuai = {}
    for pillar_name in ['year', 'month', 'day', 'hour']:
        gan = pillars[pillar_name]['gan']
        elem = _element_index_from_gan(gan)
        elem_name = ELEMENT_NAMES[elem]
        status = get_wangxiang(elem, month_zhi)
        stem_wangshuai[pillar_name] = {
            'gan_char': pillars[pillar_name]['gan_char'],
            'element': elem_name,
            'wangxiang': status,
        }
    
    # 7. 调候用神分析
    tiaohou = get_tiaohou(day_gan, month_zhi)
    qiongtong_text = None
    tiyao_entry = None
    from backend.engine.tiaohou import get_qiongtong_text, get_bazi_tiyao_for_hour
    qiongtong_text = get_qiongtong_text(day_gan, month_zhi)
    tiyao_entry = get_bazi_tiyao_for_hour(day_gan, month_zhi, pillars['hour']['gan'], pillars['hour']['zhi'])
    
    # 8. 大运
    luck = calculate_dayun(
        pillars['year']['gan'],
        pillars['year']['zhi'],
        gender,
        year, month, day,
    )
    
    # 9. Build the eight characters string
    bazi_str = f"{pillars['year']['gan_char']}{pillars['year']['zhi_char']} " \
               f"{pillars['month']['gan_char']}{pillars['month']['zhi_char']} " \
               f"{pillars['day']['gan_char']}{pillars['day']['zhi_char']} " \
               f"{pillars['hour']['gan_char']}{pillars['hour']['zhi_char']}"
    
    result = {
        'birth_date': f'{year}年{month}月{day}日 {hour}:{minute:02d}',
        'gender': gender,
        'bazi': {
            'year': {
                'gan': pillars['year']['gan_char'],
                'zhi': pillars['year']['zhi_char'],
                'shi_shen': shi_shen_result['year']['gan_shi_shen'],
                'yin_yang': ['阳', '阴'][pillars['year']['gan'] % 2],
            },
            'month': {
                'gan': pillars['month']['gan_char'],
                'zhi': pillars['month']['zhi_char'],
                'shi_shen': shi_shen_result['month']['gan_shi_shen'],
                'yin_yang': ['阳', '阴'][pillars['month']['gan'] % 2],
            },
            'day': {
                'gan': pillars['day']['gan_char'],
                'zhi': pillars['day']['zhi_char'],
                'shi_shen': '日主',
                'yin_yang': ['阳', '阴'][pillars['day']['gan'] % 2],
            },
            'hour': {
                'gan': pillars['hour']['gan_char'],
                'zhi': pillars['hour']['zhi_char'],
                'shi_shen': shi_shen_result['hour']['gan_shi_shen'],
                'yin_yang': ['阳', '阴'][pillars['hour']['gan'] % 2],
            },
        },
        'zanggan': zanggan_analysis,
        'wangshuai': wangxiang,
        'stem_wangshuai': stem_wangshuai,
        'tiaohou': tiaohou,
        'qiongtong_text': qiongtong_text,
        'tiyao_entry': tiyao_entry,
        'geju': geju,
        'month_tou_chu': month_tou_chu,
        'dayun': luck,
    }
    
    # 10. Generate narrative report using rule-based algorithm (instant)
    report = generate_report(result, pillars, day_gan, month_zhi)
    result['report'] = report
    
    return result


def generate_report(result: dict, pillars: dict, day_gan: int, month_zhi: int) -> dict:
    """Generate a structured narrative Ba Zi analysis report.
    Follows the teacher's order: 调候 → 格局 → 旺气平衡 → 日主 → 总结
    """
    bazi = result['bazi']
    day_gan_char = pillars['day']['gan_char']
    month_zhi_char = pillars['month']['zhi_char']
    
    # ===== 1. 基本信息 =====
    month_names = {
        2: '寅', 3: '卯', 4: '辰', 5: '巳', 6: '午', 7: '未',
        8: '申', 9: '酉', 10: '戌', 11: '亥', 0: '子', 1: '丑',
    }
    season_map = {
        2: '春', 3: '春', 4: '春末', 5: '夏', 6: '夏', 7: '夏末',
        8: '秋', 9: '秋', 10: '秋末', 11: '冬', 0: '冬', 1: '冬末',
    }
    day_elements = ['木', '火', '土', '金', '水']
    gan_element_map = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
    day_element = day_elements[gan_element_map[day_gan]]
    
    month_name = month_names[month_zhi]
    season = season_map[month_zhi]
    
    sections = []
    
    # ===== 2. 调候分析 =====
    tiaohou = result.get('tiaohou')
    tiaohou_section = {
        'title': '一、调候分析（健康）',
        'content': [],
        'severity': 'normal',
    }
    
    # Determine if climate adjustment is critical
    # Summer wood (甲/乙 in 巳/午/未) and winter metal (庚/辛 in 亥/子/丑) are most important
    day_gan_stem = TIAN_GAN[day_gan]
    is_wood_in_summer = day_gan_stem in ['甲', '乙'] and month_zhi in [5, 6, 7]
    is_metal_in_winter = day_gan_stem in ['庚', '辛'] and month_zhi in [0, 1, 11]
    
    if is_wood_in_summer:
        tiaohou_section['severity'] = 'critical'
        tiaohou_section['content'].append(
            f'【重要】日主{day_gan_char}为{day_element}，生于{month_name}月（{season}），'
            f'属于"夏令木"，调候至关紧要。夏木最需水来滋润降温，若无水则健康易有隐患。'
        )
    elif is_metal_in_winter:
        tiaohou_section['severity'] = 'critical'
        tiaohou_section['content'].append(
            f'【重要】日主{day_gan_char}为{day_element}，生于{month_name}月（{season}），'
            f'属于"冬令金"，调候至关紧要。冬金最需火来温暖，若无火则健康易有隐患。'
        )
    else:
        tiaohou_section['content'].append(
            f'日主{day_gan_char}为{day_element}，生于{month_name}月（{season}），'
            f'调候需求一般，但若八字整体偏寒或偏热仍需注意。'
        )
    
    # Check if tiaohou gods are effectively placed
    effective_gods = []
    missing_gods = []
    
    if tiaohou and tiaohou.get('key_gods'):
        key_gods = tiaohou['key_gods'][:3]
        god_names = [g['gan_char'] for g in key_gods]
        
        # Check if any key god appears in effective positions
        # (1) year/month/hour heavenly stem, (2) hour branch's 本气
        effective_positions = ['year', 'month', 'hour']
        effective_gods = []
        missing_gods = []
        
        # Get hour branch's 本气 (first hidden stem)
        from backend.data.solar_terms import DI_ZHI_ZANG_GAN
        hour_zhi_char = result['bazi']['hour']['zhi']
        hour_zhi_benqi = DI_ZHI_ZANG_GAN.get(hour_zhi_char, [''])[0]
        
        for god in god_names:
            found = False
            # Check heavenly stems
            for pos in effective_positions:
                if result['bazi'].get(pos, {}).get('gan') == god:
                    effective_gods.append(f'{god}（{pos}柱天干）')
                    found = True
                    break
            # Check hour branch's 本气
            if not found and god == hour_zhi_benqi:
                effective_gods.append(f'{god}（时支{hour_zhi_char}本气）')
                found = True
            if not found:
                missing_gods.append(god)
        
        if effective_gods:
            tiaohou_section['content'].append(
                f'穷通宝鉴云：{tiaohou.get("summary", "")[:100]}……'
            )
            tiaohou_section['content'].append(
                f'调候用神 {", ".join(god_names)} 中，{", ".join(effective_gods)} 出现在有效位置'
                f'（年/月/时天干或时支本气），在原局中能起到调候作用，健康方面有保障。'
            )
        else:
            tiaohou_section['content'].append(
                f'穷通宝鉴建议用神为 {", ".join(god_names)}，但在原局有效位置'
                f'（年/月/时天干）均未出现，需大运天干出现方能起到调候作用。'
            )
        
        if missing_gods:
            tiaohou_section['content'].append(
                f'缺失：{", ".join(missing_gods)}在原局有效位置未透出，相关方面需后天注意。'
            )
    elif tiaohou:
        tiaohou_section['content'].append(
            f'穷通宝鉴提示：{tiaohou.get("summary", "")[:150]}……'
        )
    else:
        tiaohou_section['content'].append('穷通宝鉴未提供此组合的详细调候参考。')
    
    sections.append(tiaohou_section)
    
    # ===== 3. 格局分析（事业财富） =====
    geju_section = {
        'title': '二、格局分析（事业财富）',
        'content': [],
    }
    
    geju = result.get('geju', [])
    has_geju = any(g.get('shi_shen') for g in geju)
    
    if has_geju:
        valid_geju = [g for g in geju if g.get('shi_shen')]
        for g in valid_geju:
            geju_section['content'].append(
                f'月令{month_zhi_char}中藏气{g["gan_char"]}透出在{g["position"]}柱天干，'
                f'形成{g["geju_name"]}。'
            )
        
        if len(valid_geju) >= 2:
            geju_section['content'].append(
                '多股气同时透出，构成双格。多重格局代表命主能力多元，'
                '但也需注意精力分散的问题。'
            )
    else:
        geju_section['content'].append(
            f'月令{month_zhi_char}的藏气均未透出天干（年/月/时柱），'
            f'暂无明显格局。格局未成不代表命不好，但需要到大运流年引动藏气时，'
            f'方可发挥该方面的潜力。'
        )
    
    # Analyze the strongest element
    wangshuai = result.get('wangshuai', {})
    strongest = '旺'
    strongest_elements = [e for e, s in wangshuai.items() if s == strongest]
    second_strong = '相'
    second_elements = [e for e, s in wangshuai.items() if s == second_strong]
    
    if strongest_elements:
        geju_section['content'].append(
            f'当前月令为{month_zhi_char}月（{season}），八字中【{",".join(strongest_elements)}】当令最旺，'
            f'【{",".join(second_elements)}】次旺。'
        )
    
    # Determine what balances the strong element
    controlling = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}
    produced = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
    
    balance_analysis = []
    for se in strongest_elements:
        controller = controlling[se]
        producer = produced[se]
        controller_status = wangshuai.get(controller, '')
        producer_status = wangshuai.get(producer, '')
        if controller_status in ['旺', '相']:
            balance_analysis.append(
                f'旺气{se}有{controller}（{controller_status}）来制衡，形成有效平衡。'
            )
        elif controller_status == '休':
            balance_analysis.append(
                f'旺气{se}虽有{controller}来制衡，但{controller}处于休地，力量不够。'
            )
        elif controller_status in ['囚', '死']:
            balance_analysis.append(
                f'旺气{se}的制衡五行{controller}处于弱地（{controller_status}），难以有效制约。'
            )
    
    if balance_analysis:
        geju_section['content'].extend(balance_analysis)
    
    sections.append(geju_section)
    
    # ===== 4. 日主分析（是否需要扶抑） =====
    rizhu_section = {
        'title': '三、日主分析',
        'content': [],
    }
    
    # Get day stem's element and its status
    day_elem_status = wangshuai.get(day_element, '')
    rizhu_section['content'].append(
        f'日主为{day_gan_char}（{day_element}），在{month_name}月处于"{day_elem_status}"的状态。'
    )
    
    # Check if day master needs balancing
    if day_elem_status in ['旺', '相']:
        rizhu_section['content'].append(
            f'日主{day_element}当令较旺，但是否需要扶抑取决于八字整体格局——'
            f'如果格局旺气需要日主来平衡，则身旺是好事；如果格局已经自平衡，则不必强求日主强弱。'
        )
    elif day_elem_status == '休':
        rizhu_section['content'].append(
            f'日主处于休地，力量有所不足。但若格局旺气不需要日主参与平衡，'
            f'则日主强弱不作为主要判断依据。'
        )
    elif day_elem_status in ['囚', '死']:
        rizhu_section['content'].append(
            f'日主处于囚/死地，在原局力量较弱。但如果八字格局旺气另有平衡之道，'
            f'日主弱也不影响富贵。'
        )
    
    sections.append(rizhu_section)
    
    # ===== 5. 综合分析 =====
    summary_section = {
        'title': '四、综合分析结论',
        'content': [],
    }
    
    # Check if tiaohou is critical and has no gods
    if (is_wood_in_summer or is_metal_in_winter) and not effective_gods:
        summary_section['content'].append(
            '【健康提醒】夏令木/冬令金无调候用神在有效位置，需注意健康养护。'
        )
    
    # Overall balance assessment
    if len(strongest_elements) >= 2:
        summary_section['content'].append(
            f'八字中{",".join(strongest_elements)}均当令，五行力量集中在旺气上，'
            f'八字气势偏向一方。能否富贵要看是否有其他五行来有效平衡这股旺气。'
        )
    elif len(strongest_elements) == 1:
        controller = controlling[strongest_elements[0]]
        controller_wx = wangshuai.get(controller, '')
        if controller_wx in ['旺', '相']:
            summary_section['content'].append(
                f'八字旺气在{strongest_elements[0]}，但有{controller}（{controller_wx}）来制衡，'
                f'形成有效的五行平衡格局，属于层次较高的命局。'
            )
        else:
            summary_section['content'].append(
                f'八字旺气在{strongest_elements[0]}，但制衡五行{controller}力量不足（{controller_wx}），'
                f'原局难以达到理想平衡，需要大运流年来引动制衡之力。'
            )
    
    # Luck cycle analysis
    dayun = result.get('dayun', {})
    luck_cycles = dayun.get('luck_cycles', [])
    if luck_cycles:
        first_cycle = luck_cycles[0]
        # Determine if first luck is helpful
        first_gan = first_cycle['gan']
        first_gan_element = day_elements[gan_element_map[first_gan]]
        summary_section['content'].append(
            f'命主{dayun.get("starting_age", 0)}岁起运，第一步大运为{first_cycle["gan_char"]}{first_cycle["zhi_char"]}'
            f'（{first_gan_element}运），大运走势将在后续逐年展现。'
        )
    
    sections.append(summary_section)
    
    return {'sections': sections}
