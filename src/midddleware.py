import starlette
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse, Response


class ErrorCatchMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        stream_resp_t = starlette.middleware.base._StreamingResponse  # noqa
        try:
            response: Optional[stream_resp_t, Response] = await call_next(request)
        except Exception as e:  # noqa
            response = stream_resp_t(status_code=500, content=f"internal error: {e}")

        if response.status_code != 200:
            origin_err = []
            async for content in response.body_iterator:
                origin_err.append(content.decode("utf-8", errors="ignore"))
            return JSONResponse({"code": response.status_code, "msg": "".join(origin_err)})

        response.headers['Server'] = 'madliar'
        return response
