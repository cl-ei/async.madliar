from aiohttp import web
from jinja2 import Template


class HttpResponse(web.Response):
    def __init__(self, content, *args, **kwargs):
        if "content_type" not in kwargs:
            kwargs["content_type"] = "text/html"
        if "body" not in kwargs:
            kwargs["body"] = content
        super(HttpResponse, self).__init__(*args, **kwargs)


def render_to_response(template, context=None, request=None):
    try:
        with open(template, encoding="utf-8") as f:
            template_context = f.read()
    except IOError:
        template_context = "<center><h3>Template Does Not Existed!</h3></center>"

    template = Template(template_context)
    return HttpResponse(template.render(context or {}), content_type="text/html")
