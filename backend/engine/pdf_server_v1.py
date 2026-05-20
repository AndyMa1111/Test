"""
Server-side PDF generation using fpdf2.
Clean modern layout: sequential sections, no forced page breaks, gold accent.
Structure: 八字 → 大运 → 五行旺衰 → 调候用神 → 格局分析 → AI深度解读(6 sections)
"""
import os, re
from fpdf import FPDF

GOLD = (178, 149, 93)
GOLD_LIGHT = (247, 244, 238)
DARK = (16, 16, 16)
GRAY = (136, 136, 136)
GRAY_LIGHT = (250, 250, 250)
WHITE = (255, 255, 255)

ELEM_COLORS = {
    '甲': (0, 160, 40), '乙': (0, 160, 40),
    '丙': (200, 20, 20), '丁': (200, 20, 20),
    '戊': (139, 109, 3), '己': (139, 109, 3),
    '庚': (220, 130, 10), '辛': (220, 130, 10),
    '壬': (40, 120, 230), '癸': (40, 120, 230),
}
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def _gold_bar(pdf, w=2.5, h=8):
    """Draw a gold accent bar at current position."""
    pdf.set_fill_color(*GOLD)
    pdf.rect(pdf.get_x(), pdf.get_y(), w, h, style="F")


def _section_title(pdf, text):
    """Section sub-title with gold underline."""
    pdf.set_font("zh", "B", 11.5)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 7, text, ln=True)
    # Thin gold underline
    y = pdf.get_y()
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, y, pdf.l_margin + 80, y)
    pdf.ln(3)


def generate_pdf(result: dict) -> str:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.add_font("zh", "", FONT_PATH)
    pdf.add_font("zh", "B", FONT_PATH)

    lm = pdf.l_margin  # ~10
    uw = pdf.w - lm * 2  # ~190

    # ═══════════ HEADER ═══════════
    pdf.set_fill_color(*GOLD)
    pdf.rect(lm, pdf.get_y(), uw, 2.5, style="F")
    pdf.ln(5)
    pdf.set_font("zh", "B", 22)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 12, "八字命理分析报告", ln=True, align="C")
    pdf.set_font("zh", "", 10.5)
    pdf.set_text_color(*GRAY)
    birth = result.get("birth_date", "")
    gender = "男命" if result.get("gender") == "男" else "女命"
    pdf.cell(0, 7, f"{birth}  ·  {gender}", ln=True, align="C")
    pdf.ln(4)

    # ═══════════ PART 1: 基础排盘 ═══════════
    pdf.set_fill_color(*GOLD)
    pdf.set_font("zh", "B", 11.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 10, "    基础排盘", ln=True, fill=True)
    pdf.set_text_color(*DARK)
    pdf.ln(4)

    bazi = result.get("bazi", {})
    order = ["year", "month", "day", "hour"]
    name_map = {"year": "年柱", "month": "月柱", "day": "日主", "hour": "时柱"}

    # ─── 1. 八字排盘表 ───
    _section_title(pdf, "八字排盘")
    lw = 22
    cw = (uw - lw) / 4  # Total width = lw + 4*cw = uw

    def _header_row():
        pdf.set_font("zh", "B", 9.5)
        pdf.set_fill_color(*GOLD)
        pdf.set_text_color(*WHITE)
        pdf.cell(lw, 8, "", border=1, fill=True, align="C")
        for k in order:
            pdf.cell(cw, 8, name_map[k], border=1, fill=True, align="C")
        pdf.ln()

    def _data_row(label, draw_cell):
        pdf.set_font("zh", "", 8.5)
        pdf.set_fill_color(*GRAY_LIGHT)
        pdf.set_text_color(*GRAY)
        pdf.cell(lw, 7, label, border=1, fill=True, align="C")
        for i, k in enumerate(order):
            pdf.set_fill_color(*GOLD_LIGHT) if i == 2 else pdf.set_fill_color(*WHITE)
            draw_cell(k, i)
        pdf.ln()

    _header_row()

    # 天干
    def _tg(k, i):
        g = bazi.get(k, {}).get("gan", "")
        pdf.set_text_color(*ELEM_COLORS.get(g, DARK))
        pdf.set_font("zh", "B", 14)
        pdf.cell(cw, 7, g, border=1, fill=True, align="C")
    _data_row("天干", _tg)

    # 地支
    def _dz(k, i):
        z = bazi.get(k, {}).get("zhi", "")
        pdf.set_text_color(*ELEM_COLORS.get(z, DARK))
        pdf.set_font("zh", "B", 14)
        pdf.cell(cw, 7, z, border=1, fill=True, align="C")
    _data_row("地支", _dz)

    # 藏干
    zanggan = result.get("zanggan", {})
    def _cg(k, i):
        zg = zanggan.get(k, {})
        parts = [g["gan_char"] for g in zg.get("zanggan", [])]
        txt = " ".join(parts) if parts else "-"
        pdf.set_text_color(*DARK)
        pdf.set_font("zh", "", 10.5)
        pdf.cell(cw, 7, txt, border=1, fill=True, align="C")
    _data_row("藏干", _cg)

    # 纳音
    def _ny(k, i):
        ny = bazi.get(k, {}).get("nayin", "-")
        pdf.set_text_color(*GRAY)
        pdf.set_font("zh", "", 9.5)
        pdf.cell(cw, 7, ny, border=1, fill=True, align="C")
    _data_row("纳音", _ny)

    # 神煞
    def _ss(k, i):
        ss = bazi.get(k, {}).get("shensha", [])
        txt = " ".join(ss) if ss else "-"
        pdf.set_text_color(*GRAY)
        pdf.set_font("zh", "", 8)
        pdf.cell(cw, 7, txt, border=1, fill=True, align="C")
    _data_row("神煞", _ss)

    pdf.ln(5)

    # ─── 2. 大运走势 ───
    _section_title(pdf, "大运走势")
    dayun = result.get("dayun", {})
    st = f"{dayun.get('starting_years', 0)}岁"
    if dayun.get("starting_months", 0) > 0:
        st += f"{dayun['starting_months']}个月"
    pdf.set_font("zh", "", 10.5)
    pdf.set_text_color(*GRAY)
    dt = "顺排" if dayun.get("forward") else "逆排"
    pdf.cell(0, 6, f"起运：{st}  ·  排法：{dt}", ln=True)
    pdf.ln(2)

    cycles = dayun.get("luck_cycles", [])
    if cycles:
        dw = uw // 3
        # Header
        pdf.set_font("zh", "B", 9.5)
        pdf.set_fill_color(*GOLD)
        pdf.set_text_color(*WHITE)
        pdf.cell(dw, 7, "大运", border=1, fill=True, align="C")
        pdf.cell(dw, 7, "干支", border=1, fill=True, align="C")
        pdf.cell(dw, 7, "年龄", border=1, fill=True, align="C")
        pdf.ln()
        # Rows
        for idx, c in enumerate(cycles):
            num = idx + 1
            pdf.set_font("zh", "", 10.5)
            pdf.set_text_color(*DARK)
            pdf.cell(dw, 7, str(num), border=1, align="C")
            gc = c["gan_char"]
            pdf.set_font("zh", "B", 11.5)
            pdf.set_text_color(*ELEM_COLORS.get(gc, DARK))
            pdf.cell(dw, 7, f"{gc}{c['zhi_char']}", border=1, align="C")
            pdf.set_text_color(*DARK)
            pdf.set_font("zh", "", 10.5)
            pdf.cell(dw, 7, c["age_range"], border=1, align="C")
            pdf.ln()
    pdf.ln(5)

    wangshuai = result.get("wangshuai", {})
    controlling = {"木": "金", "火": "水", "土": "木", "金": "火", "水": "土"}

    # ─── 3. 五行旺衰 ───
    _section_title(pdf, "五行旺衰")
    wx_cn = {"旺": "旺", "相": "相", "休": "休", "囚": "囚", "死": "死"}
    for elem_name, status in wangshuai.items():
        ec = ELEM_COLORS.get({"木": "甲", "火": "丙", "土": "戊", "金": "庚", "水": "壬"}.get(elem_name, ""), DARK)
        sc = {"旺": (0, 130, 0), "相": (60, 140, 60), "休": GRAY, "囚": (160, 100, 80), "死": (180, 80, 70)}.get(status, GRAY)
        # Draw inline badge
        pdf.set_font("zh", "B", 10.5)
        pdf.set_text_color(*ec)
        pdf.cell(pdf.get_string_width(elem_name) + 2, 7, elem_name, ln=False)
        pdf.set_font("zh", "", 9.5)
        pdf.set_text_color(*sc)
        pdf.cell(pdf.get_string_width(status) + 4, 7, f"({status})", ln=False)
        pdf.cell(6, 7, "", ln=False)  # spacer
    pdf.ln(8)
    mz = bazi.get("month", {}).get("zhi", "")
    if mz:
        pdf.set_font("zh", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 6, f"（月令{mz}月，以上为各五行当月的旺相休囚死状态。）", ln=True)
    pdf.ln(3)

    # ─── 4. 调候用神 ───
    _section_title(pdf, "调候用神")

    # key_gods_summary may be lost if LLM report replaced rule-based report
    # Reconstruct from raw data
    key_gods = result.get("report", {}).get("key_gods_summary", {})
    if not key_gods.get("tiaohou") and not key_gods.get("geju"):
        # Reconstruct from raw result data
        tiaohou_raw = result.get("tiaohou", {})
        tiaohou_needed = []
        tiaohou_found = []
        if tiaohou_raw and tiaohou_raw.get("key_gods"):
            needed_gods = tiaohou_raw["key_gods"]
            if isinstance(needed_gods, list):
                for g in needed_gods:
                    if isinstance(g, dict):
                        tiaohou_needed.append(g.get("gan_char", ""))
                    else:
                        tiaohou_needed.append(str(g))
            # Check found positions
            from backend.data.solar_terms import DI_ZHI_ZANG_GAN
            for pos_key, pos_name in [('year','年'), ('month','月'), ('hour','时')]:
                p_gan = bazi.get(pos_key, {}).get('gan', '')
                if p_gan and p_gan in tiaohou_needed:
                    tiaohou_found.append(f'{p_gan}（{pos_name}柱天干）')
            hour_zhi = bazi.get('hour', {}).get('zhi', '')
            hour_benqi = DI_ZHI_ZANG_GAN.get(hour_zhi, [None])[0]
            if hour_benqi and hour_benqi in tiaohou_needed and not any(hour_benqi in f for f in tiaohou_found):
                tiaohou_found.append(f'{hour_benqi}（时支{hour_zhi}本气）')
        key_gods['tiaohou'] = {'needed': tiaohou_needed, 'found': tiaohou_found}
        # Reconstruct geju balance
        gj_list = []
        strong_elems = [e for e, s in wangshuai.items() if s == "旺"]
        for se in strong_elems:
            ctrl = controlling.get(se, "")
            cs = wangshuai.get(ctrl, "")
            is_eff = cs in ["旺", "相"]
            element_gan_map = {'木': '甲乙', '火': '丙丁', '土': '戊己', '金': '庚辛', '水': '壬癸'}
            matching = []
            contr_chars = element_gan_map.get(ctrl, "")
            for pk in ['year', 'month', 'day', 'hour']:
                g = bazi.get(pk, {}).get('gan', '')
                pos_names = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
                if g in contr_chars:
                    matching.append(f'{g}（{pos_names[pk]}柱天干）')
            gj_list.append({
                'strong_element': se, 'controller': ctrl,
                'controller_status': cs, 'is_effective': is_eff,
                'in_bazi': matching, 'has_month_hidden': False,
            })
        key_gods['geju'] = gj_list

    th = key_gods.get("tiaohou", {})
    if th.get("needed"):
        pdf.set_font("zh", "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(pdf.get_string_width("调候用神：") + 2, 6, "调候用神：", ln=False)
        pdf.set_font("zh", "", 10.5)
        nt = "需要 " + "、".join(th["needed"])
        if th.get("found") and len(th["found"]) > 0:
            pdf.set_text_color(0, 119, 0)
            nt += "  [√] " + "、".join(th["found"])
        else:
            pdf.set_text_color(204, 0, 0)
            nt += "  [×] 原局有效位置未出现，需大运引动"
        pdf.multi_cell(0, 6, nt, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("zh", "", 10.5)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 6, "暂无调候用神数据。", ln=True)
    pdf.ln(1)

    # 格局喜神
    gj = key_gods.get("geju", [])
    for g in gj:
        pdf.set_font("zh", "B", 10.5)
        pdf.set_text_color(*DARK)
        pdf.cell(pdf.get_string_width("格局喜神：") + 2, 6, "格局喜神：", ln=False)
        pdf.set_font("zh", "", 10.5)
        txt = f"旺气【{g['strong_element']}】需【{g['controller']}】来制衡"
        hb = bool(g.get("in_bazi") and len(g["in_bazi"]) > 0)
        if hb:
            pdf.set_text_color(*DARK)
            txt += "  " + "、".join(g["in_bazi"])
        elif not g.get("is_effective"):
            pdf.set_text_color(204, 0, 0)
            txt += f"  [×] {g['controller']}在{g['controller_status']}地"
        pdf.multi_cell(0, 6, txt, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 穷通宝鉴
    qiongtong = result.get("qiongtong_text", "")
    if qiongtong:
        pdf.set_font("zh", "B", 10.5)
        pdf.set_text_color(*GOLD)
        pdf.cell(0, 7, "穷通宝鉴", ln=True)
        pdf.ln(1)
        pdf.set_font("zh", "", 9)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 5.5, qiongtong.strip(), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # 八字提要
    tiyao = result.get("tiyao_entry", "")
    if tiyao:
        pdf.set_font("zh", "B", 10.5)
        pdf.set_text_color(*GOLD)
        pdf.cell(0, 7, "八字提要", ln=True)
        pdf.ln(1)
        pdf.set_font("zh", "", 9)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 5.5, tiyao.strip(), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # ─── 5. 格局分析 ───
    _section_title(pdf, "格局分析")
    geju = result.get("geju", [])
    if geju and any(g.get("shi_shen") for g in geju):
        for g in geju:
            if g.get("shi_shen"):
                pdf.set_font("zh", "B", 10.5)
                gc = g.get("gan_char", "")
                pdf.set_text_color(*ELEM_COLORS.get(gc, DARK))
                pdf.cell(pdf.get_string_width(gc) + 2, 7, gc, ln=False)
                pdf.set_text_color(*DARK)
                pdf.set_font("zh", "", 10.5)
                pdf.cell(0, 7, f"  透出在{g.get('position', '')}柱天干，成{g.get('geju_name', '')}", ln=True)
    else:
        pdf.set_font("zh", "", 10.5)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 6, "月令藏气未透天干，暂无明显格局。", ln=True)
    pdf.ln(2)

    # 旺气制衡
    strong_elems = [e for e, s in wangshuai.items() if s == "旺"]
    if strong_elems:
        se = strong_elems[0]
        ctrl = controlling.get(se, "")
        cs = wangshuai.get(ctrl, "")
        pdf.set_font("zh", "", 10)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 6, f"八字中【{se}】当令最旺，需【{ctrl}】来制衡。", ln=True)
        if cs in ["旺", "相"]:
            pdf.set_text_color(0, 119, 0)
            pdf.cell(0, 6, f"[√] {ctrl}处于{cs}地，形成有效平衡。", ln=True)
        elif cs == "休":
            pdf.set_text_color(180, 120, 0)
            pdf.cell(0, 6, f"[~] {ctrl}处于休地，制衡力不足。", ln=True)
        elif cs in ["囚", "死"]:
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 6, f"[×] {ctrl}处于{cs}地，难以有效制衡。", ln=True)
    pdf.ln(5)

    # ═══════════ PART 2: AI 深度解读 ═══════════
    pdf.ln(2)
    pdf.set_fill_color(*GOLD)
    pdf.set_font("zh", "B", 11.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 10, "    AI 深度解读", ln=True, fill=True)
    pdf.set_text_color(*DARK)
    pdf.ln(4)

    sections = result.get("report", {}).get("sections", [])
    cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八"]

    for idx, sec in enumerate(sections):
        title = sec.get("title", "")
        title_c = re.sub(r'^###\s*', '', title).strip()
        title_c = re.sub(r'^[一二三四五六七八九十][\、\.\)]\s*', '', title_c).strip()
        num_s = cn_nums[idx] if idx < len(cn_nums) else str(idx + 1)
        ft = f"{num_s}、{title_c}"

        # Gold left bar + title
        _gold_bar(pdf)
        pdf.set_x(pdf.get_x() + 5)
        pdf.set_font("zh", "B", 12.5)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, ft, ln=True)
        pdf.ln(1.5)

        pdf.set_font("zh", "", 11)
        for line in sec.get("content", []):
            cl = line.strip()
            if cl:
                pdf.set_x(lm + 3)
                pdf.multi_cell(uw - 6, 6, cl, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
        pdf.ln(3)

    # ═══════════ FOOTER ═══════════
    pdf.ln(4)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.3)
    pdf.line(lm, pdf.get_y(), lm + uw, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("zh", "", 8.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, "本报告由 FateLab 八字命理分析系统 AI 深度解读生成", ln=True, align="C")
    pdf.cell(0, 5, "fatelab.cn", ln=True, align="C")

    pdf_path = os.path.expanduser("~/bazi_server_report.pdf")
    pdf.output(pdf_path)
    return pdf_path
