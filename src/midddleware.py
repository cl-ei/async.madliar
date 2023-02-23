import starlette
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from . import error
from fastapi.responses import JSONResponse, Response, HTMLResponse


class ErrorCatchMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        stream_resp_t = starlette.middleware.base._StreamingResponse  # noqa
        try:
            response: Optional[stream_resp_t, Response] = await call_next(request)
            if response.status_code == 404:
                raise error.NotFound
        except error.NotFound:
            return HTMLResponse(content="<h1>404 - Not Found</h1>", status_code=404)
        except error.Forbidden:
            return HTMLResponse(content="<h1>403 - Forbidden</h1>", status_code=403)
        except Exception as e:  # noqa
            return HTMLResponse(content=f"internal error: {e}", status_code=500)

        if response.status_code >= 400:
            origin_err = []
            async for content in response.body_iterator:
                origin_err.append(content.decode("utf-8", errors="ignore"))
            return JSONResponse({"code": response.status_code, "msg": "".join(origin_err)})

        response.headers['Server'] = 'madliar'
        return response
