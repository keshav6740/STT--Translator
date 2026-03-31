from dataclasses import asdict, dataclass, field
from datetime import datetime

SUPPORTED_LANGUAGES = {
    "english": {"google_stt": "en-US", "translate": "en", "whisper": "en", "name": "English"},
    "hindi": {"google_stt": "hi-IN", "translate": "hi", "whisper": "hi", "name": "Hindi"},
    "bengali": {"google_stt": "bn-IN", "translate": "bn", "whisper": "bn", "name": "Bengali"},
    "gujarati": {"google_stt": "gu-IN", "translate": "gu", "whisper": "gu", "name": "Gujarati"},
    "kannada": {"google_stt": "kn-IN", "translate": "kn", "whisper": "kn", "name": "Kannada"},
    "tamil": {"google_stt": "ta-IN", "translate": "ta", "whisper": "ta", "name": "Tamil"},
    "marathi": {"google_stt": "mr-IN", "translate": "mr", "whisper": "mr", "name": "Marathi"},
    "telugu": {"google_stt": "te-IN", "translate": "te", "whisper": "te", "name": "Telugu"},
    "spanish": {"google_stt": "es-ES", "translate": "es", "whisper": "es", "name": "Spanish"},
    "french": {"google_stt": "fr-FR", "translate": "fr", "whisper": "fr", "name": "French"},
    "german": {"google_stt": "de-DE", "translate": "de", "whisper": "de", "name": "German"},
    "japanese": {"google_stt": "ja-JP", "translate": "ja", "whisper": "ja", "name": "Japanese"},
    "korean": {"google_stt": "ko-KR", "translate": "ko", "whisper": "ko", "name": "Korean"},
    "chinese_simplified": {"google_stt": "cmn-Hans-CN", "translate": "zh-CN", "whisper": "zh", "name": "Chinese Simplified"},
}

DEFAULT_LANGUAGE_KEY = "english"

SIMPLE_STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "please", "kindly",
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "could", "would", "can", "will",
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "assistant", "computer",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but",
    "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "uh", "um", "ah", "er", "ok", "okay", "like",
    "yeah", "yes", "hmm", "huh", "hey", "hi", "hello", "tell", "say", "current", "whats", "what's", "what", "is",
}


@dataclass
class CaptionEntry:
    id: str
    timestamp_str: str
    iso_timestamp: str
    text: str
    keywords: list[str] = field(default_factory=list)
    detected_language: str = "unknown"

    @classmethod
    def create(cls, caption_id: str, text: str, keywords: list[str], detected_language: str = "unknown") -> "CaptionEntry":
        now = datetime.now()
        return cls(
            id=caption_id,
            timestamp_str=now.strftime("%H:%M:%S"),
            iso_timestamp=now.isoformat(),
            text=text,
            keywords=keywords,
            detected_language=detected_language,
        )

    def to_dict(self) -> dict:
        return asdict(self)
