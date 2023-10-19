import datetime

import starlette
from starlette.requests import Request
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from . import error
from fastapi.responses import JSONResponse, Response, HTMLResponse


class ErrorCatchMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/show_314":
            print(
                "receive show req: \n"
                f"\t{request.method}: {request.url.path}\n"
                f"\tQuery: {request.query_params}\n"
                f"\tHeaders: ",
                end=""
            )
            for key, value in request.headers.items():
                print(f"\n\t\t{key}: {value}", end="")

            print(
                f"\n\tBody: {await request.body()}\n\n"
                f"<- {datetime.datetime.now()}\n"
            )
            return JSONResponse({"code": 0, "msg": "ok", "data": None})

        stream_resp_t = starlette.middleware.base._StreamingResponse  # noqa
        try:
            response: Optional[stream_resp_t, Response] = await call_next(request)
            if response.status_code == 404:
                raise error.NotFound
        except error.NotFound:
            return HTMLResponse(content="<center><h1>404 - Not Found</h1></center>", status_code=404)
        except error.Forbidden:
            return HTMLResponse(content="<center><h1>403 - Forbidden</h1></center>", status_code=403)
        except Exception as e:  # noqa
            return HTMLResponse(content=f"internal error: {e}", status_code=500)

        if response.status_code >= 400:
            origin_err = []
            async for content in response.body_iterator:
                origin_err.append(content.decode("utf-8", errors="ignore"))
            return JSONResponse({"code": response.status_code, "msg": "".join(origin_err)})

        response.headers['Server'] = 'madliar'
        return response
