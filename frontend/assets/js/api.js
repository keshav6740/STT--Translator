const API_BASE_URL = `${window.location.origin}/api`;

export async function apiRequest(path, options = {}) {
    const sessionId = window.localStorage.getItem("voice-ai-session-id");
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: { "Content-Type": "application/json", "X-Session-Id": sessionId || "" },
        ...options,
    });
    const data = await response.json();
    if (!response.ok) {
        const error = new Error(data.message || `Request failed: ${response.status}`);
        error.status = response.status;
        throw error;
    }
    return data;
}

export function openCaptionStream(onCaption) {
    const sessionId = window.localStorage.getItem("voice-ai-session-id");
    const source = new EventSource(`${API_BASE_URL}/captions/stream?session_id=${encodeURIComponent(sessionId || "")}`);
    source.addEventListener("snapshot", (event) => {
        onCaption({ type: "snapshot", payload: JSON.parse(event.data) });
    });
    source.addEventListener("caption", (event) => onCaption(JSON.parse(event.data)));
    return source;
}
