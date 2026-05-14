"""
十神 (Ten Gods) calculation for Ba Zi.
Ten gods are determined based on the relationship between the Day Stem (日干) and other stems.
"""

# Ten God names
SHI_SHEN_NAMES = {
    '正官': '正官',
    '七杀': '七杀',
    '正印': '正印',
    '偏印': '偏印',
    '正财': '正财',
    '偏财': '偏财',
    '伤官': '伤官',
    '食神': '食神',
    '比肩': '比肩',
    '劫财': '劫财',
}


def _get_shi_shen(day_gan: int, other_gan: int) -> str:
    """
    Determine the ten god relationship between day stem and another stem.
    
    Relations (with 日干 as self):
    生我者印: 正印(异性), 偏印(同性)
    我生者食伤: 伤官(异性), 食神(同性)
    克我者官杀: 正官(异性), 七杀(同性)
    我克者财: 正财(异性), 偏财(同性)
    同我者比劫: 劫财(异性), 比肩(同性)
    """
    # Determine element relationship
    # Heavenly stems elements:
    # 0=甲(木), 1=乙(木), 2=丙(火), 3=丁(火), 4=戊(土), 5=己(土), 6=庚(金), 7=辛(金), 8=壬(水), 9=癸(水)
    
    elements = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]  # element index for each stem (0=木, 1=火, 2=土, 3=金, 4=水)
    day_element = elements[day_gan]
    other_element = elements[other_gan]
    
    day_yang = day_gan % 2 == 0
    other_yang = other_gan % 2 == 0
    
    # Same element → 比劫
    if day_element == other_element:
        return '比肩' if day_yang == other_yang else '劫财'
    
    # 生我 (element that produces my element)
    # Wood(0) produces Fire(1), Fire(1) produces Earth(2), Earth(2) produces Metal(3), Metal(3) produces Water(4), Water(4) produces Wood(0)
    producing = {0: 4, 1: 0, 2: 1, 3: 2, 4: 3}  # who produces me?
    if other_element == producing[day_element]:
        return '偏印' if day_yang == other_yang else '正印'
    
    # 我生 (element I produce)
    produced = {0: 1, 1: 2, 2: 3, 3: 4, 4: 0}  # who do I produce?
    if other_element == produced[day_element]:
        return '食神' if day_yang == other_yang else '伤官'
    
    # 克我 (element that controls me)
    controlling = {0: 3, 1: 4, 2: 0, 3: 1, 4: 2}  # who controls me?
    if other_element == controlling[day_element]:
        return '七杀' if day_yang == other_yang else '正官'
    
    # 我克 (element I control)
    controlled = {0: 2, 1: 3, 2: 4, 3: 0, 4: 1}  # who do I control?
    if other_element == controlled[day_element]:
        return '偏财' if day_yang == other_yang else '正财'
    
    return '未知'


def calculate_all_shi_shen(day_gan: int, pillars: dict) -> dict:
    """
    Calculate ten gods for all four pillars.
    
    Args:
        day_gan: Index of the day heavenly stem (0-9)
        pillars: dict with 'year', 'month', 'day', 'hour' keys, each containing 'gan', 'zhi'
    
    Returns:
        dict with ten god relationships for each pillar stem and the 藏干 of each branch
    """
    result = {}
    
    for pillar_name in ['year', 'month', 'day', 'hour']:
        pillar = pillars[pillar_name]
        gan = pillar['gan']
        # Day stem to itself is 比肩
        if pillar_name == 'day':
            result[pillar_name] = {
                'gan_shi_shen': '比肩',
                'gan_char': pillar.get('gan_char', ''),
                'zanggan': None,
            }
        else:
            result[pillar_name] = {
                'gan_shi_shen': _get_shi_shen(day_gan, gan),
                'gan_char': pillar.get('gan_char', ''),
                'zanggan': None,
            }
    
    return result


def get_shi_shen_for_gan(day_gan: int, target_gan: int) -> str:
    """Get the ten god name for any heavenly stem against the day stem."""
    return _get_shi_shen(day_gan, target_gan)


def get_zanggan_shi_shen(day_gan: int, zhi_index: int) -> list:
    """
    Get the ten gods for each hidden stem (藏干) in a branch.
    
    Args:
        day_gan: Day heavenly stem index
        zhi_index: Earthly branch index (0=子, 1=丑, ..., 11=亥)
    
    Returns:
        List of (gan_char, gan_index, shi_shen_name) for each 藏干
    """
    from backend.data.solar_terms import DI_ZHI, DI_ZHI_ZANG_GAN, TIAN_GAN
    
    zhi_char = DI_ZHI[zhi_index]
    zanggan_list = DI_ZHI_ZANG_GAN[zhi_char]
    
    # Map Chinese stem chars to indices
    gan_map = {char: idx for idx, char in enumerate(TIAN_GAN)}
    
    result = []
    for gan_char in zanggan_list:
        gan_idx = gan_map[gan_char]
        result.append({
            'gan_char': gan_char,
            'gan_index': gan_idx,
            'shi_shen': _get_shi_shen(day_gan, gan_idx),
        })
    
    return result
