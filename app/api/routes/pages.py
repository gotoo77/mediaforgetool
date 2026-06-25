from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    static_dir = Path("app/static")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "css_version": int((static_dir / "app.css").stat().st_mtime),
            "js_version": int((static_dir / "app.js").stat().st_mtime),
        },
    )
