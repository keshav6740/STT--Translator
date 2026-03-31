try:
    from app import create_app
    from app.core.config import Settings
except ModuleNotFoundError:
    from backend.app import create_app
    from backend.app.core.config import Settings

app = create_app()


if __name__ == "__main__":
    settings = Settings()
    app.run(host=settings.host, port=settings.port, debug=settings.debug, use_reloader=False)
