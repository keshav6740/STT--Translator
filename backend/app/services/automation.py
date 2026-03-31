import datetime
import os
import platform
import subprocess
import urllib.parse
import webbrowser

import requests


class AutomationService:
    def __init__(self, user_folders: dict, default_weather_location: str) -> None:
        self.user_folders = user_folders
        self.default_weather_location = default_weather_location

    def open_website(self, url: str = "https://www.google.com") -> str:
        try:
            webbrowser.open(url)
            return f"Website opened: {url}"
        except Exception as exc:
            return f"Unable to open website: {exc}"

    def search_youtube(self, query: str) -> str:
        if not query:
            return "No search query provided for YouTube."
        return self.open_website(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}")

    def search_google(self, query: str) -> str:
        if not query:
            return "No search query provided for Google."
        return self.open_website(f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}")

    def launch_application(self, app_name: str) -> str:
        if not app_name:
            return "No application name provided."
        system = platform.system().lower()
        app_map = {
            "windows": {"notepad": ["notepad.exe"], "calculator": ["calc.exe"], "explorer": ["explorer.exe"], "cmd": ["cmd.exe"], "powershell": ["powershell.exe"]},
            "darwin": {"terminal": ["open", "-a", "Terminal"], "calculator": ["open", "-a", "Calculator"], "textedit": ["open", "-a", "TextEdit"]},
            "linux": {"terminal": ["gnome-terminal"], "calculator": ["gnome-calculator"], "gedit": ["gedit"]},
        }
        command = app_map.get(system, {}).get(app_name.lower())
        if not command:
            return f"'{app_name}' is not in the approved application list for {system}."
        try:
            subprocess.Popen(command)
            return f"Launched '{app_name}'."
        except Exception as exc:
            return f"Unable to launch '{app_name}': {exc}"

    def open_folder(self, folder_key: str) -> str:
        path = self.user_folders.get(folder_key.lower())
        if not path:
            return f"Folder key '{folder_key}' is not defined."
        if not os.path.isdir(path):
            return f"Folder path does not exist: {path}"
        system = platform.system().lower()
        try:
            if system == "windows":
                os.startfile(path)
            elif system == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return f"Opened folder: {folder_key}"
        except Exception as exc:
            return f"Unable to open folder '{folder_key}': {exc}"

    @staticmethod
    def get_current_time() -> str:
        return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."

    @staticmethod
    def get_current_date() -> str:
        return f"Today's date is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."

    def get_weather(self, location: str | None = None) -> str:
        location = location or self.default_weather_location
        url = (
            f"https://wttr.in/{urllib.parse.quote_plus(location)}"
            "?format=Location: %l%nCondition: %C (%c)%nTemp: %t (%f)%nWind: %w%nHumidity: %h%nPrecip: %p"
        )
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text.strip() or f"Could not retrieve weather for {location}."
        except Exception as exc:
            return f"Weather lookup failed for {location}: {exc}"
