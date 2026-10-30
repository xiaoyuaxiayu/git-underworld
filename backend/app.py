from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .git_reader import analyze, ScanError

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
app = FastAPI(title='Git 地府 · 本地只读分析', docs_url=None, redoc_url=None)

@app.middleware('http')
async def local_only(request: Request, call_next):
    if request.url.hostname not in ('127.0.0.1', 'localhost', 'testserver'):
        return JSONResponse({'detail':'仅允许本机访问。'}, status_code=403)
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        return JSONResponse({'detail':'不允许跨站请求。'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    return response

class ScanRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    limit: int = Field(default=200, ge=1, le=1000)

@app.post('/api/analyze')
def scan(body: ScanRequest):
    try:
        return analyze(body.path, body.limit)
    except (ScanError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get('/')
def index():
    return FileResponse(FRONTEND / 'index.html')

app.mount('/static', StaticFiles(directory=FRONTEND), name='static')
