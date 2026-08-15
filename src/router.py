import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_template(template_name: str, context: dict = None) -> str:
    layouts_dir = os.getcwd()  # 入口文件的路径
    env = Environment(
        loader=FileSystemLoader(layouts_dir),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,      # 移除块后的第一个换行
        lstrip_blocks=True,    # 移除块前的空格
    )
    template = env.get_template(template_name)
    context = context or {}
    return template.render(**context)


router = APIRouter()


@router.get("/")
async def home_page() -> RedirectResponse:
    return RedirectResponse(url="/original-intention")


@router.get("/original-intention")
async def old_blog() -> HTMLResponse:
    html = render_template("src/tpl/original-intention.html")
    return HTMLResponse(html)
