from deep_translator import GoogleTranslator


class TranslationService:
    @staticmethod
    def translate(text: str, target_code: str) -> str:
        if not text.strip():
            return ""
        return GoogleTranslator(source="auto", target=target_code).translate(text) or ""
