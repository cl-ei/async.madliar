from app.http import HttpResponse


async def default_middle_ware(app, handler):
    async def wrapper(request):
        try:
            response = await handler(request)
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            reason = getattr(e, "reason", "Internal Server Error")
            content = "<center><h3>%s %s!</h3></center>" % (status_code, reason)
            response = HttpResponse(content, status=status_code, reason=reason)
        response.headers.add("Server", "madliar")
        return response
    return wrapper


installed_middlewares = [
    default_middle_ware,
]
