"""Same-origin Vue assets and bounded, error-aware API/SSE proxy."""
import json
import os
from pathlib import Path
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import uvicorn

BACKEND = os.getenv("AGENT_BACKEND_URL", "http://127.0.0.1:18100")
HERE = Path(__file__).resolve().parent
app = FastAPI()


@app.get("/")
async def index():
    return FileResponse(HERE / "web_chat.html")


@app.get("/assets/{filename}")
async def asset(filename: str):
    if filename not in ("app.js", "style.css", "vue.global.prod.js"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return FileResponse(HERE / "frontend" / filename)


@app.api_route("/chat/stream", methods=["GET", "POST"])
async def stream(req: Request):
    body = await req.body()
    async def relay():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(190, connect=3)) as client:
                async with client.stream(req.method, f"{BACKEND}/chat/stream", params=req.query_params, content=body, headers={"content-type": "application/json"}) as upstream:
                    if upstream.status_code >= 400:
                        yield "data: " + json.dumps({"type": "Error", "message": "입력을 확인해주세요.", "status": upstream.status_code}, ensure_ascii=False) + "\n\n"
                    else:
                        async for chunk in upstream.aiter_bytes():
                            yield chunk
                        return
        except httpx.RequestError:
            yield "data: " + json.dumps({"type": "Error", "message": "백엔드 연결 실패 또는 시간 초과입니다. 서버 연결을 확인한 뒤 재시도하세요."}, ensure_ascii=False) + "\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(relay(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, req: Request):
    if path not in ("health", "systems", "version", "chat", "evaluation", "evaluation/live", "evaluation/investigation") and not path.startswith("sessions/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    try:
        async with httpx.AsyncClient(timeout=190) as client:
            r = await client.request(req.method, f"{BACKEND}/{path}", content=await req.body(), params=req.query_params, headers={"content-type": "application/json"})
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse({"detail": "백엔드 연결에 실패했습니다. 서버 실행을 확인해주세요."}, status_code=503)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("FRONTEND_PORT", "8600")))
