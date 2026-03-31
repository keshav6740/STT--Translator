# Voice AI Workbench

Core workflows:

- Voice command execution
- Speech to text
- Translation
- Live captions with real-time streaming

## Structure

- `backend/`
  - `app/__init__.py`: Flask app factory
  - `app/api/routes.py`: HTTP and streaming endpoints
  - `app/core/`: config, models, shared state
  - `app/services/`: speech, translation, automation, intent logic
  - `run.py`: local entrypoint
- `frontend/`
  - `index.html`: single-page shell
  - `assets/css/app.css`: layout and visual system
  - `assets/js/api.js`: API client and caption stream
  - `assets/js/app.js`: UI state and event handling
- `test.py`, `main.html`: legacy prototype files kept for reference

## Run

1. Install the Python dependencies used by the backend:

```bash
pip install -r requirements.txt
```

2. Make sure your local speech stack is available:
   - microphone drivers and input permissions
   - any Whisper runtime dependencies your machine needs
3. Start the backend:

```bash
cd backend
python run.py
```

4. Open `http://127.0.0.1:5001/` in the browser. The Flask app now serves the frontend directly.

## Architecture Direction

- Backend concerns are separated by domain instead of mixed in one file.
- Live captions now support server-sent events instead of constant polling.
- Captioning state is isolated per browser session instead of being global.
- The frontend is split into focused modules instead of a single inline script.
- UI text rendering avoids injecting raw transcript HTML.
- Desktop automation is narrowed to safer approved actions rather than blind typing.

## Recommended Next Upgrades

- Move captions and transcripts into persistent storage.
- Replace rule-based intents with a structured intent classifier.
- Add speaker segmentation and transcript export.
- Add authentication and per-user sessions before public deployment.
- Migrate the frontend to a component framework if the UI grows beyond this scope.
