from dataclasses import dataclass, field
import os


@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.getenv("STT_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("STT_PORT", "5001")))
    debug: bool = field(default_factory=lambda: os.getenv("STT_DEBUG", "true").lower() == "true")
    whisper_model: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base"))
    ambient_noise_duration: float = field(default_factory=lambda: float(os.getenv("AMBIENT_NOISE_DURATION", "1.0")))
    default_weather_location: str = field(default_factory=lambda: os.getenv("DEFAULT_WEATHER_LOCATION", "India"))
    user_folders: dict = field(
        default_factory=lambda: {
            "downloads": os.path.expanduser(r"~\Downloads"),
            "documents": os.path.expanduser(r"~\Documents"),
            "projects": os.getenv("PROJECTS_FOLDER", os.path.expanduser(r"~\Projects")),
        }
    )
