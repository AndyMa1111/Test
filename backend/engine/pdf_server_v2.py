"""
PDF v2.0 — Mirrors web page content exactly.
Order: 八字 → 大运 → 五行旺衰 → 调候(穷通+提要) → 格局 → AI报告(关键用神+6sections)
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
# 地支五行色
ZHI_ELEM = {
    '寅': (0, 160, 40), '卯': (0, 160, 40),          # 木
    '巳': (200, 20, 20), '午': (200, 20, 20), '未': (139, 109, 3),  # 火, 未=土
    '申': (220, 130, 10), '酉': (220, 130, 10),       # 金
    '亥': (40, 120, 230), '子': (40, 120, 230),       # 水
    '辰': (139, 109, 3), '戌': (139, 109, 3), '丑': (139, 109, 3),  # 土
}
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def _sub_title(pdf, text):
    """Gold sub-title with underline (same as web .card-title)."""
    pdf.set_font("zh", "B", 11)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 7, text, ln=True)
    y = pdf.get_y()
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, y, pdf.l_margin + 70, y)
    pdf.ln(3)


def _gold_bar(pdf, w=2.5, h=7):
    pdf.set_fill_color(*GOLD)
    pdf.rect(pdf.get_x(), pdf.get_y(), w, h, style="F")


def generate_pdf(result: dict) -> str:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.add_font("zh", "", FONT_PATH)
    pdf.add_font("zh", "B", FONT_PATH)

    lm = pdf.l_margin
    uw = pdf.w - lm * 2

    bazi = result.get("bazi", {})
    order = ["year", "month", "day", "hour"]
    name_map = {"year": "年柱", "month": "月柱", "day": "日主", "hour": "时柱"}

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

    # ═══════════ 1. 四柱八字 ═══════════
    _sub_title(pdf, "四柱八字")

    lw = 22
    cw = (uw - lw) / 4

    # Header
    pdf.set_font("zh", "B", 9.5)
    pdf.set_fill_color(*GOLD)
    pdf.set_text_color(*WHITE)
    pdf.cell(lw, 8, "", border=1, fill=True, align="C")
    for k in order:
        nm = "日主" if k == "day" else name_map[k] + "柱"
        pdf.cell(cw, 8, nm, border=1, fill=True, align="C")
    pdf.ln()

    def _row(label, draw_fn):
        pdf.set_font("zh", "", 8.5)
        pdf.set_fill_color(*GRAY_LIGHT)
        pdf.set_text_color(*GRAY)
        pdf.cell(lw, 7, label, border=1, fill=True, align="C")
        for i, k in enumerate(order):
            if i == 2:
                pdf.set_fill_color(*GOLD_LIGHT)
            else:
                pdf.set_fill_color(*WHITE)
            draw_fn(k)
        pdf.ln()

    # 天干
    def _tg(k):
        pdf.set_text_color(*ELEM_COLORS.get(bazi[k]["gan"], DARK))
        pdf.set_font("zh", "B", 14)
        pdf.cell(cw, 7, bazi[k]["gan"], border=1, fill=True, align="C")
    _row("天干", _tg)

    # 地支
    def _dz(k):
        pdf.set_text_color(*ZHI_ELEM.get(bazi[k]["zhi"], DARK))
        pdf.set_font("zh", "B", 14)
        pdf.cell(cw, 7, bazi[k]["zhi"], border=1, fill=True, align="C")
    _row("地支", _dz)

    # 藏干
    zanggan = result.get("zanggan", {})
    def _cg(k):
        zg = zanggan.get(k, {})
        parts = [g["gan_char"] for g in zg.get("zanggan", [])]
        txt = " ".join(parts) if parts else "-"
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        pdf.set_fill_color(*WHITE)
        pdf.rect(x0, y0, cw, 7, style="D")
        if not parts:
            pdf.set_text_color(*GRAY)
            pdf.set_font("zh", "", 10.5)
            pdf.set_xy(x0 + 1, y0 + 0.5)
            pdf.cell(pdf.get_string_width("-"), 7, "-")
        else:
            # Space each character evenly within the cell
            step = cw / (len(parts) + 1)
            for i, ch in enumerate(parts):
                c = ELEM_COLORS.get(ch, DARK)
                pdf.set_text_color(*c)
                pdf.set_font("zh", "", 10.5)
                cx = x0 + step * (i + 1) - pdf.get_string_width(ch) / 2
                pdf.set_xy(cx, y0 + 0.5)
                pdf.cell(pdf.get_string_width(ch) + 1, 7, ch)
        pdf.set_xy(x0 + cw, y0)
    _row("藏干", _cg)

    # 纳音
    def _ny(k):
        ny = bazi[k].get("nayin", "-")
        pdf.set_text_color(*GRAY)
        pdf.set_font("zh", "", 9.5)
        pdf.cell(cw, 7, ny, border=1, fill=True, align="C")
    _row("纳音", _ny)

    # 神煞
    def _ss(k):
        ss_list = bazi[k].get("shensha", [])
        txt = " ".join(ss_list) if ss_list else "-"
        pdf.set_text_color(*GRAY)
        pdf.set_font("zh", "", 8)
        pdf.cell(cw, 7, txt, border=1, fill=True, align="C")
    _row("神煞", _ss)

    pdf.ln(5)

    # ═══════════ 2. 大运 ═══════════
    _sub_title(pdf, "大运")
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
        pdf.set_font("zh", "B", 9.5)
        pdf.set_fill_color(*GOLD)
        pdf.set_text_color(*WHITE)
        pdf.cell(dw, 7, "大运", border=1, fill=True, align="C")
        pdf.cell(dw, 7, "干支", border=1, fill=True, align="C")
        pdf.cell(dw, 7, "年龄", border=1, fill=True, align="C")
        pdf.ln()
        for idx, c in enumerate(cycles):
            num = idx + 1
            pdf.set_font("zh", "", 10.5)
            pdf.set_text_color(*DARK)
            pdf.cell(dw, 7, str(num), border=1, align="C")
            # 干支 cell with separate colors for 天干 and 地支
            x0 = pdf.get_x()
            y0 = pdf.get_y()
            pdf.rect(x0, y0, dw, 7, style="D")
            gc = c["gan_char"]
            zc = c["zhi_char"]
            # 天干 (left half)
            pdf.set_font("zh", "B", 11.5)
            pdf.set_text_color(*ELEM_COLORS.get(gc, DARK))
            cx = x0 + dw * 0.25 - pdf.get_string_width(gc) / 2
            pdf.set_xy(cx, y0 + 0.3)
            pdf.cell(pdf.get_string_width(gc) + 1, 7, gc)
            # 地支 (right half)
            pdf.set_text_color(*ZHI_ELEM.get(zc, DARK))
            cx = x0 + dw * 0.75 - pdf.get_string_width(zc) / 2
            pdf.set_xy(cx, y0 + 0.3)
            pdf.cell(pdf.get_string_width(zc) + 1, 7, zc)
            pdf.set_xy(x0 + dw, y0)
            # 年龄
            pdf.set_font("zh", "", 10.5)
            pdf.set_text_color(*DARK)
            pdf.cell(dw, 7, c["age_range"], border=1, align="C")
            pdf.ln()
    pdf.ln(5)

    wangshuai = result.get("wangshuai", {})
    controlling = {"木": "金", "火": "水", "土": "木", "金": "火", "水": "土"}

    # ═══════════ 3. 五行旺相休囚死 ═══════════
    _sub_title(pdf, "五行旺相休囚死")
    for elem_name, status in wangshuai.items():
        ec = ELEM_COLORS.get({"木": "甲", "火": "丙", "土": "戊", "金": "庚", "水": "壬"}.get(elem_name, ""), DARK)
        sc = {"旺": (0, 130, 0), "相": (60, 140, 60), "休": GRAY, "囚": (160, 100, 80), "死": (180, 80, 70)}.get(status, GRAY)
        pdf.set_font("zh", "B", 10.5)
        pdf.set_text_color(*ec)
        pdf.cell(pdf.get_string_width(elem_name) + 2, 7, elem_name, ln=False)
        pdf.set_font("zh", "", 9.5)
        pdf.set_text_color(*sc)
        pdf.cell(pdf.get_string_width(status) + 4, 7, f"({status})", ln=False)
        pdf.cell(6, 7, "", ln=False)
    pdf.ln(8)
    mz = bazi.get("month", {}).get("zhi", "")
    if mz:
        pdf.set_font("zh", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 6, f"（月令{mz}月，以上为各五行当月的旺相休囚死状态。）", ln=True)
    pdf.ln(3)

    # ═══════════ 4. 调候用神 ═══════════
    _sub_title(pdf, "调候用神")

    # 穷通宝鉴
    qiongtong = result.get("qiongtong_text", "")
    if qiongtong:
        lines = qiongtong.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line:
                pdf.set_font("zh", "", 9)
                pdf.set_text_color(*DARK)
                pdf.set_x(lm + 3)
                pdf.multi_cell(uw - 6, 5.5, line, align="L", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(0.5)
    else:
        pdf.set_font("zh", "", 10.5)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 6, "穷通宝鉴暂无此组合的调候记录。", ln=True)

    # 八字提要
    tiyao = result.get("tiyao_entry", "")
    if tiyao:
        pdf.ln(1)
        pdf.set_font("zh", "", 9)
        pdf.set_text_color(*DARK)
        pdf.set_x(lm + 3)
        pdf.multi_cell(uw - 6, 5.5, tiyao.strip(), align="L", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    # ═══════════ 5. 格局分析 ═══════════
    _sub_title(pdf, "格局分析")
    geju = result.get("geju", [])
    if geju and any(g.get("shi_shen") for g in geju):
        for g in geju:
            if g.get("shi_shen"):
                pdf.set_x(lm + 3)
                pdf.set_font("zh", "B", 10.5)
                pdf.set_text_color(*ELEM_COLORS.get(g["gan_char"], DARK))
                pdf.cell(pdf.get_string_width(g["gan_char"]) + 2, 7, g["gan_char"], ln=False)
                pdf.set_font("zh", "", 10.5)
                pdf.set_text_color(*DARK)
                pdf.cell(0, 7, f"  透出在{g.get('position', '')}柱天干，成{g.get('geju_name', '')}", ln=True)
    else:
        pdf.set_x(lm + 3)
        pdf.set_font("zh", "", 10.5)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 6, "暂无格局分析。", ln=True)

    # 旺气制衡
    strong_elems = [e for e, s in wangshuai.items() if s == "旺"]
    if strong_elems:
        se = strong_elems[0]
        ctrl = controlling.get(se, "")
        cs = wangshuai.get(ctrl, "")
        pdf.ln(2)
        pdf.set_x(lm + 3)
        pdf.set_font("zh", "", 10)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 6, f"八字中【{se}】当令最旺，需【{ctrl}】来制衡。", ln=True)
        pdf.set_x(lm + 3)
        if cs in ["旺", "相"]:
            pdf.set_text_color(0, 119, 0)
            pdf.cell(0, 6, f"[√] {ctrl}处于{cs}地，形成有效平衡。", ln=True)
        elif cs == "休":
            pdf.set_text_color(180, 120, 0)
            pdf.cell(0, 6, f"[~] {ctrl}处于休地，制衡力不足。", ln=True)
        elif cs in ["囚", "死"]:
            pdf.set_text_color(204, 0, 0)
            pdf.cell(0, 6, f"[×] {ctrl}处于{cs}地，难以有效制衡。", ln=True)
    pdf.ln(4)

    # ═══════════ 6. 命理分析报告 ═══════════
    pdf.ln(2)
    pdf.set_fill_color(*GOLD)
    pdf.set_font("zh", "B", 11.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 10, "    命理分析报告", ln=True, fill=True)
    pdf.set_text_color(*DARK)
    pdf.ln(4)

    report_data = result.get("report", {})
    sections = report_data.get("sections", [])
    cn_nums = ["一", "二", "三", "四", "五", "六", "七", "八"]
    pdf.ln(4)

    # ─── AI 6 sections ───
    for idx, sec in enumerate(sections):
        title = sec.get("title", "")
        title_c = re.sub(r'^###\s*', '', title).strip()
        title_c = re.sub(r'^[一二三四五六七八九十][\、\.\)]\s*', '', title_c).strip()
        num_s = cn_nums[idx] if idx < len(cn_nums) else str(idx + 1)
        ft = f"{num_s}、{title_c}"

        _gold_bar(pdf)
        pdf.set_x(pdf.get_x() + 5)
        pdf.set_font("zh", "B", 12)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, ft, ln=True)
        pdf.ln(1.5)

        pdf.set_font("zh", "", 10.5)
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
