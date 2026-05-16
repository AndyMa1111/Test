"""
Server-side PDF generation using fpdf2 (pure Python, no Chromium needed).
Works in all environments including WeChat browser.
Now includes 6-row bazi table, nayin, shensha, and modern formatting.
"""
import os
from fpdf import FPDF

# 五行颜色 (RGB)
ELEM_COLORS = {
    '甲': (0, 180, 50), '乙': (0, 180, 50),   # 木 - 绿
    '丙': (211, 5, 5),  '丁': (211, 5, 5),    # 火 - 红
    '戊': (139, 109, 3), '己': (139, 109, 3),  # 土 - 金棕
    '庚': (239, 145, 4), '辛': (239, 145, 4),  # 金 - 橙
    '壬': (46, 131, 246), '癸': (46, 131, 246), # 水 - 蓝
}
GOLD = (178, 149, 93)
GOLD_LIGHT = (247, 244, 238)
DARK = (16, 16, 16)
GRAY = (136, 136, 136)
GRAY_LIGHT = (250, 250, 250)


def _space_for(pdf, needed_mm: float, section_title: str = ""):
    """Check if there's enough vertical space left on the page.
    If not, add a page break. If a section title is provided, repeat it after the break."""
    remaining = pdf.h - pdf.b_margin - pdf.get_y()
    if remaining < needed_mm:
        pdf.add_page()
        if section_title:
            pdf.set_font("zh", "B", 12)
            pdf.set_text_color(*GOLD)
            pdf.cell(0, 10, section_title + "（续）", ln=True)
            pdf.set_text_color(*DARK)
            pdf.set_font("zh", "", 10)


def generate_pdf(result: dict) -> str:
    """Generate a PDF from analysis result using fpdf2.
    Returns the PDF file path."""
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    pdf.add_font("zh", "", font_path)
    pdf.add_font("zh", "B", font_path)
    pdf.add_font("zh", "I", font_path)

    # Title
    pdf.set_font("zh", "B", 18)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 12, "八字命理分析报告", ln=True, align="C")
    pdf.set_font("zh", "", 9)
    pdf.set_text_color(*GRAY)
    birth = result.get("birth_date", "")
    gender = "男命" if result.get("gender") == "男" else "女命"
    pdf.cell(0, 7, f"{birth} · {gender}", ln=True, align="C")
    pdf.ln(3)

    # ----- 6-row Bazi table -----
    order = ["year", "month", "day", "hour"]
    name_map = {"year": "年柱", "month": "月柱", "day": "日主", "hour": "时柱"}
    bazi = result.get("bazi", {})

    # Header row
    pdf.set_font("zh", "B", 8)
    pdf.set_fill_color(*GOLD)
    pdf.set_text_color(255, 255, 255)
    col_w = [30, (190 - 30) // 4, (190 - 30) // 4, (190 - 30) // 4, (190 - 30) // 4]
    # Adjust: 5 columns: label + 4 pillars
    pdf.cell(30, 8, "", border=1, fill=True, align="C")
    for k in order:
        pdf.cell(col_w[1], 8, name_map[k], border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*DARK)

    def _pillar_cell(label, cells, is_day_index=None):
        """Draw one row of the bazi table."""
        pdf.set_font("zh", "", 7.5)
        pdf.set_fill_color(*GRAY_LIGHT)
        pdf.cell(30, 7, label, border=1, fill=True, align="C")
        for i, (kv, val) in enumerate(zip(order, cells)):
            if i == is_day_index:
                pdf.set_fill_color(*GOLD_LIGHT)
                pdf.set_text_color(*DARK)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_font("zh", "B", 11) if label in ("天干", "地支") else pdf.set_font("zh", "", 8)
            pdf.cell(col_w[1], 7, str(val), border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(*DARK)

    # Row 1: 天干 (with element color)
    pdf.set_font("zh", "B", 7.5)
    pdf.set_fill_color(*GRAY_LIGHT)
    pdf.cell(30, 7, "天干", border=1, fill=True, align="C")
    for i, k in enumerate(order):
        p = bazi.get(k, {})
        g = p.get("gan", "")
        c = ELEM_COLORS.get(g, DARK)
        pdf.set_text_color(*c)
        bg = 1 if k == "day" else 0
        if bg:
            pdf.set_fill_color(*GOLD_LIGHT)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("zh", "B", 13)
        pdf.cell(col_w[1], 8, g, border=1, fill=bg, align="C")
    pdf.ln()
    pdf.set_text_color(*DARK)

    # Row 2: 地支 (with element color)
    pdf.set_font("zh", "B", 7.5)
    pdf.set_fill_color(*GRAY_LIGHT)
    pdf.cell(30, 7, "地支", border=1, fill=True, align="C")
    for i, k in enumerate(order):
        p = bazi.get(k, {})
        z = p.get("zhi", "")
        c = ELEM_COLORS.get(z, DARK)
        pdf.set_text_color(*c)
        bg = 1 if k == "day" else 0
        if bg:
            pdf.set_fill_color(*GOLD_LIGHT)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("zh", "B", 13)
        pdf.cell(col_w[1], 8, z, border=1, fill=bg, align="C")
    pdf.ln()
    pdf.set_text_color(*DARK)

    # Row 3: 藏干
    zanggan = result.get("zanggan", {})
    pdf.set_font("zh", "", 7.5)
    pdf.set_fill_color(*GRAY_LIGHT)
    pdf.cell(30, 7, "藏干", border=1, fill=True, align="C")
    for k in order:
        zg = zanggan.get(k, {})
        parts = []
        if zg.get("zanggan"):
            for g in zg["zanggan"]:
                gc = g.get("gan_char", "")
                parts.append(gc)
        txt = " ".join(parts) if parts else "-"
        pdf.set_text_color(*DARK)
        pdf.set_font("zh", "", 9)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_w[1], 7, txt, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*DARK)

    # Row 4: 纳音
    pdf.set_font("zh", "", 7.5)
    pdf.set_fill_color(*GRAY_LIGHT)
    pdf.cell(30, 7, "纳音", border=1, fill=True, align="C")
    for k in order:
        p = bazi.get(k, {})
        ny = p.get("nayin", "-")
        pdf.set_text_color(*GRAY)
        pdf.set_font("zh", "", 8)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_w[1], 7, ny, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*DARK)

    # Row 5: 神煞
    pdf.set_font("zh", "", 7.5)
    pdf.set_fill_color(*GRAY_LIGHT)
    pdf.cell(30, 7, "神煞", border=1, fill=True, align="C")
    for k in order:
        p = bazi.get(k, {})
        ss = p.get("shensha", [])
        txt = " ".join(ss) if ss else "-"
        pdf.set_text_color(*GRAY)
        pdf.set_font("zh", "", 7)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_w[1], 7, txt, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*DARK)

    pdf.ln(5)

    # ----- 关键用神摘要（高亮框） -----
    report_data = result.get("report", {})
    ks = report_data.get("key_gods_summary", {})

    if ks:
        # Gold border box
        pdf.set_draw_color(*GOLD)
        pdf.set_fill_color(253, 250, 242)  # #fdfaf2
        # We'll draw a box manually
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        # Save the remaining page space check
        _space_for(pdf, 35)
        y0 = pdf.get_y()

        # Draw box border (rect)
        pdf.rect(x0, y0, 190, 0, style="D")  # height will be extended
        pdf.set_xy(x0 + 4, y0 + 3)

        # Title
        pdf.set_font("zh", "B", 11)
        pdf.set_text_color(*GOLD)
        pdf.cell(0, 8, "关键用神", ln=True)
        pdf.set_x(x0 + 4)

        # 调候
        th = ks.get("tiaohou", {})
        if th.get("needed"):
            pdf.set_font("zh", "B", 9)
            pdf.set_text_color(*DARK)
            pdf.cell(pdf.get_string_width("调候用神：") + 2, 6, "调候用神：", ln=False)
            pdf.set_font("zh", "", 9)
            needed_txt = "需要 " + "、".join(th["needed"])
            if th.get("found") and len(th["found"]) > 0:
                pdf.set_text_color(0, 119, 0)
                needed_txt += "  ✓ 命中找到：" + "、".join(th["found"])
            else:
                pdf.set_text_color(204, 0, 0)
                needed_txt += "  ✗ 原局有效位置未出现，需大运引动"
            pdf.multi_cell(182, 6, needed_txt, new_x="LMARGIN", new_y="NEXT")
            _space_for(pdf, 10)

        # 格局喜神
        gj = ks.get("geju", [])
        for g in gj:
            pdf.set_x(x0 + 4)
            pdf.set_font("zh", "B", 9)
            pdf.set_text_color(*DARK)
            pdf.cell(pdf.get_string_width("格局喜神：") + 2, 6, "格局喜神：", ln=False)
            pdf.set_font("zh", "", 9)
            txt = f"旺气【{g['strong_element']}】需【{g['controller']}】来制衡"
            has_bazi = bool(g.get("in_bazi") and len(g["in_bazi"]) > 0)
            if has_bazi:
                pdf.set_text_color(*DARK)
                txt += "  " + "、".join(g["in_bazi"])
            elif not g.get("is_effective"):
                pdf.set_text_color(204, 0, 0)
                txt += f"  ✗ {g['controller']}在{g['controller_status']}地"
            pdf.multi_cell(182, 6, txt, new_x="LMARGIN", new_y="NEXT")
            _space_for(pdf, 10)

        # Close the box
        _space_for(pdf, 8)
        y1 = pdf.get_y()
        pdf.set_draw_color(*GOLD)
        pdf.rect(x0, y0, 190, y1 - y0, style="D")
        pdf.ln(4)

    # ----- 大运 -----
    dayun = result.get("dayun", {})
    start_text = f"{dayun.get('starting_years', 0)}岁"
    if dayun.get("starting_months", 0) > 0:
        start_text += f"{dayun['starting_months']}个月"

    _space_for(pdf, 25)
    pdf.set_font("zh", "B", 12)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 9, "大运走势", ln=True)
    pdf.set_text_color(*DARK)
    pdf.set_font("zh", "", 9)
    pdf.cell(0, 6, f"起运：{start_text} · 排法：{'顺排' if dayun.get('forward') else '逆排'}", ln=True)
    pdf.ln(1)

    dy_rows = []
    for i, c in enumerate(dayun.get("luck_cycles", [])):
        gc = c['gan_char']
        dy_rows.append([str(i + 1), f"{gc}{c['zhi_char']}", c['age_range']])

    if dy_rows:
        pdf.set_font("zh", "B", 8)
        pdf.set_fill_color(*GOLD)
        pdf.set_text_color(255, 255, 255)
        dw = 190 // 3
        pdf.cell(dw, 7, "大运", border=1, fill=True, align="C")
        pdf.cell(dw, 7, "干支", border=1, fill=True, align="C")
        pdf.cell(dw, 7, "年龄", border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(*DARK)
        pdf.set_font("zh", "", 9)
        for row in dy_rows:
            for i, val in enumerate(row):
                if i == 1:
                    gc = val[0] if val else ""
                    c = ELEM_COLORS.get(gc, DARK)
                    pdf.set_text_color(*c)
                    pdf.set_font("zh", "B", 10)
                else:
                    pdf.set_text_color(*DARK)
                    pdf.set_font("zh", "", 9)
                pdf.cell(dw, 7, str(val), border=1, align="C")
            pdf.ln()

    # ----- AI Report Sections -----
    report = result.get("report", {})
    sections = report.get("sections", [])
    for idx, s in enumerate(sections):
        title = s.get("title", "").replace("### ", "").strip()
        _space_for(pdf, 25, title if idx > 0 else "")

        pdf.set_font("zh", "B", 12)
        pdf.set_text_color(*GOLD)
        pdf.cell(0, 9, title, ln=True)
        pdf.set_text_color(*DARK)
        pdf.set_font("zh", "", 10)

        for line in s.get("content", []):
            clean = line.strip()
            if clean:
                _space_for(pdf, 10)
                pdf.multi_cell(0, 6.5, clean, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Footer
    _space_for(pdf, 15)
    pdf.set_font("zh", "", 7)
    pdf.set_text_color(170, 170, 170)
    pdf.cell(0, 5, "本报告由 FateLab 八字命理分析系统 AI 深度解读生成", ln=True, align="C")

    # Save
    pdf_path = os.path.expanduser("~/bazi_server_report.pdf")
    pdf.output(pdf_path)
    return pdf_path
