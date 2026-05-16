"""
Server-side PDF generation using fpdf2 (pure Python, no Chromium needed).
Works in all environments including WeChat browser.
"""
import os
import subprocess
from fpdf import FPDF


def _space_for(pdf, needed_mm: float, section_title: str = ""):
    """Check if there's enough vertical space left on the page.
    If not, add a page break. If a section title is provided, repeat it after the break."""
    remaining = pdf.h - pdf.b_margin - pdf.get_y()
    if remaining < needed_mm:
        pdf.add_page()
        # If we broke for a section, repeat the section title on the new page
        if section_title:
            pdf.set_font("zh", "B", 13)
            pdf.cell(0, 10, section_title + "（续）", ln=True)
            pdf.set_font("zh", "", 11)


def generate_pdf(result: dict) -> str:
    """
    Generate a PDF from analysis result using fpdf2.
    Returns the PDF file path.
    """
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    
    # Register Chinese font
    pdf.add_font("zh", "", font_path)
    pdf.add_font("zh", "B", font_path)
    pdf.set_font("zh", "", 20)
    
    # Title
    pdf.cell(0, 15, "八字命理分析报告", ln=True, align="C")
    pdf.set_font("zh", "", 10)
    pdf.cell(0, 8, result.get("birth_date", "") + " · " + ("男命" if result.get("gender") == "男" else "女命"), ln=True, align="C")
    pdf.ln(5)
    
    # Bazi (large display)
    bazi = result.get("bazi", {})
    bazi_str = "  ".join([f"{bazi[k]['gan']}{bazi[k]['zhi']}" for k in ["year", "month", "day", "hour"] if bazi.get(k)])
    pdf.set_font("zh", "", 16)
    pdf.cell(0, 12, bazi_str, ln=True, align="C")
    pdf.ln(5)
    
    # Report sections
    report = result.get("report", {})
    sections = report.get("sections", [])
    for idx, s in enumerate(sections):
        title = s.get("title", "").replace("### ", "").strip()
        
        # -- Guard: section title needs at least 25mm (title + 2 lines of content) --
        _space_for(pdf, 25, title if idx > 0 else "")
        
        # Section title
        pdf.set_font("zh", "B", 13)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_font("zh", "", 11)
        
        for line in s.get("content", []):
            clean = line.strip()
            if clean:
                pdf.multi_cell(0, 7, clean, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    
    # Ten gods table
    _space_for(pdf, 35)
    pdf.set_font("zh", "B", 13)
    pdf.cell(0, 10, "十神分布", ln=True)
    _draw_table(pdf, ["柱", "天干", "十神", "地支", "阴阳"],
                [[{"year":"年","month":"月","day":"日","hour":"时"}[k],
                  bazi[k]["gan"], bazi[k]["shi_shen"], bazi[k]["zhi"], bazi[k]["yin_yang"]]
                 for k in ["year","month","day","hour"]], font_path)
    pdf.ln(3)
    
    # Dayun
    dayun = result.get("dayun", {})
    start_text = f"{dayun.get('starting_years', 0)}岁"
    if dayun.get("starting_months", 0) > 0:
        start_text += f"{dayun['starting_months']}个月"
    
    _space_for(pdf, 35)
    pdf.set_font("zh", "B", 13)
    pdf.cell(0, 10, "大运", ln=True)
    pdf.set_font("zh", "", 11)
    pdf.cell(0, 7, f"起运：{start_text} 排法：{'顺排' if dayun.get('forward') else '逆排'}", ln=True)
    
    elem_map = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
    dy_rows = []
    for i, c in enumerate(dayun.get("luck_cycles", [])):
        dy_rows.append([str(i+1), f"{c['gan_char']}{c['zhi_char']}", elem_map.get(c['gan_char'], ''), c['age_range']])
    _space_for(pdf, 35)
    _draw_table(pdf, ["大运", "干支", "五行", "年龄"], dy_rows, font_path)
    
    # Footer
    _space_for(pdf, 20)
    pdf.set_font("zh", "", 8)
    pdf.cell(0, 5, "本报告由八字命理分析系统 AI 深度解读生成", ln=True, align="C")
    
    # Save
    pdf_path = os.path.expanduser("~/bazi_server_report.pdf")
    pdf.output(pdf_path)
    return pdf_path


def _draw_table(pdf, headers, rows, font_path):
    """Draw a simple table in the PDF."""
    col_widths = [190 // len(headers)] * len(headers)
    
    # Header
    pdf.set_font("zh", "B", 9)
    pdf.set_fill_color(192, 57, 43)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()
    
    # Rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("zh", "", 9)
    for row in rows:
        for i, cell in enumerate(row):
            pdf.cell(col_widths[i], 7, str(cell), border=1, align="C")
        pdf.ln()
