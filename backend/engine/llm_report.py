"""
LLM-based Ba Zi report generation.
Calls DeepSeek API to generate professional-grade analysis.
"""

import json
import urllib.request
from typing import Optional


def _get_deepseek_api_key() -> Optional[str]:
    """Read the DeepSeek API key from env or auth.json."""
    import os
    # Try env first (cloud deployment)
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    # Try from current project
    local_auth = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "auth.json")
    for path in [os.path.expanduser("~/.hermes/auth.json"), local_auth]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                creds = data.get("credential_pool", {}).get("deepseek", [])
                if creds:
                    return creds[0].get("access_token", "")
            except Exception:
                pass
    return None


def generate_llm_report(analysis_data: dict) -> dict:
    """
    Generate a Ba Zi analysis report using the LLM.
    
    Args:
        analysis_data: Raw analysis data from the engine (includes bazi, zanggan,
                      wangshuai, tiaohou, geju, dayun, etc.)
    
    Returns:
        dict with 'sections' list, same format as rule-based report
    """
    api_key = _get_deepseek_api_key()
    if not api_key:
        # Fall back to simple report
        return _fallback_report(analysis_data)
    
    # Build the prompt
    prompt = _build_prompt(analysis_data)
    
    # Call DeepSeek API
    result = _call_deepseek_api(prompt, api_key)
    
    if result:
        return result
    
    return _fallback_report(analysis_data)


def _build_prompt(data: dict) -> str:
    """Build the prompt for LLM Ba Zi analysis."""
    bazi = data.get("bazi", {})
    zanggan = data.get("zanggan", {})
    wangshuai = data.get("wangshuai", {})
    geju = data.get("geju", [])
    dayun = data.get("dayun", {})
    qiongtong_text = data.get("qiongtong_text", "")
    tiyao_entry = data.get("tiyao_entry", "")
    
    # Format birth info
    birth = f"{data.get('birth_date', '')} 性别: {data.get('gender', '')}"
    
    # Format bazi - CHINESE ONLY, NO ENGLISH
    pillar_names = {"year": "年", "month": "月", "day": "日", "hour": "时"}
    bazi_text = ""
    for k in ["year", "month", "day", "hour"]:
        p = bazi.get(k, {})
        bazi_text += f"{pillar_names[k]}柱: {p.get('gan', '')}{p.get('zhi', '')}  ({p.get('yin_yang', '')}) 十神: {p.get('shi_shen', '')}\n"
    
    # Format zanggan - CHINESE ONLY
    zg_text = ""
    for k in ["year", "month", "day", "hour"]:
        z = zanggan.get(k, {})
        items = z.get("zanggan", [])
        item_text = " ".join([f"{g['gan_char']}({g['shi_shen']})" for g in items])
        zg_text += f"{pillar_names[k]}支({z.get('zhi_char', '')}): {item_text}\n"
    
    # Format wangshuai
    ws_text = " ".join([f"{e}={s}" for e, s in wangshuai.items()])
    
    # Format geju
    gj_text = ""
    for g in geju:
        gj_text += f"  - {g.get('geju_name', '')}"
        if g.get("shi_shen"):
            gj_text += f" (透出{g.get('gan_char', '')})"
        gj_text += "\n"
    
    # Format dayun
    dy_text = f"起运: {dayun.get('starting_age', '?')}岁 排法: {'顺排' if dayun.get('forward') else '逆排'}\n"
    for c in dayun.get("luck_cycles", []):
        dy_text += f"  {c.get('age_range', '')}: {c.get('gan_char', '')}{c.get('zhi_char', '')}\n"
    
    prompt = f"""你是一位由资深八字老师亲自教授培养的AI命理专家。你严格遵循老师的教学方法论，绝不能自作主张。

## ⚠️ 你必须严格遵守的核心原则

### 论命总顺序（严格执行，不能打乱）
1. 先看**调候（健康）** — 夏天木（甲/乙生巳午未月）、冬天金（庚/辛生亥子丑月）调候至关紧要，无调候则健康有隐患
2. 再看**格局旺气如何平衡（事业财富）** — 找出八字中最旺的五行，看用什么五行来平衡它
3. **是否需要日主** — 需要日主来平衡→考虑日主扶抑；**不需要日主平衡→不管日主强弱**
4. **无药则命不好** — 原局没有其他办法来平衡格局旺气，命肯定不好

### 绝对不能犯的错误
- ❌ **不要死抓日主强弱！八字平衡看全局五行旺衰。不需要日主时，日主强弱不作为主要判断依据**
- ❌ **不要把四土月（辰未戌丑）当成木/火/金/水旺！四个土月的月令是土旺**
- ❌ **不要把日干/日支/年支当作调候用神的有效位置！有效位置只有：年/月/时天干、月支藏气且透出天干、时支本气**
- ❌ **不要混淆两种阴阳：五行层面的阴阳=温度（冷/热）；天干层面的阴阳=作用强弱（阳干强、阴干弱）**
- ❌ **不要出现任何英文单词，全文必须中文**

### 调候核心知识
- 调候主要和健康有关。**夏天的木**（甲/乙生巳午未月）和**冬天的金**（庚/辛生亥子丑月）调候需求最迫切
- 调候用神**有效位置**（原局一辈子都有）：①年/月/时天干；②月支藏气且**透出天干**；③时支本气
- **日干、日支、年支无效** — 即使这些位置出现了调候用神，也不能算
- 大运天干出现调候用神也有效（**只限该大运期间**）；**流年无效**
- 月支藏气必须**透出天干**才能起调候作用，只藏不透不算
- 务必结合下面给出的《穷通宝鉴》原文来分析

### 格局核心知识
- 月令透干成格：月支藏气透出天干→根据日干定十神→格局名
- 月令多股气同时透出→**同时成格**（如食神+偏财双格）
- 月令没透出→**暂不考虑格局**
- 透出来的气才能发挥作用，只藏不透是"待用"状态
- 天透地藏的气也是重要之气（天干在四柱任一支的藏干里有这个五行）
- 正偏混杂：天干同时出现正偏十神（如正财+偏财），且地支都有藏气的，代表这个五行太强，不是好事

### 旺相休囚死（严格按下面的对应关系）
- **寅月/卯月（春）**：木旺→火相→水休→金囚→土死
- **辰月（春末/土旺）**：**土旺**→金相→火休→木囚→水死
- **巳月/午月（夏）**：火旺→土相→木休→水囚→金死
- **未月（夏末/土旺）**：**土旺**→金相→火休→木囚→水死
- **申月/酉月（秋）**：金旺→水相→土休→火囚→木死
- **戌月（秋末/土旺）**：**土旺**→金相→火休→木囚→水死
- **亥月/子月（冬）**：水旺→木相→金休→土囚→火死
- **丑月（冬末/土旺）**：**土旺**→金相→火休→木囚→水死
- 死的五行需救应才能发挥作用

### 其他重要规则
- 年-月一起看（五运六气）；日-时一起看（日运）
- 月支=四季温度（强）；时支=一天温度（弱）；年/日支无温度
- 地支**不能**克天干（只能生）
- 合绊：相邻的两个天干五合而不能合化时，互相牵制，对其他五行作用力大大减弱
- 戊癸合在冬天（亥子丑月）不能化火，只能合绊
- 天地合组合：丁亥、甲午、戊子、己亥、辛巳、壬午、癸巳——相当于合绊
- 阳干（甲丙戊庚壬）=作用能力强，被克时不易完全被压制
- 阴干（乙丁己辛癸）=作用能力弱，被克时更容易被压制
- 地支阴阳=二气发展趋势：阳支=阳气增长（子丑寅卯辰巳），阴支=阴气增长（午未申酉戌亥）

### 论命实战要点（老师案例教的经验）
- **土多金埋**：土过重的人不是身旺有领导力，而是安于现状缺乏进取心；伤官被埋才华发挥不出来
- **婚姻难成三重障碍**：伤官见官+婚姻宫被冲+日主固执
- **子丑六合**是最牢固的合婚组合之一
- 年柱偏财=父亲有本事家境好；年柱正财=父母务实有积蓄；年柱偏印=亲情疏离/支持不足
- 女命食神旺克杀+无印制食→婚中女方易压制丈夫
- 同一干支在不同十神下含义天差地别——戊辰在正财=有钱家庭，在偏印=冷漠/无力资助

## 输出格式要求

严格按照以下**5个段落**输出，每段至少3-5句话：

### 一、调候分析（健康）
分析内容要点：是否夏令木/冬令金？穷通宝鉴如何说？调候用神是否在有效位置？

### 二、格局分析（事业财富）
分析内容要点：月令透出成格？五行旺气是什么？有有效制衡吗？正偏混杂？

### 三、日主分析
分析内容要点：日主强弱？是否需要扶抑？如果不需日主平衡则说明

### 四、大运提示
分析内容要点：起运几岁？每步大运的干支五行对命主有什么影响？

### 五、综合分析结论
分析内容要点：整体层次、优缺点、关键提示

## 原始数据
**出生**: {birth}

**八字**:
{bazi_text}

**地支藏干**:
{zg_text}

**五行旺衰**: {ws_text}

**格局**: 
{gj_text}

**《穷通宝鉴》原文**:
{qiongtong_text or '（无）'}

**《八字提要》**:
{tiyao_entry or '（无）'}

**大运**: 
{dy_text}
"""
    
    return prompt


def _call_deepseek_api(prompt: str, api_key: str) -> Optional[dict]:
    """Call DeepSeek API for analysis."""
    url = "https://api.deepseek.com/v1/chat/completions"
    
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是八字命理专家，严格按以下顺序分析：①调候（健康）②格局（事业财富）③日主④大运⑤结论。核心原则：调候和格局同时分析不冲突；不要死抓日主强弱，八字平衡看全局五行旺衰；不需日主时不管日主强弱；无平衡之法则命不好。用中文，说人话。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    
    try:
        res = urllib.request.urlopen(req, timeout=30)
        response_data = json.loads(res.read().decode("utf-8"))
        
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return None
        
        # Parse the content into sections
        sections = _parse_sections(content)
        return {"sections": sections}
    except Exception as e:
        print(f"[LLM Report Error] {e}")
        return None


def _parse_sections(content: str) -> list:
    """Parse the LLM response into structured sections."""
    import re
    
    sections = []
    current_title = ""
    current_content = []
    
    # Split by numbered headings
    lines = content.split("\n")
    
    for line in lines:
        stripped = line.strip()
        # Match section headers like "1. **调候分析**" or "一、调候分析" or "### 调候分析"
        if re.match(r'^(\d+[\.\、\)]\s*\*{0,2}|[一二三四五六七八九十][\.\、\)]\s*\*{0,2}|###\s+)', stripped):
            # Save previous section
            if current_title and current_content:
                sections.append({
                    "title": current_title,
                    "content": current_content,
                    "severity": "normal",
                })
            current_title = stripped
            current_content = []
        elif stripped:
            if current_title:
                current_content.append(stripped)
            else:
                current_content.append(stripped)
    
    # Save last section
    if current_title and current_content:
        sections.append({
            "title": current_title,
            "content": current_content,
            "severity": "normal",
        })
    
    # If no sections were parsed (simple text), wrap everything in one section
    if not sections and current_content:
        sections.append({
            "title": "命理分析",
            "content": current_content,
            "severity": "normal",
        })
    
    return sections


def _fallback_report(data: dict) -> dict:
    """Simple fallback if LLM is unavailable or times out."""
    from backend.engine.analysis import generate_report
    # We need pillars data which is already computed
    # Reconstruct minimal pillars from the data
    try:
        # The analysis module's generate_report needs particular params
        # For the fallback, return a simple structured report
        wangshuai = data.get("wangshuai", {})
        geju = data.get("geju", [])
        bazi = data.get("bazi", {})
        
        sections = []
        
        # Build simple text from available data
        bazi_str = " ".join([f"{bazi[k]['gan']}{bazi[k]['zhi']}" 
                           for k in ['year', 'month', 'day', 'hour'] 
                           if bazi.get(k)])
        
        sections.append({
            "title": "命理分析（AI深度解读）",
            "content": [
                f"八字：{bazi_str}",
                f"五行旺衰：{' '.join([f'{k}={v}' for k,v in wangshuai.items()])}",
                f"格局：{' '.join([g.get('geju_name','') for g in geju])}",
                "注：AI深度分析服务暂时繁忙，显示基础排盘数据。",
            ],
            "severity": "normal",
        })
        return {"sections": sections}
    except Exception:
        return {"sections": [{"title": "命理分析", "content": ["分析服务暂时繁忙，请稍后再试。"], "severity": "normal"}]}
