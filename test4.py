import flask
from flask import Flask, request, jsonify
from flask_cors import CORS
import speech_recognition as sr
from deep_translator import GoogleTranslator
import webbrowser
import pyautogui
import time
import os
import threading
import platform
import subprocess
import datetime
import urllib.parse
import requests
import traceback
import re
import sys

# --- Configuration ---
AMBIENT_NOISE_DURATION = 1.0
WHISPER_MODEL = "base"
DEFAULT_WEATHER_LOCATION = "India"
USER_FOLDERS = {
    "downloads": os.path.expanduser(r"~\Downloads"),
    "documents": os.path.expanduser(r"~\Documents"),
    "projects": r"C:\Users\Admin\Projects", # CHANGE THIS PATH
}

# --- Language Configuration ---
SUPPORTED_LANGUAGES = {
    "english": {"google_stt": "en-US", "translate": "en", "whisper": "en", "name": "English"},
    "hindi": {"google_stt": "hi-IN", "translate": "hi", "whisper": "hi", "name": "हिंदी (Hindi)"},
    "bengali": {"google_stt": "bn-IN", "translate": "bn", "whisper": "bn", "name": "বাংলা (Bengali)"},
    "gujarati": {"google_stt": "gu-IN", "translate": "gu", "whisper": "gu", "name": "ગુજરાતી (Gujarati)"},
    "kannada": {"google_stt": "kn-IN", "translate": "kn", "whisper": "kn", "name": "ಕನ್ನಡ (Kannada)"},
    "tamil": {"google_stt": "ta-IN", "translate": "ta", "whisper": "ta", "name": "தமிழ் (Tamil)"},
    "marathi": {"google_stt": "mr-IN", "translate": "mr", "whisper": "mr", "name": "मराठी (Marathi)"},
    "telugu": {"google_stt": "te-IN", "translate": "te", "whisper": "te", "name": "తెలుగు (Telugu)"},
    "spanish": {"google_stt": "es-ES", "translate": "es", "whisper": "es", "name": "Español (Spanish)"},
    "french": {"google_stt": "fr-FR", "translate": "fr", "whisper": "fr", "name": "Français (French)"},
    "german": {"google_stt": "de-DE", "translate": "de", "whisper": "de", "name": "Deutsch (German)"},
    "japanese": {"google_stt": "ja-JP", "translate": "ja", "whisper": "ja", "name": "日本語 (Japanese)"},
    "korean": {"google_stt": "ko-KR", "translate": "ko", "whisper": "ko", "name": "한국어 (Korean)"},
    "chinese_simplified": {"google_stt": "cmn-Hans-CN", "translate": "zh-CN", "whisper": "zh", "name": "简体中文 (Chinese Simplified)"},
}
DEFAULT_LANGUAGE_KEY = "english"

# --- Keyword Extraction (Simple) ---
SIMPLE_STOPWORDS = set([
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "please", "kindly",
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "could", "would", "can", "will",
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "assistant", "computer",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as",
    "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "just",
    "don", "should", "now", "ll", "m", "o", "re", "ve", "y", "uh", "um", "ah", "er", "ok", "okay", "like", "yeah", "yes",
    "hmm", "huh", "hey", "hi", "hello", "tell me", "say", "current", "the", "whats", "what's", "what is"
])

def simple_extract_keywords(text: str, language_key: str = DEFAULT_LANGUAGE_KEY):
    if not text: return []
    words_original_case = re.findall(r'\b\w+\b', text)
    text_lower = text.lower()
    tokens = re.findall(r'\b\w+\b', text_lower)
    current_stopwords = SIMPLE_STOPWORDS # Add language-specific stopwords later if needed
    keywords = set()
    for token in tokens:
        if token not in current_stopwords and len(token) > 2 and token.isalpha():
            keywords.add(token)
    for original_word_token in words_original_case:
        if original_word_token.istitle() and original_word_token.lower() not in current_stopwords and \
           len(original_word_token) > 2 and original_word_token.isalpha():
            keywords.add(original_word_token.lower())
    return sorted(list(keywords))

# --- Global state for Live Captioning (same as before) ---
live_captions_data = []
keyword_to_caption_id = {}
captioning_active = threading.Event()
captioning_thread = None
recognizer_caption = None
microphone_caption = None
caption_language_key_global = DEFAULT_LANGUAGE_KEY
caption_id_counter = 0

# --- Backend Action Functions (COMMANDS) - (largely same as before) ---
def open_website(url="https://www.google.com"):
    print(f"Action: Opening website {url}")
    try: webbrowser.open(url); return f"Website opened: {url}"
    except Exception as e: return f"Error opening website: {e}"

def search_youtube(query: str):
    if not query: return "No search query provided for YouTube."
    search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
    print(f"Action: Searching YouTube for '{query}'")
    return open_website(search_url)

def search_google(query: str):
    if not query: return "No search query provided for Google."
    print(f"Action: Searching Google for '{query}' (using PyAutoGUI)")
    open_website("https://www.google.com")
    time.sleep(1.5); result_type = type_text(query)
    if "error" in result_type.lower(): return f"Opened Google, but failed to type: {result_type}"
    time.sleep(0.5); result_enter = press_enter()
    if "error" in result_enter.lower(): return f"Typed search query, but failed to press Enter: {result_enter}"
    return f"Searched Google for '{query}' (check browser focus)."

def type_text(text_to_type="hello world"):
    print(f"Action: Typing text '{text_to_type}'")
    try: time.sleep(1.0); pyautogui.write(text_to_type, interval=0.05); return f"Text typed: '{text_to_type}'"
    except Exception as e: return f"PyAutoGUI error: {e}."

def press_enter():
    print("Action: Pressing Enter")
    try: time.sleep(0.5); pyautogui.press('enter'); return "Enter key pressed."
    except Exception as e: return f"PyAutoGUI error: {e}"

def launch_application(app_name: str):
    if not app_name: return "No application name provided to launch."
    print(f"Action: Attempting to launch '{app_name}'")
    system = platform.system().lower(); command = None
    try:
        app_map = {
            "windows": {"notepad": ["notepad.exe"], "calculator": ["calc.exe"], "explorer": ["explorer.exe"], "cmd": ["cmd.exe"], "powershell": ["powershell.exe"]},
            "darwin": {"terminal": ["open", "-a", "Terminal"], "calculator": ["open", "-a", "Calculator"], "textedit": ["open", "-a", "TextEdit"], "finder": ["open", "."]},
            "linux": {"terminal": ["gnome-terminal"], "calculator": ["gnome-calculator"], "gedit": ["gedit"], "files": ["nautilus"]}
        }
        app_name_lower = app_name.lower()
        if system in app_map and app_name_lower in app_map[system]: command = app_map[system][app_name_lower]
        elif system == "darwin": command = ["open", "-a", app_name]
        elif system == "linux": command = [app_name_lower]
        elif system == "windows": command = ["start", "", app_name_lower]
        else: return f"App '{app_name}' launch not configured for {system} or app unknown."
        if command:
            if system == "windows" and command[0] == "start": subprocess.Popen(command, shell=True)
            else: subprocess.Popen(command)
            return f"Launched '{app_name}'."
        return f"Could not determine launch command for '{app_name}' on {system}."
    except FileNotFoundError: return f"Error: App '{command[0] if command else app_name}' not found."
    except Exception as e: return f"Error launching app '{app_name}': {e}"

def open_folder(folder_key: str):
    if not folder_key: return "No folder key provided."
    print(f"Action: Attempting to open folder '{folder_key}'")
    path = USER_FOLDERS.get(folder_key.lower())
    if not path: return f"Folder key '{folder_key}' not defined in USER_FOLDERS."
    if not os.path.isdir(path): return f"Error: Path for '{folder_key}' ('{path}') not a directory."
    system = platform.system().lower()
    try:
        if system == "windows": os.startfile(path)
        elif system == "darwin": subprocess.Popen(["open", path])
        elif system == "linux": subprocess.Popen(["xdg-open", path])
        else: return f"Unsupported OS for opening folders: {system}"
        return f"Opened folder: {folder_key} ({path})"
    except Exception as e: return f"Error opening folder '{folder_key}': {e}"

def get_current_time():
    now = datetime.datetime.now(); time_str = now.strftime("%I:%M %p")
    print(f"Action: Getting current time: {time_str}")
    return f"The current time is {time_str}."

def get_current_date():
    now = datetime.datetime.now(); date_str = now.strftime("%A, %B %d, %Y")
    print(f"Action: Getting current date: {date_str}")
    return f"Today's date is {date_str}."

def get_weather(location=DEFAULT_WEATHER_LOCATION):
    if not location: location = DEFAULT_WEATHER_LOCATION # Ensure location is not empty
    print(f"Action: Checking weather for '{location}'")
    url = f"https://wttr.in/{urllib.parse.quote_plus(location)}?format=Location: %l%nCondition: %C (%c)%nTemp: %t (%f)%nWind: %w%nHumidity: %h%nPrecip: %p"
    try:
        response = requests.get(url, timeout=10); response.raise_for_status()
        weather_info = response.text.strip()
        if not weather_info: return f"Could not retrieve weather data for '{location}'."
        return f"Weather for {location}:\n{weather_info}"
    except requests.exceptions.RequestException as e: return f"Network error fetching weather: {e}"
    except Exception as e: return f"Unexpected error fetching weather: {e}"

def navigate_to_keyword_time(topic: str):
    global keyword_to_caption_id, live_captions_data
    if not topic: return "Please specify what topic to navigate to."
    search_term = topic.strip().lower()
    found_caption_id = None
    if search_term in keyword_to_caption_id: found_caption_id = keyword_to_caption_id[search_term]
    else:
        best_match_len = 0
        for kw, cap_id in keyword_to_caption_id.items():
            if search_term in kw or kw in search_term:
                if len(kw) > best_match_len: found_caption_id = cap_id; best_match_len = len(kw)
    if found_caption_id:
        cap_info = next((c for c in live_captions_data if c["id"] == found_caption_id), None)
        time_str = cap_info['timestamp_str'] if cap_info else "that time"
        return f"Found discussion about '{search_term}' around {time_str}. NavigateToID:{found_caption_id}"
    return f"Sorry, couldn't find discussion about '{search_term}'."

# --- NEW Intent Definitions ---
INTENTS_EN = {
    "GET_TIME": {
        "keywords": ["time"],
        "function": get_current_time,
        "requires_entity": False,
        "priority": 10
    },
    "GET_DATE": {
        "keywords": ["date"],
        "function": get_current_date,
        "requires_entity": False,
        "priority": 10
    },
    "OPEN_GOOGLE_DEFAULT": {
        "keywords": ["open google"], # More specific phrase
        "function": lambda: open_website(), # Lambda to match no-arg call
        "requires_entity": False,
        "priority": 20 # Higher priority than general search
    },
    "SEARCH_GOOGLE": {
        "keywords": ["google", "search", "find", "look up"],
        "function": search_google,
        "entity_name": "query",
        "requires_entity": True,
        "entity_extract_patterns": [
            r"(?:google|search|find|look up)(?:\s+on google)?(?:\s+for)?\s+(.+)",
            r"(.+)\s+(?:on )?google" # e.g. "cats on google"
        ],
        "default_entity_prompt": "What would you like to search on Google?",
        "priority": 5
    },
    "SEARCH_YOUTUBE": {
        "keywords": ["youtube", "search", "find", "play"],
        "function": search_youtube,
        "entity_name": "query",
        "requires_entity": True,
        "entity_extract_patterns": [
            r"(?:youtube|search|find|play)(?:\s+on youtube)?(?:\s+for)?\s+(.+)",
            r"(.+)\s+on youtube"
        ],
        "default_entity_prompt": "What would you like to search on YouTube?",
        "priority": 5
    },
    "GET_WEATHER_DEFAULT": {
        "keywords": ["weather"],
        # This intent might be triggered if no location is found by GET_WEATHER_LOCATION
        "function": lambda: get_weather(), # Uses default location
        "requires_entity": False,
        "priority": 3 # Lower priority than specific location weather
    },
    "GET_WEATHER_LOCATION": {
        "keywords": ["weather"], # Same primary keyword, relies on entity extraction
        "function": get_weather,
        "entity_name": "location",
        "requires_entity": True,
         "entity_extract_patterns": [
            r"weather(?:\s+in|\s+for)\s+([\w\s]+)" , # weather in London
            r"what's the weather like in\s+([\w\s]+)",
            r"tell me the weather for\s+([\w\s]+)"
        ],
        "default_entity_prompt": "For which location should I check the weather?",
        "priority": 6 # Higher than default weather
    },
    "OPEN_FOLDER": {
        "keywords": ["open", "show me", "access"],
        # Check for folder keywords to distinguish from LAUNCH_APPLICATION
        "secondary_keywords_check": ["folder", "directory"] + list(USER_FOLDERS.keys()),
        "function": open_folder,
        "entity_name": "folder_key",
        "requires_entity": True,
        "entity_extract_patterns": [
            # Try to match exact folder keys first
            r"(?:open|show me|access)(?:\s+(?:the|my))?\s+(" + "|".join(USER_FOLDERS.keys()) + r")(?:\s+folder|\s+directory)?",
            r"(?:open|show me|access)(?:\s+(?:the|my))?\s+([\w\s]+?)(?:\s+folder|\s+directory)"
        ],
        "default_entity_prompt": f"Which folder? (e.g., {', '.join(USER_FOLDERS.keys())})",
        "priority": 15
    },
    "LAUNCH_APPLICATION": {
        "keywords": ["launch", "open", "start", "run"],
        "function": launch_application,
        "entity_name": "app_name",
        "requires_entity": True,
        "entity_extract_patterns": [
            r"(?:launch|open|start|run)\s+([\w\s\.-]+)" # [\w\s\.-]+ allows for app names with dots like "cmd.exe"
        ],
        "default_entity_prompt": "Which application would you like to launch?",
        "priority": 10 # Lower than OPEN_FOLDER to avoid "open documents" being "launch documents"
    },
    "PRESS_ENTER": {
        "keywords": ["press enter", "hit enter", "enter key"],
        "function": press_enter,
        "requires_entity": False,
        "priority": 10
    },
    "TYPE_TEXT": {
        "keywords": ["type", "write", "text", "dictate"],
        "function": type_text,
        "entity_name": "text_to_type",
        "requires_entity": True,
        "entity_extract_patterns": [
            r"(?:type|write|text|dictate)(?:\s+this)?(?:\s+text)?\s+(.+)"
        ],
        "default_entity_prompt": "What text should I type?",
        "priority": 5
    },
    "NAVIGATE_TO_KEYWORD": {
        "keywords": ["navigate", "show", "find", "go to", "jump to", "talked about", "discussion", "part about"],
        "function": navigate_to_keyword_time,
        "entity_name": "topic",
        "requires_entity": True,
        "entity_extract_patterns": [
             r"(?:navigate(?:\s+to)?|show\s*me|find|go\s*to|jump\s*to)\s*(?:discussion|part|section)?\s*(?:on|about)?\s*(?:where we talked about)?\s*(.+)"
        ],
        "default_entity_prompt": "What topic do you want to navigate to in the captions?",
        "priority": 7
    }
}

ALL_INTENT_SETS = {
    "english": INTENTS_EN,
    "hindi": {}, # Add Hindi intents similarly if needed
    # ... other languages ...
}

# --- Recognizer Instance & Helpers (same as before) ---
def get_recognizer_mic(mic_index=None):
    recognizer = sr.Recognizer(); recognizer.energy_threshold = 3000
    recognizer.dynamic_energy_threshold = True
    try:
        mic_list = sr.Microphone.list_microphone_names()
        if not mic_list: print("Error: No microphones found."); return None, None
        actual_idx = mic_index if mic_index is not None and isinstance(mic_index, int) and 0 <= mic_index < len(mic_list) else 0
        if mic_index is not None and (not isinstance(mic_index, int) or not (0 <= mic_index < len(mic_list))):
            print(f"Warning: Mic index {mic_index} invalid. Using default {actual_idx}.")
        microphone = sr.Microphone(device_index=actual_idx)
        print(f"Using microphone {actual_idx}: {mic_list[actual_idx]}")
        return recognizer, microphone
    except Exception as e: print(f"Error initializing mic: {e}"); return None, None

def adjust_noise(recognizer, source, duration=AMBIENT_NOISE_DURATION):
    print(f"Adjusting for ambient noise ({duration}s)...")
    try: recognizer.adjust_for_ambient_noise(source, duration=duration); print(f"Ambient noise OK. Threshold: {recognizer.energy_threshold}")
    except Exception as e: print(f"Could not adjust for ambient noise: {e}")

# --- Live Captioning Thread Function (same as before) ---
def captioning_loop():
    global live_captions_data, keyword_to_caption_id, recognizer_caption, microphone_caption, captioning_active, caption_language_key_global, caption_id_counter
    if not recognizer_caption or not microphone_caption:
        print("Captioning Error: Mic/Recognizer not init."); captioning_active.clear(); return
    whisper_lang_code = SUPPORTED_LANGUAGES[caption_language_key_global].get("whisper")
    print(f"Captioning thread started. Lang: {caption_language_key_global} (Whisper: {whisper_lang_code or 'auto'}), Mic: {microphone_caption.device_index}")
    with microphone_caption as source:
        adjust_noise(recognizer_caption, source, duration=1.5)
        while captioning_active.is_set():
            try:
                recognizer_caption.pause_threshold = 0.7
                audio = recognizer_caption.listen(source, timeout=1.0, phrase_time_limit=10)
            except sr.WaitTimeoutError: continue
            except Exception as e: print(f"Captioning listen error: {e}"); time.sleep(0.1); continue
            if not captioning_active.is_set(): break
            try:
                rec_text = recognizer_caption.recognize_whisper(audio, model=WHISPER_MODEL, language=whisper_lang_code).strip()
                if rec_text:
                    now = datetime.datetime.now(); caption_id_counter += 1
                    cap_id = f"caption-{now.strftime('%Y%m%d%H%M%S%f')}-{caption_id_counter}"
                    keywords = simple_extract_keywords(rec_text, caption_language_key_global)
                    cap_entry = {"id": cap_id, "timestamp_str": now.strftime("%H:%M:%S"), "iso_timestamp": now.isoformat(), "text": rec_text, "keywords": keywords}
                    live_captions_data.append(cap_entry)
                    for kw in keywords:
                        if kw not in keyword_to_caption_id: keyword_to_caption_id[kw] = cap_id
                    print(f"[{cap_entry['timestamp_str']}] {rec_text[:60]}... (KW: {keywords[:3]})")
            except sr.UnknownValueError: pass
            except sr.RequestError as e: print(f"Captioning Whisper API error: {e}"); time.sleep(5)
            except Exception as e: print(f"Captioning processing error: {e}"); traceback.print_exc()
    print("Captioning thread finished.")


# --- Flask App Setup (same) ---
app = Flask(__name__)
CORS(app)

# --- API Endpoints (get_languages, get_microphones, STT, Translate, Captioning control - same) ---
@app.route('/api/languages', methods=['GET'])
def get_supported_languages():
    # ... (same as before)
    lang_list = [{"key": k, "name": v.get("name", k.capitalize())} for k, v in SUPPORTED_LANGUAGES.items()]
    return jsonify({"status": "success", "languages": lang_list})


@app.route('/api/microphones', methods=['GET'])
def get_microphones_api():
    # ... (same as before)
    try:
        mic_list = sr.Microphone.list_microphone_names()
        mics = [{"index": i, "name": name} for i, name in enumerate(mic_list)]
        if not mics:
            return jsonify({"status":"warning", "message": "No microphones detected.", "microphones":[]})
        return jsonify({"status": "success", "microphones": mics})
    except Exception as e:
        print(f"Error listing microphones: {e}")
        try:
            sr.Microphone() 
            return jsonify({"status":"warning", "message": f"Could not list all mics ({e}), default might work.", "microphones":[{"index":0, "name":"Default"}]})
        except Exception as e_inner:
             return jsonify({"status": "error", "message": f"Failed to list/access mics: {e_inner}"}), 500

# --- MODIFIED listen_command_api ---
@app.route('/api/listen_command', methods=['POST'])
def listen_command_api():
    if captioning_active.is_set():
        return jsonify({"status": "error", "message": "Stop live captioning before using commands."}), 409

    data = request.get_json()
    mic_idx_str = data.get('mic_index')
    language_key = data.get('language_key', DEFAULT_LANGUAGE_KEY).lower()

    if language_key not in SUPPORTED_LANGUAGES:
        return jsonify({"status": "error", "message": f"Unsupported language: {language_key}"}), 400

    active_intents = ALL_INTENT_SETS.get(language_key)
    if not active_intents:
        return jsonify({"status": "warning", "message": f"No intents defined for {language_key}."}), 200

    whisper_lang_code = SUPPORTED_LANGUAGES[language_key].get("whisper")
    try:
        mic_index_val = int(mic_idx_str) if mic_idx_str is not None and str(mic_idx_str).isdigit() else None
    except ValueError: mic_index_val = None

    recognizer, microphone = get_recognizer_mic(mic_index_val)
    if not recognizer or not microphone:
        return jsonify({"status": "error", "message": "Mic initialization failed."}), 500

    recognized_text = None; error_message = None; action_result = None; status_code = 200
    try:
        with microphone as source:
            adjust_noise(recognizer, source)
            lang_name = SUPPORTED_LANGUAGES[language_key]['name']
            print(f"Listening for INTENTS in {lang_name} (Whisper '{WHISPER_MODEL}', lang: {whisper_lang_code or 'auto'})...")
            try:
                audio = recognizer.listen(source, timeout=15, phrase_time_limit=15)
            except sr.WaitTimeoutError:
                return jsonify({"status": "timeout", "message": "No command detected."})

        print(f"Processing intent with Whisper...")
        try:
            recognized_text_original = recognizer.recognize_whisper(audio, model=WHISPER_MODEL, language=whisper_lang_code)
            recognized_text = recognized_text_original.lower().strip() if recognized_text_original else ""
            print(f"Whisper recognized ({language_key}): '{recognized_text_original}'")

            if not recognized_text:
                action_result = "Whisper recognized empty string."
            else:
                # --- Intent Matching Logic ---
                possible_matches = []
                for intent_name, intent_def in active_intents.items():
                    score = 0
                    # Check primary keywords
                    primary_keywords_found = [kw for kw in intent_def["keywords"] if kw in recognized_text]
                    if not primary_keywords_found and "keywords_any" not in intent_def : # if "keywords" is meant as "all must be present"
                        continue
                    if "keywords_any" in intent_def: # if any of these keywords_any trigger the intent
                         if not any(kw_any in recognized_text for kw_any in intent_def["keywords_any"]):
                            continue
                    
                    score += len(primary_keywords_found) * 2 # Weight primary keywords higher

                    # Optional: check for secondary keywords to refine
                    if "secondary_keywords_check" in intent_def:
                        if not any(skw in recognized_text for skw in intent_def["secondary_keywords_check"]):
                            # If secondary check fails, this intent is not a good match, unless it's a very generic primary keyword
                            if len(primary_keywords_found) <=1 and primary_keywords_found[0] in ["open", "search"]: # generic keywords
                                continue # skip if secondary check fails for generic keywords

                    priority = intent_def.get("priority", 0)
                    possible_matches.append({
                        "name": intent_name, "definition": intent_def,
                        "score": score, "priority": priority
                    })
                
                if not possible_matches:
                    action_result = f"Recognized '{recognized_text_original}', but no clear intent matched."
                else:
                    # Sort by priority (desc), then by score (desc)
                    possible_matches.sort(key=lambda x: (x["priority"], x["score"]), reverse=True)
                    best_match = possible_matches[0]
                    matched_intent_name = best_match["name"]
                    matched_intent_def = best_match["definition"]
                    print(f"Best Intent Match: '{matched_intent_name}' (Score: {best_match['score']}, Priority: {best_match['priority']})")

                    extracted_entity = None
                    if matched_intent_def.get("requires_entity"):
                        entity_patterns = matched_intent_def.get("entity_extract_patterns", [])
                        for pattern in entity_patterns:
                            match = re.search(pattern, recognized_text_original, re.IGNORECASE) # Use original case for entity
                            if match and match.groups():
                                extracted_entity = match.group(1).strip()
                                print(f"Extracted entity for '{matched_intent_def.get('entity_name', 'arg')}': '{extracted_entity}'")
                                break # Found entity with first pattern
                        
                        if not extracted_entity:
                            action_result = matched_intent_def.get("default_entity_prompt", f"I need more information for '{matched_intent_name}'.")
                            # Don't execute if required entity is missing
                            matched_intent_def = None
                    
                    if matched_intent_def: # If intent is still valid for execution
                        action_func = matched_intent_def["function"]
                        if matched_intent_def.get("requires_entity"):
                            if extracted_entity:
                                action_result = action_func(extracted_entity)
                            # else: action_result already set by prompt
                        else: # No entity required
                            action_result = action_func()
            # --- End Intent Matching Logic ---

        except sr.UnknownValueError: error_message = "Whisper could not understand audio."
        except sr.RequestError as e: error_message = f"Whisper RequestError: {e}"; status_code = 503
        except Exception as e:
            error_message = f"Whisper/execution error: {e}"; traceback.print_exc(); status_code = 500
        if error_message: print(error_message)

    except Exception as e:
        error_message = f"Listening setup error: {e}"; traceback.print_exc(); status_code = 500
        if error_message: print(error_message)

    response_payload = {"recognized_text": recognized_text_original if 'recognized_text_original' in locals() else None}
    if error_message:
        response_payload.update({"status": "error", "message": error_message})
        return jsonify(response_payload), status_code
    else:
        response_payload.update({"status": "success", "action_taken": action_result})
        return jsonify(response_payload)


@app.route('/api/listen_stt', methods=['POST'])
def listen_stt_api():
    # ... (same as before, or can also be updated to use Whisper preferentially if desired)
    if captioning_active.is_set():
        return jsonify({"status": "error", "message": "Stop live captioning before using STT."}), 409
    data = request.get_json(); mic_idx_str = data.get('mic_index')
    language_key = data.get('language_key', DEFAULT_LANGUAGE_KEY).lower()
    if language_key not in SUPPORTED_LANGUAGES: return jsonify({"status": "error", "message": f"Unsupported language: {language_key}"}), 400
    
    google_stt_lang = SUPPORTED_LANGUAGES[language_key].get("google_stt")
    whisper_stt_lang = SUPPORTED_LANGUAGES[language_key].get("whisper")
    use_google = bool(google_stt_lang) # Prioritize Google for this endpoint if configured

    if not use_google and not whisper_stt_lang:
        return jsonify({"status": "error", "message": f"No STT (Google/Whisper) for {language_key}."}), 500
    
    try: mic_idx_val = int(mic_idx_str) if mic_idx_str is not None and str(mic_idx_str).isdigit() else None
    except ValueError: mic_idx_val = None
    recognizer, microphone = get_recognizer_mic(mic_idx_val)
    if not recognizer or not microphone: return jsonify({"status": "error", "message": "Mic init failed."}), 500

    text = None; error_message = None; status_code = 200
    try:
        with microphone as source:
            adjust_noise(recognizer, source); lang_name = SUPPORTED_LANGUAGES[language_key]['name']
            stt_service = "Google STT" if use_google else "Whisper STT"
            stt_code = google_stt_lang if use_google else (whisper_stt_lang or 'auto')
            print(f"Listening for SPEECH ({lang_name}) via {stt_service} ({stt_code})...")
            try: audio = recognizer.listen(source, timeout=20, phrase_time_limit=30)
            except sr.WaitTimeoutError: return jsonify({"status": "timeout", "message": "No speech detected."})
        
        print(f"Processing with {stt_service} ({stt_code})...")
        try:
            if use_google: text = recognizer.recognize_google(audio, language=stt_code)
            else: text = recognizer.recognize_whisper(audio, model=WHISPER_MODEL, language=stt_code)
            print(f"{stt_service} recognized: {text}")
        except sr.UnknownValueError: error_message = f"{stt_service} couldn't understand."
        except sr.RequestError as e: error_message = f"{stt_service} API fail: {e}"; status_code = 503
        except Exception as e: error_message = f"{stt_service} error: {e}"; traceback.print_exc(); status_code = 500
    except Exception as e: error_message = f"STT setup error: {e}"; traceback.print_exc(); status_code = 500
    
    if error_message: print(error_message); return jsonify({"status": "error", "message": error_message}), status_code
    return jsonify({"status": "success", "recognized_text": text or ""})


@app.route('/api/translate', methods=['POST'])
def translate_api():
    # ... (same as before)
    data = request.get_json(); text_to_translate = data.get('text')
    target_lang_key = data.get('target_language_key', DEFAULT_LANGUAGE_KEY).lower()
    if not text_to_translate and text_to_translate != "": return jsonify({"status": "error", "message": "Missing text."}), 400
    if target_lang_key not in SUPPORTED_LANGUAGES: return jsonify({"status": "error", "message": f"Unsupported target lang: {target_lang_key}"}), 400
    translate_code = SUPPORTED_LANGUAGES[target_lang_key].get("translate")
    if not translate_code: return jsonify({"status": "error", "message": f"Translate code not for {target_lang_key}."}), 500
    
    lang_name = SUPPORTED_LANGUAGES[target_lang_key]['name']
    print(f"Translating to {lang_name} ({translate_code}): '{text_to_translate[:50]}...'")
    try:
        if not text_to_translate.strip(): translated = ""
        else: translated = GoogleTranslator(source='auto', target=translate_code).translate(text_to_translate)
        print(f"Translation: {translated}")
        return jsonify({"status": "success", "translated_text": translated or ""})
    except Exception as e: return jsonify({"status": "error", "message": f"Translation error: {e}"}), 500

# --- Live Captioning API Endpoints (start, stop, get - same as before) ---
@app.route('/api/start_captioning', methods=['POST'])
def start_captioning_api():
    # ... (same)
    global captioning_active, captioning_thread, recognizer_caption, microphone_caption, caption_language_key_global, live_captions_data, keyword_to_caption_id, caption_id_counter
    if captioning_active.is_set() and captioning_thread and captioning_thread.is_alive():
        return jsonify({"status": "warning", "message": "Captioning already active."})
    data = request.get_json(); mic_idx_str = data.get('mic_index')
    lang_key = data.get('language_key', DEFAULT_LANGUAGE_KEY).lower()
    if lang_key not in SUPPORTED_LANGUAGES: return jsonify({"status": "error", "message": f"Unsupported lang: {lang_key}"}), 400
    mic_idx_val = int(mic_idx_str) if mic_idx_str is not None and str(mic_idx_str).isdigit() else None
    caption_language_key_global = lang_key
    recognizer_c, microphone_c = get_recognizer_mic(mic_idx_val)
    if not recognizer_c or not microphone_c: return jsonify({"status": "error", "message": "Mic init failed for captioning."}), 500
    recognizer_caption, microphone_caption = recognizer_c, microphone_c
    live_captions_data, keyword_to_caption_id, caption_id_counter = [], {}, 0
    captioning_active.set()
    captioning_thread = threading.Thread(target=captioning_loop, daemon=True); captioning_thread.start()
    return jsonify({"status": "success", "message": "Captioning started."})

@app.route('/api/stop_captioning', methods=['POST'])
def stop_captioning_api():
    # ... (same)
    global captioning_active, captioning_thread
    if not captioning_active.is_set() and (not captioning_thread or not captioning_thread.is_alive()):
        return jsonify({"status": "warning", "message": "Captioning not active."})
    captioning_active.clear()
    if captioning_thread and captioning_thread.is_alive():
        captioning_thread.join(timeout=5)
        if captioning_thread.is_alive(): print("Warning: Captioning thread didn't stop cleanly.")
    return jsonify({"status": "success", "message": "Captioning stopped."})

@app.route('/api/get_captions', methods=['GET'])
def get_captions_api():
    # ... (same)
    global live_captions_data, keyword_to_caption_id
    last_count_str = request.args.get('last_count', default='0')
    try: last_count = int(last_count_str)
    except ValueError: last_count = 0
    if last_count < 0: last_count = 0
    
    current_len = len(live_captions_data)
    new_captions = live_captions_data[last_count:current_len] if last_count < current_len else []
    all_keywords = sorted(list(keyword_to_caption_id.keys()))
    return jsonify({"status": "success", "captions": new_captions, "all_keywords": all_keywords, "current_total_captions": current_len})


# --- Main Execution (same as before) ---
if __name__ == '__main__':
    print("Starting Flask server - Voice AI Suite...")
    print(f"OS: {platform.system()} {platform.release()}, Whisper Model: {WHISPER_MODEL}")
    print("User Folders (check paths):")
    for k, v in USER_FOLDERS.items(): print(f"- {k}: {v} (Exists: {os.path.exists(v)})")
    print("Languages & Intents:")
    for lang_key, lang_data in SUPPORTED_LANGUAGES.items():
        intents_avail = "INTENTS DEFINED" if lang_key in ALL_INTENT_SETS and ALL_INTENT_SETS[lang_key] else "NO INTENTS"
        print(f"- {lang_data.get('name', lang_key.capitalize())} ({lang_key}): {intents_avail}")
    print("---")
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print('Running in PyInstaller bundle. Assets MEIPASS:', sys._MEIPASS)
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)