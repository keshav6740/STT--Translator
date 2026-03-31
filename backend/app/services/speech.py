import re
from typing import Optional

import speech_recognition as sr

from ..core.models import DEFAULT_LANGUAGE_KEY, SIMPLE_STOPWORDS


def simple_extract_keywords(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r"\b\w+\b", text.lower())
    return sorted({token for token in tokens if token not in SIMPLE_STOPWORDS and len(token) > 2 and token.isalpha()})


class SpeechService:
    def __init__(self, whisper_model: str, ambient_noise_duration: float) -> None:
        self.whisper_model = whisper_model
        self.ambient_noise_duration = ambient_noise_duration

    def get_recognizer_and_mic(self, mic_index: Optional[int] = None):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 3000
        recognizer.dynamic_energy_threshold = True
        mic_list = sr.Microphone.list_microphone_names()
        if not mic_list:
            raise RuntimeError("No microphones found.")
        actual_idx = mic_index if mic_index is not None and 0 <= mic_index < len(mic_list) else 0
        microphone = sr.Microphone(device_index=actual_idx)
        return recognizer, microphone, mic_list

    def adjust_noise(self, recognizer: sr.Recognizer, source) -> None:
        recognizer.adjust_for_ambient_noise(source, duration=self.ambient_noise_duration)

    def listen_once(self, mic_index: Optional[int], language_config: dict, timeout: int, phrase_time_limit: int, prefer_google: bool = False) -> str:
        recognizer, microphone, _ = self.get_recognizer_and_mic(mic_index)
        with microphone as source:
            self.adjust_noise(recognizer, source)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        if prefer_google and language_config.get("google_stt"):
            try:
                return recognizer.recognize_google(audio, language=language_config["google_stt"])
            except sr.RequestError:
                pass
        return recognizer.recognize_whisper(
            audio,
            model=self.whisper_model,
            language=language_config.get("whisper") or DEFAULT_LANGUAGE_KEY,
        )

    def caption_stream(self, state, session_id: str, mic_index: Optional[int], language_config: dict) -> None:
        session = state.get_session(session_id)
        recognizer, microphone, _ = self.get_recognizer_and_mic(mic_index)
        whisper_lang = language_config.get("whisper")
        with microphone as source:
            self.adjust_noise(recognizer, source)
            while session.captioning_active.is_set():
                try:
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    continue
                except Exception:
                    continue
                if not session.captioning_active.is_set():
                    break
                try:
                    text = recognizer.recognize_whisper(audio, model=self.whisper_model, language=whisper_lang).strip()
                except sr.UnknownValueError:
                    continue
                except Exception:
                    continue
                if text:
                    from ..core.models import CaptionEntry

                    caption = CaptionEntry.create(
                        caption_id=state.next_caption_id(session_id),
                        text=text,
                        keywords=simple_extract_keywords(text),
                        detected_language=whisper_lang or "auto",
                    )
                    state.add_caption(session_id, caption.to_dict())
