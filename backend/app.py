"""
八字命理分析 - FastAPI Backend
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from backend.engine.analysis import analyze_full_bazi

app = FastAPI(
    title="八字命理分析 API",
    description="自动排盘、十神、大运、调候、旺衰综合分析",
    version="1.0.0",
)

# CORS - allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BirthData(BaseModel):
    year: int = Field(..., ge=1900, le=2100, description="出生年份")
    month: int = Field(..., ge=1, le=12, description="出生月份")
    day: int = Field(..., ge=1, le=31, description="出生日")
    hour: int = Field(..., ge=0, le=23, description="出生小时 (0-23)")
    minute: int = Field(0, ge=0, le=59, description="出生分钟 (0-59)")
    gender: str = Field("男", description="性别: 男/女")


class HealthCheck(BaseModel):
    status: str
    version: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "index.html")
    try:
        with open(frontend_path, "r", encoding="utf-8") as f:
            from fastapi.responses import HTMLResponse as Resp
            content = f.read()
            return Resp(content=content, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    except FileNotFoundError:
        return HTMLResponse(content="<h1>八字命理分析 API</h1><p>前端页面未找到，请访问 /docs 查看 API 文档</p>")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return HealthCheck(status="ok", version="1.0.0")


@app.post("/api/analyze")
async def analyze_bazi(data: BirthData):
    """
    基础八字分析（即时返回）：排盘 + 十神 + 藏干 + 旺衰 + 调候 + 格局 + 大运 + 算法报告
    """
    try:
        result = analyze_full_bazi(
            year=data.year,
            month=data.month,
            day=data.day,
            hour=data.hour,
            minute=data.minute,
            gender=data.gender,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/analyze/deep")
async def analyze_bazi_deep(data: BirthData):
    """
    AI 深度八字分析：先算引擎数据，再调用 LLM 生成深度分析报告
    """
    try:
        # Step 1: compute engine data
        result = analyze_full_bazi(
            year=data.year,
            month=data.month,
            day=data.day,
            hour=data.hour,
            minute=data.minute,
            gender=data.gender,
        )
        
        # Step 2: check cache for same 八字+大运
        from backend.engine.cache import get_cached_result, save_to_cache
        cached = get_cached_result(result['bazi'], result['dayun'], result['gender'])
        if cached:
            cached['_from_cache'] = True
            return cached
        
        # Step 3: call LLM for deep analysis
        from backend.engine.llm_report import generate_llm_report
        deep_report = generate_llm_report(result)
        
        # Replace report with LLM version
        result['report'] = deep_report
        result['is_deep'] = True
        result['_from_cache'] = False
        
        # Save to cache for future lookups
        save_to_cache(result['bazi'], result['dayun'], result['gender'], result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/analyze/pdf")
async def analyze_bazi_pdf(data: BirthData):
    """
    生成八字分析 PDF 报告下载。
    先运行算法分析（含AI深度解读），再生成 PDF 文件返回。
    """
    import os, json, subprocess, tempfile, urllib.parse
    from fastapi.responses import FileResponse
    
    try:
        # Step 1: same analysis as deep endpoint
        result = analyze_full_bazi(
            year=data.year, month=data.month, day=data.day,
            hour=data.hour, minute=data.minute, gender=data.gender,
        )
        from backend.engine.llm_report import generate_llm_report
        deep_report = generate_llm_report(result)
        result['report'] = deep_report
        result['is_deep'] = True
        
        # Generate PDF from result
        pdf_path = _generate_pdf_from_result(result, data)
        if pdf_path:
            filename = f'bazi_report_{data.year}{data.month:02d}{data.day:02d}.pdf'
            return FileResponse(pdf_path, media_type='application/pdf',
                                filename=filename, headers={
                                    'Content-Disposition': f"attachment; filename=\"{filename}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"
                                })
        
        from fastapi.responses import JSONResponse
        return JSONResponse({'error': 'PDF 生成失败，请稍后重试'}, status_code=500)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/analyze/pdf/from-result")
async def pdf_from_result(data: dict):
    """
    从前端已获取的完整分析结果直接生成 PDF（不重新分析）。
    前端 POST 完整的 result JSON 到本端点。
    """
    import os, subprocess, urllib.parse
    from fastapi.responses import FileResponse
    
    try:
        result = data
        pdf_path = _generate_pdf_from_result(result, None)
        if pdf_path:
            filename = 'bazi_report.pdf'
            return FileResponse(pdf_path, media_type='application/pdf',
                                filename=filename, headers={
                                    'Content-Disposition': f"attachment; filename=\"{filename}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"
                                })
        from fastapi.responses import JSONResponse
        return JSONResponse({'error': 'PDF 生成失败'}, status_code=500)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _generate_pdf_from_result(result: dict, data=None) -> str:
    """Generate PDF from a full analysis result dict. Returns PDF path or None."""
    import os, subprocess
    
    bazi = result['bazi']
    report = result['report']
    zanggan = result['zanggan']
    wangshuai = result['wangshuai']
    dayun = result['dayun']
    qiongtong = result.get('qiongtong_text', '') or ''
    tiyao = result.get('tiyao_entry', '') or ''
    geju = result.get('geju', [])
    
    order = ['year', 'month', 'day', 'hour']
    name_map = {'year': '年', 'month': '月', 'day': '日', 'hour': '时'}
    
    gender_char = '男命' if result.get('gender', '男') == '男' else '女命'
    elem_map = {'甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土', '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水'}
    
    start_text = f"{dayun['starting_years']}岁"
    if dayun.get('starting_months', 0) > 0:
        start_text += f"{dayun['starting_months']}个月"
    
    # Build report sections HTML
    sec_html = ''
    for s in report.get('sections', []):
        title = s['title'].replace('### ', '').strip()
        sec_html += f'<h2>{title}</h2>'
        for c in s['content']:
            sec_html += f'<p>{c}</p>'
    
    # Build bazi display
    bazi_spans = ''
    for k in order:
        p = bazi[k]
        cls = ' class="day"' if k == 'day' else ''
        bazi_spans += f'<span{cls}>{p["gan"]}{p["zhi"]}</span>'
    
    # Build tables
    tg_rows = ''
    for k in order:
        p = bazi[k]
        tg_rows += f'<tr><td>{name_map[k]}</td><td>{p["gan"]}</td><td>{p["shi_shen"]}</td><td>{p["zhi"]}</td><td>{p["yin_yang"]}</td></tr>'
    
    zg_rows = ''
    for k in order:
        z = zanggan[k]
        items = '、'.join([f'{g["gan_char"]}({g["shi_shen"]})' for g in z.get('zanggan', [])])
        zg_rows += f'<tr><td>{name_map[k]}</td><td>{z["zhi_char"]}</td><td>{items}</td></tr>'
    
    ws_items = '、'.join([f'{k}（{v}）' for k, v in wangshuai.items()])
    
    dy_rows = ''
    for i, c in enumerate(dayun['luck_cycles']):
        elem = elem_map.get(c['gan_char'], '')
        dy_rows += f'<tr><td>{i+1}</td><td><strong>{c["gan_char"]}{c["zhi_char"]}</strong></td><td>{elem}</td><td>{c["age_range"]}</td></tr>'
    
    gj_items = ''
    for g in geju:
        if g.get('shi_shen'):
            gj_items += f'<p>• {g["geju_name"]}</p>'
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>八字命理分析报告</title>
<style>
@page {{ size: A4; margin: 1.5cm; }}
body {{ font-family: "Noto Sans SC","Microsoft YaHei","SimSun",sans-serif; font-size: 11pt; line-height: 1.8; color: #1a1a2e; padding: 0; margin: 0.5cm; }}
h1 {{ font-size: 20pt; text-align: center; margin-bottom: 2px; }}
.sub {{ text-align: center; font-size: 10pt; color: #888; margin-bottom: 16px; }}
h2 {{ font-size: 14pt; border-bottom: 2px solid #c0392b; padding-bottom: 4px; color: #c0392b; margin-top: 14px; }}
p {{ margin: 5px 0; text-indent: 2em; }}
table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 10pt; }}
th {{ background: #c0392b; color: white; padding: 5px 6px; }}
td {{ border: 1px solid #ccc; padding: 4px 6px; text-align: center; }}
tr:nth-child(even) {{ background: #f8f8f8; }}
.bazi-box {{ text-align: center; margin: 10px 0; }}
.bazi-box span {{ display: inline-block; padding: 8px 14px; border: 1px solid #ddd; margin: 0 3px; border-radius: 4px; font-size: 16pt; }}
.bazi-box .day {{ border-color: #c0392b; background: #fff5f5; }}
.quote {{ background: #fef9ef; border-left: 4px solid #8b6914; padding: 8px 12px; margin: 8px 0; font-size: 10pt; }}
.footer {{ text-align: center; font-size: 8pt; color: #aaa; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 8px; }}
</style></head><body>
<h1>八字命理分析报告</h1>
<p class="sub">{result.get("birth_date", "")} · {gender_char}</p>
<div class="bazi-box">{bazi_spans}</div>
{sec_html}
<h2>十神分布</h2><table><tr><th>柱</th><th>天干</th><th>十神</th><th>地支</th><th>阴阳</th></tr>{tg_rows}</table>
<h2>地支藏干</h2><table><tr><th>柱</th><th>地支</th><th>藏干（十神）</th></tr>{zg_rows}</table>
<h2>五行旺相休囚死</h2><p>{ws_items}</p>
<h2>格局分析</h2>{gj_items}
<h2>调候用神 — 穷通宝鉴</h2><div class="quote">{qiongtong[:300]}……</div>'''
    
    if tiyao:
        html += f'<h2>八字提要</h2><p>{tiyao}</p>'
    
    html += f'''<h2>大运</h2><p>起运：<strong>{start_text}</strong> · 排法：{'顺排' if dayun.get('forward') else '逆排'}</p>
<table><tr><th>大运</th><th>干支</th><th>五行</th><th>年龄</th></tr>{dy_rows}</table>
<div class="footer">本报告由八字命理分析系统 AI 深度解读生成 · 基于穷通宝鉴算法引擎</div>
</body></html>'''
    
    # Write HTML and generate PDF
    pdf_dir = os.path.expanduser('~')
    html_path = os.path.join(pdf_dir, 'bazi_pdf_report.html')
    pdf_path = os.path.join(pdf_dir, 'bazi_pdf_report.pdf')
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Use Chromium
    chromium_cmd = None
    for cmd in ['chromium', 'chromium-browser', 'google-chrome']:
        try:
            subprocess.run([cmd, '--version'], capture_output=True, timeout=5)
            chromium_cmd = cmd
            break
        except Exception:
            continue
    
    if chromium_cmd:
        subprocess.run([
            chromium_cmd, '--headless', '--no-sandbox', '--disable-gpu',
            f'--print-to-pdf={pdf_path}', html_path
        ], capture_output=True, timeout=30)
        
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
            return pdf_path
    
    return None
