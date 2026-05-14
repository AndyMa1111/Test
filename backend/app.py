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
        
        # Step 2: call LLM for deep analysis
        from backend.engine.llm_report import generate_llm_report
        deep_report = generate_llm_report(result)
        
        # Replace report with LLM version
        result['report'] = deep_report
        result['is_deep'] = True
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
