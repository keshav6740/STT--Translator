from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask import send_from_directory

from .api.routes import api
from .core.state import AppState


def create_app() -> Flask:
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path="")
    CORS(app)
    app.extensions["state"] = AppState()
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/<path:path>")
    def static_proxy(path: str):
        return send_from_directory(app.static_folder, path)

    return app
