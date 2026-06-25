import argparse

import uvicorn

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the MediaForgeTool web application.")
    parser.add_argument("--host", default=settings.app_host)
    parser.add_argument("--port", default=settings.app_port, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=["app"] if args.reload else None,
    )


if __name__ == "__main__":
    main()
