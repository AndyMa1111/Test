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

# Initialize payment order database
from backend.engine.orders import init_db
init_db()

app = FastAPI(
    title="八字命理分析 API",
    description="自动排盘、十神、大运、调候、旺衰综合分析",
    version="1.0.0",
)

# Register WeChat PDF endpoint
from backend.engine.wechat_pdf import router as wechat_router
app.include_router(wechat_router)

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


# ─── PAYMENT ENDPOINTS ────────────────────────────────────────────────


class PayOrderResponse(BaseModel):
    order_id: str
    total_fee: int
    qrcode: str  # base64 data URI of QR code image
    is_reuse: bool = False


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str  # pending | paid | failed | not_found
    total_fee: int
    report: Optional[dict] = None


def _run_deep_analysis(order_id: str, birth_data: dict):
    """Run deep analysis after payment, store result in orders DB."""
    import threading
    from backend.engine.orders import save_report, mark_failed

    def task():
        try:
            result = analyze_full_bazi(
                year=birth_data["year"],
                month=birth_data["month"],
                day=birth_data["day"],
                hour=birth_data["hour"],
                minute=birth_data.get("minute", 0),
                gender=birth_data.get("gender", "男"),
            )
            from backend.engine.llm_report import generate_llm_report
            deep_report = generate_llm_report(result)
            result["report"] = deep_report
            result["is_deep"] = True
            save_report(order_id, result)
        except Exception as e:
            mark_failed(order_id, str(e))

    threading.Thread(target=task, daemon=True).start()


@app.post("/api/orders", response_model=PayOrderResponse)
async def create_pay_order(data: BirthData):
    """
    Create a payment order for AI deep analysis.
    Returns order_id + QR code image (base64).
    If the same birth data already has a paid report, returns it directly (no charge).
    """
    birth_dict = {
        "year": data.year,
        "month": data.month,
        "day": data.day,
        "hour": data.hour,
        "minute": data.minute,
        "gender": data.gender,
    }

    try:
        # Check if already paid for same birth data
        from backend.engine.orders import create_order, get_paid_order_for_birth

        existing = get_paid_order_for_birth(birth_dict)
        if existing and existing.get("report_json"):
            import json
            report = json.loads(existing["report_json"])
            return PayOrderResponse(
                order_id=existing["order_id"],
                total_fee=0,
                qrcode="",
                is_reuse=True,
            )

        # Create order in DB
        order = create_order(birth_dict)
        order_id = order["order_id"]

        # Call PayJS to get QR code
        from backend.engine.payment import create_native_order
        from backend.engine.orders import update_payjs_info

        payjs_resp = create_native_order(
            total_fee=order["total_fee"],
            out_trade_no=order_id,
            body="八字AI深度解读",
        )

        if payjs_resp.get("return_code") != 1:
            from backend.engine.orders import mark_failed
            mark_failed(order_id, payjs_resp.get("return_msg", ""))
            raise HTTPException(
                status_code=502,
                detail=f"支付平台下单失败：{payjs_resp.get('return_msg', '未知错误')}",
            )

        update_payjs_info(order_id, payjs_resp["payjs_order_id"])

        return PayOrderResponse(
            order_id=order_id,
            total_fee=order["total_fee"],
            qrcode=payjs_resp.get("qrcode", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订单失败：{str(e)}")


@app.post("/api/pay_notify")
async def pay_notify(data: dict):
    """
    支付平台异步通知回调。
    兼容 PayJS 和 XorPay 两种格式。
    """
    from backend.engine.payment import _verify_notify
    from backend.engine.orders import get_order, mark_paid

    # Verify signature
    if not _verify_notify(data):
        return {"return_code": 0, "return_msg": "验签失败"}

    # Try both PayJS and XorPay field names
    out_trade_no = data.get("out_trade_no", data.get("order_id", ""))

    # Determine if payment succeeded
    # PayJS: return_code=1, paid=1
    # XorPay: status=0, pay_result=1
    is_paid = (
        (data.get("return_code") == 1 and data.get("paid") == 1)
        or (data.get("status") == 0 and data.get("pay_result") == 1)
    )

    # Find order by our order ID (out_trade_no)
    order = get_order(out_trade_no)
    if not order:
        return {"return_code": 0, "return_msg": "订单不存在"}

    if is_paid:
        import json
        mark_paid(out_trade_no, json.dumps(data, ensure_ascii=False))

        # Trigger deep analysis in background
        import json as _json
        birth_data = _json.loads(order["birth_data"])
        _run_deep_analysis(out_trade_no, birth_data)

        return {"return_code": 1, "return_msg": "OK"}

    return {"return_code": 0, "return_msg": "支付未完成"}


@app.get("/api/orders/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(order_id: str):
    """
    Get order payment status.
    If paid and report is ready, returns the full report.
    """
    from backend.engine.orders import get_order_status as get_status

    status = get_status(order_id)
    fee = status.get("total_fee", 0)

    if status["status"] == "not_found":
        return OrderStatusResponse(order_id=order_id, status="not_found", total_fee=fee)

    return OrderStatusResponse(
        order_id=status["order_id"],
        status=status["status"],
        total_fee=fee,
        report=status.get("report"),
    )


import json, os
_REGIONS = None

def _load_regions():
    global _REGIONS
    if _REGIONS is not None:
        return _REGIONS
    path = os.path.join(os.path.dirname(__file__), "data", "regions.json")
    try:
        with open(path, encoding="utf-8") as f:
            _REGIONS = json.load(f)
    except FileNotFoundError:
        _REGIONS = {}
    return _REGIONS


@app.get("/api/regions")
async def get_regions():
    """Return Chinese administrative divisions (省/市/区)."""
    return _load_regions()


import math
from datetime import datetime as dt_mod, timezone as tz_mod

def _day_of_year(year: int, month: int, day: int) -> int:
    """Calculate day of year (1-366)."""
    return dt_mod(year, month, day).timetuple().tm_yday

def _equation_of_time(doy: int) -> float:
    """
    Calculate equation of time in minutes.
    Uses the Spencer formula.
    """
    b = 2 * math.pi * (doy - 1) / 365
    eqt = (0.000075 + 0.001868 * math.cos(b) - 0.032077 * math.sin(b)
           - 0.014615 * math.cos(2*b) - 0.04089 * math.sin(2*b))
    return 229.2 * eqt  # convert to minutes


@app.get("/api/calc-solar-time")
async def calc_solar_time(
    year: int, month: int, day: int,
    hour: int, minute: int,
    province: str = "", city: str = ""
):
    """Calculate true solar time from Beijing time and location."""
    regions = _load_regions()
    
    # Get city coordinates
    lat = 39.9
    lng = 116.4  # default: Beijing
    city_name = city
    if province and city:
        prov_data = regions.get(province, {})
        city_data = prov_data.get(city, {})
        if isinstance(city_data, dict) and "lng" in city_data:
            lng = city_data["lng"]
            lat = city_data["lat"]
    
    # Beijing time = UTC+8 reference: 120°E
    ref_lng = 120.0
    lng_diff = lng - ref_lng  # negative if west of Beijing
    
    # Longitude correction: 4 minutes per degree
    lng_correction = lng_diff * 4  # in minutes
    
    # Equation of time for the day
    doy = _day_of_year(year, month, day)
    eot = _equation_of_time(doy)
    
    # Total correction
    total_offset = lng_correction + eot  # in minutes
    
    # Calculate true solar time
    total_minutes = hour * 60 + minute + total_offset
    solar_hour = int(total_minutes // 60) % 24
    solar_minute = int(total_minutes % 60)
    
    # Determine 时辰
    SHI_CHEN = [
        (23, "子时"), (1, "丑时"), (3, "寅时"), (5, "卯时"),
        (7, "辰时"), (9, "巳时"), (11, "午时"), (13, "未时"),
        (15, "申时"), (17, "酉时"), (19, "戌时"), (21, "亥时"),
    ]
    solar_shichen = "子时"
    for start_h, name in SHI_CHEN:
        if solar_hour >= start_h:
            solar_shichen = name
    
    return {
        "solar_hour": solar_hour,
        "solar_minute": solar_minute,
        "solar_shichen": solar_shichen,
        "lng": lng,
        "lat": lat,
        "lng_correction_minutes": round(lng_correction, 1),
        "equation_of_time_minutes": round(eot, 1),
        "total_offset_minutes": round(total_offset, 1),
        "city": city_name or "北京",
    }


@app.post("/api/analyze/pdf/server")
async def analyze_bazi_pdf_server(data: BirthData):
    """
    服务端 PDF 生成（fpdf2，不依赖 Chromium）。
    兼容微信浏览器等不支持前端 PDF 生成的场景。
    """
    import os, urllib.parse
    from fastapi.responses import FileResponse, JSONResponse

    try:
        result = analyze_full_bazi(
            year=data.year, month=data.month, day=data.day,
            hour=data.hour, minute=data.minute, gender=data.gender,
        )
        from backend.engine.llm_report import generate_llm_report
        deep_report = generate_llm_report(result)
        result['report'] = deep_report
        result['is_deep'] = True

        from backend.engine.pdf_server import generate_pdf
        pdf_path = generate_pdf(result)

        if pdf_path and os.path.exists(pdf_path):
            filename = f'bazi_report_{data.year}{data.month:02d}{data.day:02d}.pdf'
            return FileResponse(pdf_path, media_type='application/pdf',
                                filename=filename, headers={
                                    'Content-Disposition': f"attachment; filename=\"{filename}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"
                                })

        return JSONResponse({'error': 'PDF 生成失败'}, status_code=500)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
