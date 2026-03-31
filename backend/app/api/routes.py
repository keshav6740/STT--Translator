from queue import Empty, Queue
import json
import threading
import uuid

import speech_recognition as sr
from flask import Blueprint, Response, current_app, jsonify, request

from ..core.config import Settings
from ..core.models import DEFAULT_LANGUAGE_KEY, SUPPORTED_LANGUAGES
from ..services.automation import AutomationService
from ..services.intents import IntentService
from ..services.speech import SpeechService
from ..services.translation import TranslationService

api = Blueprint("api", __name__)


def get_state():
    return current_app.extensions["state"]


def get_services():
    settings = Settings()
    state = get_state()
    return (
        SpeechService(settings.whisper_model, settings.ambient_noise_duration),
        AutomationService(settings.user_folders, settings.default_weather_location),
        settings,
        state,
    )


def parse_mic_index(raw_value):
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def get_session_id() -> str:
    session_id = request.args.get("session_id") or request.headers.get("X-Session-Id")
    if not session_id and request.is_json:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id")
    return (session_id or "default").strip() or "default"


@api.route("/health", methods=["GET"])
def health():
    _, _, settings, state = get_services()
    session = state.get_session(get_session_id())
    return jsonify(
        {
            "status": "success",
            "app": "voice-ai-workbench",
            "captioning_active": session.captioning_active.is_set(),
            "whisper_model": settings.whisper_model,
            "languages": len(SUPPORTED_LANGUAGES),
        }
    )


@api.route("/languages", methods=["GET"])
def languages():
    items = [{"key": "", "name": "Auto-detect where supported"}]
    items.extend({"key": key, "name": value["name"]} for key, value in SUPPORTED_LANGUAGES.items())
    return jsonify({"status": "success", "languages": items})


@api.route("/microphones", methods=["GET"])
def microphones():
    try:
        names = sr.Microphone.list_microphone_names()
        return jsonify({"status": "success", "microphones": [{"index": i, "name": name} for i, name in enumerate(names)]})
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Failed to list microphones: {exc}"}), 500


@api.route("/listen/command", methods=["POST"])
def listen_command():
    speech, automation, _, state = get_services()
    session_id = get_session_id()
    session = state.get_session(session_id)
    if session.captioning_active.is_set():
        return jsonify({"status": "error", "message": "Stop live captioning before using commands."}), 409
    payload = request.get_json(silent=True) or {}
    language_key = (payload.get("language_key") or DEFAULT_LANGUAGE_KEY).lower() or DEFAULT_LANGUAGE_KEY
    if language_key not in SUPPORTED_LANGUAGES:
        return jsonify({"status": "error", "message": f"Unsupported language: {language_key}"}), 400
    intent_service = IntentService(automation, session)
    try:
        recognized_text = speech.listen_once(parse_mic_index(payload.get("mic_index")), SUPPORTED_LANGUAGES[language_key], 15, 15)
        return jsonify({"status": "success", "recognized_text": recognized_text, "action_taken": intent_service.resolve(recognized_text)})
    except sr.WaitTimeoutError:
        return jsonify({"status": "timeout", "message": "No command detected."})
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Command pipeline failed: {exc}"}), 500


@api.route("/listen/stt", methods=["POST"])
def listen_stt():
    speech, _, _, state = get_services()
    session = state.get_session(get_session_id())
    if session.captioning_active.is_set():
        return jsonify({"status": "error", "message": "Stop live captioning before using STT."}), 409
    payload = request.get_json(silent=True) or {}
    language_key = (payload.get("language_key") or "").lower()
    language_config = SUPPORTED_LANGUAGES.get(language_key or DEFAULT_LANGUAGE_KEY)
    if not language_config:
        return jsonify({"status": "error", "message": f"Unsupported language: {language_key}"}), 400
    try:
        text = speech.listen_once(parse_mic_index(payload.get("mic_index")), language_config, 20, 30, prefer_google=True)
        return jsonify({"status": "success", "recognized_text": text})
    except sr.WaitTimeoutError:
        return jsonify({"status": "timeout", "message": "No speech detected."})
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Speech recognition failed: {exc}"}), 500


@api.route("/translate", methods=["POST"])
def translate():
    payload = request.get_json(silent=True) or {}
    target_language_key = (payload.get("target_language_key") or DEFAULT_LANGUAGE_KEY).lower()
    if target_language_key not in SUPPORTED_LANGUAGES:
        return jsonify({"status": "error", "message": f"Unsupported target language: {target_language_key}"}), 400
    try:
        translated = TranslationService.translate(payload.get("text", ""), SUPPORTED_LANGUAGES[target_language_key]["translate"])
        return jsonify({"status": "success", "translated_text": translated})
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Translation failed: {exc}"}), 500


@api.route("/captions/start", methods=["POST"])
def start_captions():
    speech, _, _, state = get_services()
    payload = request.get_json(silent=True) or {}
    session_id = get_session_id()
    language_key = (payload.get("language_key") or DEFAULT_LANGUAGE_KEY).lower() or DEFAULT_LANGUAGE_KEY
    if language_key not in SUPPORTED_LANGUAGES:
        return jsonify({"status": "error", "message": f"Unsupported language: {language_key}"}), 400
    session = state.get_session(session_id)
    if session.captioning_active.is_set():
        return jsonify({"status": "warning", "message": "Captioning already active."})
    session = state.reset_caption_session(session_id, language_key)
    session.captioning_active.set()
    session.captioning_thread = threading.Thread(
        target=speech.caption_stream,
        args=(state, session_id, parse_mic_index(payload.get("mic_index")), SUPPORTED_LANGUAGES[language_key]),
        daemon=True,
    )
    session.captioning_thread.start()
    return jsonify({"status": "success", "message": "Captioning started."})


@api.route("/captions/stop", methods=["POST"])
def stop_captions():
    _, _, _, state = get_services()
    session = state.get_session(get_session_id())
    if not session.captioning_active.is_set():
        return jsonify({"status": "warning", "message": "Captioning not active."})
    session.captioning_active.clear()
    if session.captioning_thread and session.captioning_thread.is_alive():
        session.captioning_thread.join(timeout=5)
    return jsonify({"status": "success", "message": "Captioning stopped."})


@api.route("/captions", methods=["GET"])
def captions():
    _, _, _, state = get_services()
    session_id = get_session_id()
    try:
        last_count = max(int(request.args.get("last_count", "0")), 0)
    except ValueError:
        last_count = 0
    snapshot = state.snapshot(session_id, last_count)
    snapshot["status"] = "success"
    return jsonify(snapshot)


@api.route("/captions/export", methods=["GET"])
def export_captions():
    _, _, _, state = get_services()
    session_id = get_session_id()
    export_format = (request.args.get("format") or "txt").lower()
    snapshot = state.snapshot(session_id, 0)
    captions = snapshot["captions"]
    if export_format == "json":
        return jsonify({"status": "success", "captions": captions, "all_keywords": snapshot["all_keywords"]})

    lines = []
    for caption in captions:
        lines.append(f"[{caption['timestamp_str']}] ({caption.get('detected_language', 'auto')}) {caption['text']}")
    body = "\n".join(lines)
    return Response(
        body,
        mimetype="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{session_id}-captions.txt"'},
    )


@api.route("/captions/stream", methods=["GET"])
def captions_stream():
    _, _, _, state = get_services()
    session_id = get_session_id()
    client_id = str(uuid.uuid4())
    queue = Queue()
    state.register_subscriber(session_id, client_id, queue)

    def generate():
        try:
            snapshot = state.snapshot(session_id, 0)
            yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
            while True:
                try:
                    caption = queue.get(timeout=15)
                    yield f"event: caption\ndata: {json.dumps(caption)}\n\n"
                except Empty:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            state.remove_subscriber(session_id, client_id)

    return Response(generate(), mimetype="text/event-stream")
