from dataclasses import dataclass, field
from queue import Queue
import threading


@dataclass
class CaptionSessionState:
    captioning_active: threading.Event = field(default_factory=threading.Event)
    captioning_thread: threading.Thread | None = None
    captioning_language: str = "english"
    caption_counter: int = 0
    live_captions: list[dict] = field(default_factory=list)
    keyword_to_caption_id: dict[str, str] = field(default_factory=dict)
    subscribers: dict[str, Queue] = field(default_factory=dict)

    def reset(self, language_key: str) -> None:
        self.captioning_active = threading.Event()
        self.captioning_language = language_key
        self.captioning_thread = None
        self.caption_counter = 0
        self.live_captions = []
        self.keyword_to_caption_id = {}
        self.subscribers = {}


class AppState:
    def __init__(self) -> None:
        self.sessions: dict[str, CaptionSessionState] = {}
        self.lock = threading.RLock()

    def get_session(self, session_id: str) -> CaptionSessionState:
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = CaptionSessionState()
            return self.sessions[session_id]

    def reset_caption_session(self, session_id: str, language_key: str) -> CaptionSessionState:
        with self.lock:
            self.sessions[session_id] = CaptionSessionState()
            self.sessions[session_id].captioning_language = language_key
            return self.sessions[session_id]

    def next_caption_id(self, session_id: str) -> str:
        with self.lock:
            session = self.get_session(session_id)
            session.caption_counter += 1
            return f"{session_id}-caption-{session.caption_counter}"

    def add_caption(self, session_id: str, caption: dict) -> None:
        with self.lock:
            session = self.get_session(session_id)
            session.live_captions.append(caption)
            for keyword in caption.get("keywords", []):
                session.keyword_to_caption_id.setdefault(keyword, caption["id"])
            subscribers = list(session.subscribers.values())
        for queue in subscribers:
            queue.put(caption)

    def snapshot(self, session_id: str, last_count: int) -> dict:
        with self.lock:
            session = self.get_session(session_id)
            current_len = len(session.live_captions)
            new_captions = session.live_captions[last_count:current_len] if last_count < current_len else []
            all_keywords = sorted(session.keyword_to_caption_id.keys())
            active = session.captioning_active.is_set()
        return {
            "captions": new_captions,
            "all_keywords": all_keywords,
            "current_total_captions": current_len,
            "captioning_active": active,
        }

    def register_subscriber(self, session_id: str, client_id: str, queue: Queue) -> None:
        with self.lock:
            session = self.get_session(session_id)
            session.subscribers[client_id] = queue

    def remove_subscriber(self, session_id: str, client_id: str) -> None:
        with self.lock:
            session = self.get_session(session_id)
            session.subscribers.pop(client_id, None)
