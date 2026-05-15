"""WeChat PDF download endpoint (GET)."""
import os, urllib.parse
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from backend.engine.analysis import analyze_full_bazi

router = APIRouter()


@router.get("/api/analyze/pdf/dl")
async def pdf_dl(year: int, month: int, day: int, hour: int, minute: int = 0, gender: str = "男"):
    """微信专用：GET 方式直接下载 PDF（绕过 blob 限制）。"""
    try:
        result = analyze_full_bazi(year=year, month=month, day=day,
                                   hour=hour, minute=minute, gender=gender)
        from backend.engine.llm_report import generate_llm_report
        deep_report = generate_llm_report(result)
        result['report'] = deep_report
        result['is_deep'] = True

        from backend.engine.pdf_server import generate_pdf
        pdf_path = generate_pdf(result)

        if pdf_path and os.path.exists(pdf_path):
            filename = f'bazi_report_{year}{month:02d}{day:02d}.pdf'
            return FileResponse(pdf_path, media_type='application/pdf',
                                filename=filename, headers={
                                    'Content-Disposition': f"attachment; filename=\"{filename}\"; filename*=UTF-8''{urllib.parse.quote(filename)}"
                                })
        return JSONResponse({'error': 'PDF 生成失败'}, status_code=500)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
