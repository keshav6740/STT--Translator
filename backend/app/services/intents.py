import re


class IntentService:
    def __init__(self, automation_service, session_state) -> None:
        self.automation = automation_service
        self.state = session_state

    def resolve(self, text: str) -> str:
        normalized = (text or "").strip().lower()
        if not normalized:
            return "No speech recognized."

        if "time" in normalized:
            return self.automation.get_current_time()
        if "date" in normalized:
            return self.automation.get_current_date()
        if "weather" in normalized:
            location_match = re.search(r"weather(?:\s+in|\s+for)?\s+(.+)", text, re.IGNORECASE)
            location = location_match.group(1).strip() if location_match else None
            return self.automation.get_weather(location)
        if "youtube" in normalized:
            query_match = re.search(r"(?:youtube|play|search)(?:\s+for|\s+on youtube)?\s+(.+)", text, re.IGNORECASE)
            return self.automation.search_youtube(query_match.group(1).strip() if query_match else "")
        if any(token in normalized for token in ["google", "search", "look up", "find"]):
            query_match = re.search(r"(?:google|search|look up|find)(?:\s+for|\s+on google)?\s+(.+)", text, re.IGNORECASE)
            return self.automation.search_google(query_match.group(1).strip() if query_match else "")
        if any(token in normalized for token in ["launch", "open", "start", "run"]):
            folder_match = re.search(r"(?:open|show|access)(?:\s+my|\s+the)?\s+(downloads|documents|projects)", normalized)
            if folder_match:
                return self.automation.open_folder(folder_match.group(1))
            app_match = re.search(r"(?:launch|open|start|run)\s+([\w\-. ]+)", text, re.IGNORECASE)
            if app_match:
                return self.automation.launch_application(app_match.group(1).strip())
        if any(token in normalized for token in ["navigate", "jump", "discussion", "part about", "go to"]):
            topic_match = re.search(r"(?:navigate(?:\s+to)?|jump(?:\s+to)?|go\s+to|discussion(?:\s+about)?|part\s+about)\s+(.+)", text, re.IGNORECASE)
            topic = topic_match.group(1).strip().lower() if topic_match else ""
            if topic in self.state.keyword_to_caption_id:
                caption_id = self.state.keyword_to_caption_id[topic]
                return f"Found discussion about '{topic}'. NavigateToID:{caption_id}"
            return f"Couldn't find discussion about '{topic}'."
        return f"Recognized '{text}', but no modern action flow matched it."
