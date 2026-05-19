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



# 纳音表 (60甲子)
NAYIN_MAP = {}
_nayin_data = [
    ("甲子","乙丑","海中金"),("丙寅","丁卯","炉中火"),("戊辰","己巳","大林木"),
    ("庚午","辛未","路旁土"),("壬申","癸酉","剑锋金"),("甲戌","乙亥","山头火"),
    ("丙子","丁丑","涧下水"),("戊寅","己卯","城头土"),("庚辰","辛巳","白蜡金"),
    ("壬午","癸未","杨柳木"),("甲申","乙酉","泉中水"),("丙戌","丁亥","屋上土"),
    ("戊子","己丑","霹雳火"),("庚寅","辛卯","松柏木"),("壬辰","癸巳","长流水"),
    ("甲午","乙未","沙中金"),("丙申","丁酉","山下火"),("戊戌","己亥","平地木"),
    ("庚子","辛丑","壁上土"),("壬寅","癸卯","金箔金"),("甲辰","乙巳","覆灯火"),
    ("丙午","丁未","天河水"),("戊申","己酉","大驿土"),("庚戌","辛亥","钗钏金"),
    ("壬子","癸丑","桑柘木"),("甲寅","乙卯","大溪水"),("丙辰","丁巳","沙中土"),
    ("戊午","己未","天上火"),("庚申","辛酉","石榴木"),("壬戌","癸亥","大海水"),
]
for g1, g2, n in _nayin_data:
    NAYIN_MAP[g1] = n
    NAYIN_MAP[g2] = n

def get_nayin(gan: str, zhi: str) -> str:
    """Get 纳音 for a 干支 pair."""
    return NAYIN_MAP.get(gan + zhi, "")


# ─── 神煞计算 ───

# 三合局映射（用于桃花/驿马/华盖/劫煞/灾煞/岁煞/将星）
SAN_HE = {
    "寅": {"members": ["寅","午","戌"], "taohua": "卯", "yima": "申", "huagai": "戌",
           "jiesha": "亥", "zaisha": "子", "suisha": "丑", "jiangxing": "午"},
    "午": {"members": ["寅","午","戌"], "taohua": "卯", "yima": "申", "huagai": "戌",
           "jiesha": "亥", "zaisha": "子", "suisha": "丑", "jiangxing": "午"},
    "戌": {"members": ["寅","午","戌"], "taohua": "卯", "yima": "申", "huagai": "戌",
           "jiesha": "亥", "zaisha": "子", "suisha": "丑", "jiangxing": "午"},
    "巳": {"members": ["巳","酉","丑"], "taohua": "午", "yima": "亥", "huagai": "丑",
           "jiesha": "寅", "zaisha": "卯", "suisha": "辰", "jiangxing": "酉"},
    "酉": {"members": ["巳","酉","丑"], "taohua": "午", "yima": "亥", "huagai": "丑",
           "jiesha": "寅", "zaisha": "卯", "suisha": "辰", "jiangxing": "酉"},
    "丑": {"members": ["巳","酉","丑"], "taohua": "午", "yima": "亥", "huagai": "丑",
           "jiesha": "寅", "zaisha": "卯", "suisha": "辰", "jiangxing": "酉"},
    "申": {"members": ["申","子","辰"], "taohua": "酉", "yima": "寅", "huagai": "辰",
           "jiesha": "巳", "zaisha": "午", "suisha": "未", "jiangxing": "子"},
    "子": {"members": ["申","子","辰"], "taohua": "酉", "yima": "寅", "huagai": "辰",
           "jiesha": "巳", "zaisha": "午", "suisha": "未", "jiangxing": "子"},
    "辰": {"members": ["申","子","辰"], "taohua": "酉", "yima": "寅", "huagai": "辰",
           "jiesha": "巳", "zaisha": "午", "suisha": "未", "jiangxing": "子"},
    "亥": {"members": ["亥","卯","未"], "taohua": "子", "yima": "巳", "huagai": "未",
           "jiesha": "申", "zaisha": "酉", "suisha": "戌", "jiangxing": "卯"},
    "卯": {"members": ["亥","卯","未"], "taohua": "子", "yima": "巳", "huagai": "未",
           "jiesha": "申", "zaisha": "酉", "suisha": "戌", "jiangxing": "卯"},
    "未": {"members": ["亥","卯","未"], "taohua": "子", "yima": "巳", "huagai": "未",
           "jiesha": "申", "zaisha": "酉", "suisha": "戌", "jiangxing": "卯"},
}

# 天乙贵人: 日干 → 地支
TIANYI = {
    "甲": ("丑","未"),"戊": ("丑","未"),"庚": ("丑","未"),
    "乙": ("子","申"),"己": ("子","申"),
    "丙": ("亥","酉"),"丁": ("亥","酉"),
    "壬": ("卯","巳"),"癸": ("卯","巳"),
    "辛": ("午","寅"),
}

# 文昌贵人: 日干 → 地支
WENCHANG = {"甲":"巳","乙":"午","丙":"申","丁":"酉","戊":"申","己":"酉","庚":"亥","辛":"子","壬":"寅","癸":"卯"}

# 天德: 月支 → 所查(天干或地支)
TIANDE = {
    "寅":"丁","卯":"申","辰":"壬","巳":"辛","午":"亥","未":"甲",
    "申":"癸","酉":"寅","戌":"丙","亥":"乙","子":"巳","丑":"庚",
}

# 月德: 月支 → 天干
YUEDE = {
    "寅":"丙","午":"丙","戌":"丙",
    "亥":"甲","卯":"甲","未":"甲",
    "申":"壬","子":"壬","辰":"壬",
    "巳":"庚","酉":"庚","丑":"庚",
}

# 羊刃: 阳日干 → 地支
YANGREN = {"甲":"卯","丙":"午","戊":"午","庚":"酉","壬":"子"}


def get_shensha(day_gan: str, day_zhi: str, month_zhi: str,
                pillar_gan: str, pillar_zhi: str) -> list:
    """
    Compute 神煞 for a single pillar.
    Returns a list of 神煞 names present in this pillar.
    """
    result = []

    # 1. 天乙贵人 (日干查地支)
    tianyi_zhi = TIANYI.get(day_gan, ())
    if pillar_zhi in tianyi_zhi:
        result.append("天乙贵人")

    # 2. 文昌贵人 (日干查地支)
    if pillar_zhi == WENCHANG.get(day_gan, ""):
        result.append("文昌贵人")

    # 3. 天德 (月支查天干/地支)
    tian_de_val = TIANDE.get(month_zhi, "")
    if pillar_gan == tian_de_val or pillar_zhi == tian_de_val:
        result.append("天德")

    # 4. 月德 (月支查天干)
    if pillar_gan == YUEDE.get(month_zhi, ""):
        result.append("月德")

    # 5. 桃花、驿马、华盖、劫煞、灾煞、岁煞 (日支查)
    he_data = SAN_HE.get(day_zhi)
    if he_data:
        if pillar_zhi == he_data["taohua"]:
            result.append("桃花")
        if pillar_zhi == he_data["yima"]:
            result.append("驿马")
        if pillar_zhi == he_data["huagai"]:
            result.append("华盖")
        if pillar_zhi == he_data["jiesha"]:
            result.append("劫煞")

    # 6. 将星 (只以日支查)
    if he_data and pillar_zhi == he_data["jiangxing"]:
        result.append("将星")

    # 7. 羊刃 (阳日干查地支)
    if pillar_zhi == YANGREN.get(day_gan, ""):
        result.append("羊刃")

    return result

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
    pos_cn = {'year': '年', 'month': '月', 'hour': '时'}
    for gan_char in month_hidden:
        for key in ['year', 'month', 'hour']:
            if pillars[key]['gan_char'] == gan_char:
                month_hidden_indexes.append({
                    'gan_char': gan_char,
                    'position': pos_cn[key],
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
                'nayin': get_nayin(pillars['year']['gan_char'], pillars['year']['zhi_char']),
                'shensha': get_shensha(day_gan_char, pillars['day']['zhi_char'], pillars['month']['zhi_char'],
                                        pillars['year']['gan_char'], pillars['year']['zhi_char']),
            },
            'month': {
                'gan': pillars['month']['gan_char'],
                'zhi': pillars['month']['zhi_char'],
                'shi_shen': shi_shen_result['month']['gan_shi_shen'],
                'yin_yang': ['阳', '阴'][pillars['month']['gan'] % 2],
                'nayin': get_nayin(pillars['month']['gan_char'], pillars['month']['zhi_char']),
                'shensha': get_shensha(day_gan_char, pillars['day']['zhi_char'], pillars['month']['zhi_char'],
                                        pillars['month']['gan_char'], pillars['month']['zhi_char']),
            },
            'day': {
                'gan': pillars['day']['gan_char'],
                'zhi': pillars['day']['zhi_char'],
                'shi_shen': '日主',
                'yin_yang': ['阳', '阴'][pillars['day']['gan'] % 2],
                'nayin': get_nayin(pillars['day']['gan_char'], pillars['day']['zhi_char']),
                'shensha': get_shensha(day_gan_char, pillars['day']['zhi_char'], pillars['month']['zhi_char'],
                                        pillars['day']['gan_char'], pillars['day']['zhi_char']),
            },
            'hour': {
                'gan': pillars['hour']['gan_char'],
                'zhi': pillars['hour']['zhi_char'],
                'shi_shen': shi_shen_result['hour']['gan_shi_shen'],
                'yin_yang': ['阳', '阴'][pillars['hour']['gan'] % 2],
                'nayin': get_nayin(pillars['hour']['gan_char'], pillars['hour']['zhi_char']),
                'shensha': get_shensha(day_gan_char, pillars['day']['zhi_char'], pillars['month']['zhi_char'],
                                        pillars['hour']['gan_char'], pillars['hour']['zhi_char']),
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
        effective_positions = [('year', '年'), ('month', '月'), ('hour', '时')]
        effective_gods = []
        missing_gods = []
        
        # Get hour branch's 本气 (first hidden stem)
        from backend.data.solar_terms import DI_ZHI_ZANG_GAN
        hour_zhi_char = result['bazi']['hour']['zhi']
        hour_zhi_benqi = DI_ZHI_ZANG_GAN.get(hour_zhi_char, [''])[0]
        
        for god in god_names:
            found = False
            # Check heavenly stems
            for pos_key, pos_cn in effective_positions:
                if result['bazi'].get(pos_key, {}).get('gan') == god:
                    effective_gods.append(f'{god}（{pos_cn}柱天干）')
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
    
    # ===== 4. 日主性格分析 =====
    # 十天干本性
    TIAN_GAN_CHARACTER = {
        '甲': '甲木为参天大树，正直仁厚、有担当，性格刚直不阿，有领导气质，但不喜受人压制。',
        '乙': '乙木为藤萝花草，柔韧善变、适应力强，外表温和内心坚韧，善于周旋协调。',
        '丙': '丙火为太阳之火，热情开朗、慷慨大方，感染力强，但容易急躁冲动，缺乏耐性。',
        '丁': '丁火为灯烛之火，细腻温和、心思缜密，有内在的光和热，情感丰富但容易内耗。',
        '戊': '戊土为高岗厚土，稳重诚信、包容大度，行事沉稳可靠，但有时过于固执保守。',
        '己': '己土为田园沃土，谦逊包容、善于滋养，心思细腻、善于规划，但容易犹豫不决。',
        '庚': '庚金为刀剑之金，刚毅果断、义字当头，有魄力和执行力，但有时过于刚硬。',
        '辛': '辛金为珠玉之金，精致优雅、追求完美，思维敏锐、善于细节，但容易敏感挑剔。',
        '壬': '壬水为江河之水，智慧变通、大气磅礴，视野开阔、善于谋略，但不喜受约束。',
        '癸': '癸水为雨露之水，聪慧内敛、以柔克刚，直觉敏锐、富有灵性，但容易情绪化。',
    }
    # 十神性格影响
    SHI_SHEN_CHARACTER = {
        '正官': '正官旺者，原则性强、负责任、守规矩，但容易过于拘谨。',
        '七杀': '七杀旺者，有魄力、敢闯敢拼、不畏挑战，但容易冲动激进。',
        '正印': '正印旺者，仁慈稳重、好学习、有文化修养，但依赖性强。',
        '偏印': '偏印旺者，思维独特、有创意、善于逆向思考，但孤僻不合群。',
        '正财': '正财旺者，务实稳重、理财有道、注重实际，但格局偏小。',
        '偏财': '偏财旺者，慷慨大方、善于交际、有商业头脑，但大手大脚。',
        '伤官': '伤官旺者，聪明才艺出众、口才好、有艺术天赋，但心高气傲、口无遮拦。',
        '食神': '食神旺者，温和善良、有口福、懂生活享受，但容易安于现状。',
        '比肩': '比肩旺者，独立自主、自尊心强、有竞争意识，但固执己见。',
        '劫财': '劫财旺者，讲义气、朋友多、行动力强，但容易因朋友破财。',
    }
    
    xingge_section = {
        'title': '三、日主性格分析',
        'content': [],
    }
    
    # 1. 日干本性
    base_char = TIAN_GAN_CHARACTER.get(day_gan_char, '')
    if base_char:
        xingge_section['content'].append(f'【日干本性】日主为{day_gan_char}。{base_char}')
    
    # 2. 十神组合影响 — 统计各柱天干的十神出现频率
    shi_shen_counts = {}
    for pk in ['year', 'month', 'hour']:
        ss = bazi[pk]['shi_shen']
        shi_shen_counts[ss] = shi_shen_counts.get(ss, 0) + 1
    
    # 藏干也统计
    for pk in ['year', 'month', 'day', 'hour']:
        zg = result['zanggan'].get(pk, {}).get('zanggan', [])
        for item in zg:
            ss = item.get('shi_shen', '')
            if ss:
                shi_shen_counts[ss] = shi_shen_counts.get(ss, 0) + 0.5  # 藏干权重减半
    
    dominant_ss = sorted(shi_shen_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    dominant_ss = [(name, count) for name, count in dominant_ss if count >= 1.0]
    
    if dominant_ss:
        descs = []
        for name, count in dominant_ss:
            char_desc = SHI_SHEN_CHARACTER.get(name, '')
            if char_desc:
                descs.append(f'{name}（{int(count)}处）→ {char_desc}')
        xingge_section['content'].append('【十神特征】' + '；'.join(descs))
    
    # 3. 五行体质影响
    elem_influence = []
    if strongest_elements:
        elem_influence.append(f'八字中【{",".join(strongest_elements)}】当令最旺')
    if second_elements:
        elem_influence.append(f'【{",".join(second_elements)}】次旺')
    
    elem_char = {
        '木': '木主仁，性格正直温和、有上进心',
        '火': '火主礼，性格热情开朗、积极向上',
        '土': '土主信，性格稳重踏实、诚信可靠',
        '金': '金主义，性格果敢决断、讲求原则',
        '水': '水主智，性格聪明变通、善于思考',
    }
    elem_desc_parts = []
    for e in strongest_elements + second_elements:
        d = elem_char.get(e, '')
        if d:
            elem_desc_parts.append(f'{e}{d}')
    
    if elem_influence:
        xingge_section['content'].append('【五行气质】' + '，'.join(elem_influence) + '。')
    if elem_desc_parts:
        xingge_section['content'].append('受旺气影响：' + '；'.join(elem_desc_parts) + '。')
    
    # 调候对性格的影响
    if is_wood_in_summer or is_metal_in_winter:
        if not effective_gods:
            xingge_section['content'].append(
                '命局偏寒/偏热但缺少有效调候，性格上容易走向极端或内在压力较大。'
            )
    
    # 4. 性格总结
    sections.append(xingge_section)
    
    # ===== 5. 婚姻分析 =====
    gender = result.get('gender', '男')
    
    # 地支关系映射
    LIUHE = {'子丑', '寅亥', '卯戌', '辰酉', '巳申', '午未'}
    SANHE_MAP = {
        '申': {'子', '辰'}, '子': {'申', '辰'}, '辰': {'申', '子'},
        '寅': {'午', '戌'}, '午': {'寅', '戌'}, '戌': {'寅', '午'},
        '巳': {'酉', '丑'}, '酉': {'巳', '丑'}, '丑': {'巳', '酉'},
        '亥': {'卯', '未'}, '卯': {'亥', '未'}, '未': {'亥', '卯'},
    }
    CHONG = {'子午', '午子', '卯酉', '酉卯', '寅申', '申寅', '巳亥', '亥巳', '辰戌', '戌辰', '丑未', '未丑'}
    HAI = {'子未', '未子', '丑午', '午丑', '寅巳', '巳寅', '卯辰', '辰卯', '申亥', '亥申', '酉戌', '戌酉'}
    XING = {'丑戌', '戌丑', '丑未', '未丑', '戌未', '未戌', '寅巳', '巳寅', '巳申', '申巳', '寅申', '申寅'}
    BANHE = {
        ('寅', '午'): '寅午半合火局', ('午', '戌'): '午戌半合火局', ('寅', '戌'): '寅戌半合火局',
        ('巳', '酉'): '巳酉半合金局', ('酉', '丑'): '酉丑半合金局', ('巳', '丑'): '巳丑半合金局',
        ('申', '子'): '申子半合水局', ('子', '辰'): '子辰半合水局', ('申', '辰'): '申辰半合水局',
        ('亥', '卯'): '亥卯半合木局', ('卯', '未'): '卯未半合木局', ('亥', '未'): '亥未半合木局',
    }
    
    def get_relation(z1, z2):
        pair = z1 + z2
        pair_rev = z2 + z1
        if pair in LIUHE or pair_rev in LIUHE:
            return f'{z1}{z2}六合'
        if pair in CHONG or pair_rev in CHONG:
            return f'{z1}{z2}相冲'
        if pair in HAI or pair_rev in HAI:
            return f'{z1}{z2}相害'
        if pair in XING or pair_rev in XING:
            return f'{z1}{z2}相刑'
        if (z1, z2) in BANHE:
            return BANHE[(z1, z2)]
        if (z2, z1) in BANHE:
            return BANHE[(z2, z1)]
        return None
    
    hunyin_section = {
        'title': '四、婚姻分析',
        'content': [],
    }
    
    day_zhi_char = bazi['day']['zhi']
    month_zhi_char = bazi['month']['zhi']
    year_zhi_char = bazi['year']['zhi']
    hour_zhi_char = bazi['hour']['zhi']
    
    # 1. 夫妻宫分析（日支与月、时、年的关系）
    rels = []
    for other_name, other_zhi in [('月', month_zhi_char), ('时', hour_zhi_char), ('年', year_zhi_char)]:
        rel = get_relation(day_zhi_char, other_zhi)
        if rel:
            rels.append(f'日支{day_zhi_char}与{other_name}支{other_zhi}：{rel}')
    
    if rels:
        hunyin_section['content'].append(f'【夫妻宫（日支{day_zhi_char}）】' + '；'.join(rels) + '。')
    
    # 日支合多判断
    he_count = 0
    for other_zhi in [month_zhi_char, hour_zhi_char, year_zhi_char]:
        pair1, pair2 = day_zhi_char + other_zhi, other_zhi + day_zhi_char
        if pair1 in LIUHE or pair2 in LIUHE or (day_zhi_char, other_zhi) in BANHE or (other_zhi, day_zhi_char) in BANHE:
            he_count += 1
    if he_count >= 2:
        hunyin_section['content'].append(
            f'日支{day_zhi_char}与多柱相合，心思易被外界事务牵动，感情上容易分心。'
        )
    
    # 2. 夫妻星分析
    # 五行元素: 0=木, 1=火, 2=土, 3=金, 4=水
    # 天干: 甲乙(0),丙丁(1),戊己(2),庚辛(3),壬癸(4)
    # `克我` 关系: 木→金→火→水→土→木 (逆五行)
    # 我克: 木克土, 火克金, 土克水, 金克木, 水克火 (顺五行)
    my_element = day_gan // 2
    # 克我 element = (my_element + 3) % 5
    ke_wo_elem = (my_element + 3) % 5
    yang_ke_wo = ke_wo_elem * 2       # 克我之阳干
    yin_ke_wo = ke_wo_elem * 2 + 1    # 克我之阴干
    # 我克 element = (my_element + 2) % 5
    wo_ke_elem = (my_element + 2) % 5
    yang_wo_ke = wo_ke_elem * 2       # 我克之阳干
    yin_wo_ke = wo_ke_elem * 2 + 1    # 我克之阴干
    gan_yinyang = day_gan % 2  # 0=阳, 1=阴
    
    if gender == '女':
        # 女命：正官=克我异性，七杀=克我同性
        if gan_yinyang == 0:  # 阳干，阳被阴克=正官，阳被阳克=七杀
            zheng_guan = TIAN_GAN[yin_ke_wo]
            qi_sha = TIAN_GAN[yang_ke_wo]
        else:  # 阴干，阴被阳克=正官，阴被阴克=七杀
            zheng_guan = TIAN_GAN[yang_ke_wo]
            qi_sha = TIAN_GAN[yin_ke_wo]
        
        # 查找夫妻星（天干，排除日主自己）
        fu_stars = []
        for pk in ['year', 'month', 'hour']:
            gan_char = bazi[pk]['gan']
            if gan_char == zheng_guan:
                fu_stars.append(f'正官{gan_char}（{pk}柱天干）')
            elif gan_char == qi_sha:
                fu_stars.append(f'七杀{gan_char}（{pk}柱天干）')
        
        # 查找夫妻星（地支藏干）
        fu_stars_cang = []
        for pk in ['year', 'month', 'day', 'hour']:
            zg = result['zanggan'].get(pk, {}).get('zanggan', [])
            zhi_char = result['zanggan'].get(pk, {}).get('zhi_char', '')
            for idx, item in enumerate(zg):
                gan_c = item['gan_char']
                if gan_c == zheng_guan or gan_c == qi_sha:
                    label = '正官' if gan_c == zheng_guan else '七杀'
                    pos_info = f'{pk}支{zhi_char}'
                    if idx == 0:
                        pos_info += '（本气）'
                    fu_stars_cang.append(f'{label}{gan_c}（{pos_info}）')
        
        if fu_stars:
            hunyin_section['content'].append(f'【夫妻星】夫妻星透出天干：{"、".join(fu_stars)}。')
        else:
            hunyin_section['content'].append('【夫妻星】夫妻星（正官/七杀）在天干均未透出。')
        
        if fu_stars_cang:
            hunyin_section['content'].append(f'地支中藏夫妻星：{"、".join(fu_stars_cang)}。')
        else:
            hunyin_section['content'].append('原局地支中也不见夫妻星，异性缘分较浅，需大运流年引动。')
        
        # 是否缺夫妻星综合判断
        has_fu_in_gan = len(fu_stars) > 0
        has_fu_in_benqi = False
        for pk in ['year', 'month', 'day', 'hour']:
            zg = result['zanggan'].get(pk, {}).get('zanggan', [])
            zhi_char = result['zanggan'].get(pk, {}).get('zhi_char', '')
            if zg and zg[0]['gan_char'] in [zheng_guan, qi_sha]:
                has_fu_in_benqi = True
                break
        has_fu_in_cang = len(fu_stars_cang) > 0
        
        if not has_fu_in_gan and not has_fu_in_cang:
            hunyin_section['content'].append('⚠️ 原局天干地支均无夫妻星，属于较难成婚的命局。')
        
        # 好日柱检查（24个女命好日柱）
        good_day_female = {'庚午', '丙子', '辛巳', '丁亥', '戊寅', '己卯', '癸未', '甲申', '乙酉', '壬辰', '癸丑', '壬戌'}
        day_pillar = bazi['day']['gan'] + bazi['day']['zhi']
        if day_pillar in good_day_female:
            # 检查夫妻星是否在夫妻宫本气
            day_zg = result['zanggan'].get('day', {}).get('zanggan', [])
            if day_zg and day_zg[0]['gan_char'] in [zheng_guan, qi_sha]:
                hunyin_section['content'].append(
                    f'✅ {day_pillar}日柱为佳配，夫妻星（{day_zg[0]["gan_char"]}）在夫妻宫本气，配偶自身条件好。'
                )
        
        # 官杀混杂检查
        has_zg_in_gan = zheng_guan in [bazi[pk]['gan'] for pk in ['year', 'month', 'hour']]
        has_qs_in_gan = qi_sha in [bazi[pk]['gan'] for pk in ['year', 'month', 'hour']]
        has_zg_in_zhi = any(zheng_guan in [item['gan_char'] for item in result['zanggan'].get(pk, {}).get('zanggan', [])] for pk in ['year', 'month', 'day', 'hour'])
        has_qs_in_zhi = any(qi_sha in [item['gan_char'] for item in result['zanggan'].get(pk, {}).get('zanggan', [])] for pk in ['year', 'month', 'day', 'hour'])
        
        if has_zg_in_gan and has_qs_in_gan:
            hunyin_section['content'].append('⚠️ 天干官杀混杂（正官七杀同时透出），异性缘分复杂，感情选择需谨慎。')
        elif not has_zg_in_gan and has_zg_in_zhi and has_qs_in_zhi:
            hunyin_section['content'].append('天干无官杀混杂，但地支中正官七杀并存，暗藏偏缘，需注意中年后的感情波动。')
        
        # 女命出轨判断：日干之"禄"在日支或时支，且与任一其他地支合
        # 禄: 甲寅乙卯、丙午丁巳、戊巳己午、庚申辛酉、壬亥癸子
        LU_MAP = {'甲': '寅', '乙': '卯', '丙': '午', '丁': '巳', '戊': '巳', '己': '午', '庚': '申', '辛': '酉', '壬': '亥', '癸': '子'}
        lu_zhi = LU_MAP.get(day_gan_char, '')
        if lu_zhi:
            lu_in_rizhi = (lu_zhi == day_zhi_char)
            lu_in_shizhi = (lu_zhi == hour_zhi_char)
            if lu_in_rizhi or lu_in_shizhi:
                lu_pos = '日支' if lu_in_rizhi else '时支'
                # 检查该禄与任一其他地支有合
                other_zhi_list = []
                for ok, ov in [('年', year_zhi_char), ('月', month_zhi_char), ('时', hour_zhi_char), ('日', day_zhi_char)]:
                    if ov == lu_zhi:
                        continue
                    other_zhi_list.append((ok, ov))
                he_found = []
                for ok, ov in other_zhi_list:
                    pair1 = lu_zhi + ov
                    pair2 = ov + lu_zhi
                    if pair1 in LIUHE or pair2 in LIUHE:
                        he_found.append(f'{ok}支{ov}六合')
                    elif (lu_zhi, ov) in BANHE:
                        he_found.append(f'{ok}支{ov}{BANHE[(lu_zhi, ov)]}')
                    elif (ov, lu_zhi) in BANHE:
                        he_found.append(f'{ok}支{ov}{BANHE[(ov, lu_zhi)]}')
                if he_found:
                    hunyin_section['content'].append(
                        f'⚠️ 女命身体出轨判断：日干{day_gan_char}之禄在{lu_pos}{lu_zhi}，'
                        f'该禄与{"、".join(he_found)}，符合判断条件。'
                    )
    
    else:  # 男命
        # 男命：正财=我克异性，偏财=我克同性
        if gan_yinyang == 0:  # 阳干，阳克阴=正财，阳克阳=偏财
            zheng_cai = TIAN_GAN[yin_wo_ke]
            pian_cai = TIAN_GAN[yang_wo_ke]
        else:  # 阴干，阴克阳=正财，阴克阴=偏财
            zheng_cai = TIAN_GAN[yang_wo_ke]
            pian_cai = TIAN_GAN[yin_wo_ke]
        
        cai_stars = []
        for pk in ['year', 'month', 'day', 'hour']:
            gan_char = bazi[pk]['gan']
            if gan_char == zheng_cai:
                cai_stars.append(f'正财{gan_char}（{pk}柱天干）')
            elif gan_char == pian_cai:
                cai_stars.append(f'偏财{gan_char}（{pk}柱天干）')
        
        if cai_stars:
            hunyin_section['content'].append(f'【夫妻星】夫妻星透出天干：{"、".join(cai_stars)}。')
        else:
            hunyin_section['content'].append('【夫妻星】夫妻星（正财/偏财）在天干均未透出。')
        
        # 好日柱检查（24个男命好日柱）
        good_day_male = {'戊子', '己亥', '壬午', '癸巳', '甲戌', '甲辰', '乙丑', '乙未', '丙申', '丁酉', '庚寅', '辛卯'}
        day_pillar = bazi['day']['gan'] + bazi['day']['zhi']
        if day_pillar in good_day_male:
            day_zg = result['zanggan'].get('day', {}).get('zanggan', [])
            if day_zg and day_zg[0]['gan_char'] in [zheng_cai, pian_cai]:
                hunyin_section['content'].append(
                    f'✅ {day_pillar}日柱为佳配，夫妻星（{day_zg[0]["gan_char"]}）在夫妻宫本气，配偶条件好。'
                )
    
    sections.append(hunyin_section)
    
    # ===== 6. 综合分析 =====
    summary_section = {
        'title': '五、综合分析结论',
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
    
    # ===== 关键用神摘要（用于PDF和前端高亮显示） =====
    key_gods_summary = {}
    
    # --- 调候 ---
    tiaohou_gods = []
    if tiaohou and tiaohou.get('key_gods'):
        god_chars = [g['gan_char'] for g in tiaohou['key_gods'][:3]]
        hour_zhi_char = result['bazi']['hour']['zhi']
        hour_zhi_benqi_hidden = DI_ZHI_ZANG_GAN.get(hour_zhi_char, [''])[0]
        
        found_positions = []
        # Check year/month/hour heavenly stems
        for pos_key, pos_name in [('year','年'), ('month','月'), ('hour','时')]:
            p_gan = result['bazi'].get(pos_key, {}).get('gan', '')
            if p_gan in god_chars:
                found_positions.append(f'{p_gan}（{pos_name}柱天干）')
        # Check hour branch 本气
        if hour_zhi_benqi_hidden in god_chars and not any(hour_zhi_benqi_hidden in fp for fp in found_positions):
            found_positions.append(f'{hour_zhi_benqi_hidden}（时支{hour_zhi_char}本气）')
        
        tiaohou_gods = {
            'needed': god_chars,
            'found': found_positions,
            'missing': [g for g in god_chars if g not in [result['bazi'][pk]['gan'] for pk in ['year','month','hour']] and g != hour_zhi_benqi_hidden],
        }
    
    key_gods_summary['tiaohou'] = tiaohou_gods if tiaohou_gods else {'needed': [], 'found': [], 'missing': []}
    
    # --- 格局喜神 ---
    geju_balance = []
    for se in strongest_elements:
        controller = controlling[se]
        controller_wx = wangshuai.get(controller, '')
        is_effective = controller_wx in ['旺', '相']
        # Find which Gan/Zhi in the 八字 match this element
        element_gan_map = {'木': '甲乙', '火': '丙丁', '土': '戊己', '金': '庚辛', '水': '壬癸'}
        pos_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
        matching_gans = []
        contr_chars = element_gan_map.get(controller, '')
        for pk in ['year', 'month', 'day', 'hour']:
            p = result['bazi'].get(pk, {})
            g = p.get('gan', '')
            if g in contr_chars:
                matching_gans.append(f'{g}（{pos_names[pk]}柱天干）')
        # Also check hidden stems in month branch for the controller
        month_hiddens = DI_ZHI_ZANG_GAN.get(result['bazi']['month']['zhi'], [])
        month_got = any(h in contr_chars for h in month_hiddens)
        
        geju_balance.append({
            'strong_element': se,
            'controller': controller,
            'controller_status': controller_wx,
            'is_effective': is_effective,
            'in_bazi': matching_gans,  # 只在天干中寻找喜神
            'has_month_hidden': month_got,
        })
    
    key_gods_summary['geju'] = geju_balance
    
    return {'sections': sections, 'key_gods_summary': key_gods_summary}
