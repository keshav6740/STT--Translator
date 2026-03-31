import { apiRequest, openCaptionStream } from "./api.js";

const el = {
    micSelect: document.getElementById("micSelect"),
    healthStatus: document.getElementById("healthStatus"),
    healthMeta: document.getElementById("healthMeta"),
    commandLangSelect: document.getElementById("commandLangSelect"),
    sttLangSelect: document.getElementById("sttLangSelect"),
    targetLangSelect: document.getElementById("targetLangSelect"),
    captionLangSelect: document.getElementById("captionLangSelect"),
    listenCmdBtn: document.getElementById("listenCmdBtn"),
    recordSttBtn: document.getElementById("recordSttBtn"),
    translateBtn: document.getElementById("translateBtn"),
    startCaptionBtn: document.getElementById("startCaptionBtn"),
    stopCaptionBtn: document.getElementById("stopCaptionBtn"),
    exportCaptionBtn: document.getElementById("exportCaptionBtn"),
    cmdStatus: document.getElementById("cmdStatus"),
    cmdResult: document.getElementById("cmdResult"),
    sttStatus: document.getElementById("sttStatus"),
    originalText: document.getElementById("originalText"),
    translateStatus: document.getElementById("translateStatus"),
    translatedText: document.getElementById("translatedText"),
    liveCaptionStatus: document.getElementById("liveCaptionStatus"),
    captionsContainer: document.getElementById("captionsContainer"),
    keywordsSummaryContainer: document.getElementById("keywordsSummaryContainer"),
};

const state = { captionSource: null, keywords: new Set() };

if (!window.localStorage.getItem("voice-ai-session-id")) {
    window.localStorage.setItem("voice-ai-session-id", crypto.randomUUID());
}

function setStatus(node, message) {
    node.textContent = message;
}

function downloadUrl(path) {
    const sessionId = window.localStorage.getItem("voice-ai-session-id") || "";
    return `${window.location.origin}${path}${path.includes("?") ? "&" : "?"}session_id=${encodeURIComponent(sessionId)}`;
}

function selectedMic() {
    return el.micSelect.value;
}

function addOption(select, value, label, selected = false) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = selected;
    select.appendChild(option);
}

function renderKeywords() {
    el.keywordsSummaryContainer.innerHTML = "";
    [...state.keywords].sort().forEach((keyword) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "keyword";
        chip.textContent = keyword;
        chip.addEventListener("click", () => setStatus(el.liveCaptionStatus, `Keyword indexed: say "go to ${keyword}" in Command Console.`));
        el.keywordsSummaryContainer.appendChild(chip);
    });
}

function navigateToCaption(captionId) {
    const target = document.getElementById(captionId);
    if (!target) {
        setStatus(el.liveCaptionStatus, `Caption ${captionId} is not in the current transcript view.`);
        return;
    }
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("flash-focus");
    setTimeout(() => target.classList.remove("flash-focus"), 1600);
    setStatus(el.liveCaptionStatus, "Jumped to the referenced transcript moment.");
}

function renderCaption(caption) {
    if (caption?.type === "snapshot") {
        el.captionsContainer.innerHTML = "";
        state.keywords = new Set();
        (caption.payload.captions || []).slice().reverse().forEach((item) => renderCaption(item));
        return;
    }

    const item = document.createElement("article");
    item.className = "caption-entry";
    item.id = caption.id;

    const meta = document.createElement("div");
    meta.className = "caption-meta";
    const timestamp = document.createElement("span");
    timestamp.textContent = caption.timestamp_str;
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = caption.detected_language || "auto";
    meta.append(timestamp, tag);

    const text = document.createElement("div");
    text.textContent = caption.text;

    const keywords = document.createElement("div");
    keywords.className = "caption-meta";
    (caption.keywords || []).forEach((keyword) => {
        const chip = document.createElement("span");
        chip.className = "keyword";
        chip.textContent = keyword;
        keywords.appendChild(chip);
        state.keywords.add(keyword);
    });

    item.append(meta, text, keywords);
    el.captionsContainer.prepend(item);
    renderKeywords();
}

async function loadHealth() {
    try {
        const data = await apiRequest("/health");
        el.healthStatus.textContent = "Online";
        el.healthMeta.textContent = `${data.whisper_model} model, ${data.languages} languages`;
    } catch (error) {
        el.healthStatus.textContent = "Offline";
        el.healthMeta.textContent = error.message;
    }
}

async function loadLanguages() {
    const data = await apiRequest("/languages");
    [el.commandLangSelect, el.sttLangSelect, el.targetLangSelect, el.captionLangSelect].forEach((select) => {
        select.innerHTML = "";
    });

    data.languages.forEach(({ key, name }) => {
        addOption(el.commandLangSelect, key, name, key === "english");
        addOption(el.sttLangSelect, key, name, key === "");
        addOption(el.targetLangSelect, key || "english", name, key === "english");
        addOption(el.captionLangSelect, key, name, key === "");
    });
}

async function loadMics() {
    try {
        const data = await apiRequest("/microphones");
        el.micSelect.innerHTML = "";
        data.microphones.forEach(({ index, name }, order) => addOption(el.micSelect, String(index), `${index}: ${name}`, order === 0));
        if (!data.microphones.length) {
            addOption(el.micSelect, "", "No microphones found", true);
            el.micSelect.disabled = true;
        }
    } catch (error) {
        el.micSelect.innerHTML = "";
        addOption(el.micSelect, "", "Microphones unavailable", true);
        el.micSelect.disabled = true;
        throw error;
    }
}

function bindEvents() {
    el.listenCmdBtn.addEventListener("click", async () => {
        el.listenCmdBtn.disabled = true;
        setStatus(el.cmdStatus, "Listening for command...");
        try {
            const data = await apiRequest("/listen/command", {
                method: "POST",
                body: JSON.stringify({ mic_index: selectedMic(), language_key: el.commandLangSelect.value }),
            });
            setStatus(el.cmdStatus, `Heard: ${data.recognized_text}`);
            el.cmdResult.textContent = data.action_taken || "";
            const navMatch = (data.action_taken || "").match(/NavigateToID:([^\s]+)/);
            if (navMatch) {
                navigateToCaption(navMatch[1]);
            }
        } catch (error) {
            setStatus(el.cmdStatus, error.message);
        } finally {
            el.listenCmdBtn.disabled = false;
        }
    });

    el.recordSttBtn.addEventListener("click", async () => {
        el.recordSttBtn.disabled = true;
        setStatus(el.sttStatus, "Listening for speech...");
        try {
            const data = await apiRequest("/listen/stt", {
                method: "POST",
                body: JSON.stringify({ mic_index: selectedMic(), language_key: el.sttLangSelect.value }),
            });
            el.originalText.value = data.recognized_text || "";
            setStatus(el.sttStatus, "Speech captured.");
        } catch (error) {
            setStatus(el.sttStatus, error.message);
        } finally {
            el.recordSttBtn.disabled = false;
        }
    });

    el.translateBtn.addEventListener("click", async () => {
        el.translateBtn.disabled = true;
        setStatus(el.translateStatus, "Translating...");
        try {
            const data = await apiRequest("/translate", {
                method: "POST",
                body: JSON.stringify({ text: el.originalText.value, target_language_key: el.targetLangSelect.value || "english" }),
            });
            el.translatedText.value = data.translated_text || "";
            setStatus(el.translateStatus, "Translation complete.");
        } catch (error) {
            setStatus(el.translateStatus, error.message);
        } finally {
            el.translateBtn.disabled = false;
        }
    });

    el.startCaptionBtn.addEventListener("click", async () => {
        el.startCaptionBtn.disabled = true;
        setStatus(el.liveCaptionStatus, "Starting caption stream...");
        el.captionsContainer.innerHTML = "";
        state.keywords = new Set();
        renderKeywords();
        try {
            await apiRequest("/captions/start", {
                method: "POST",
                body: JSON.stringify({ mic_index: selectedMic(), language_key: el.captionLangSelect.value }),
            });
            state.captionSource?.close();
            state.captionSource = openCaptionStream(renderCaption);
            el.startCaptionBtn.disabled = true;
            el.stopCaptionBtn.disabled = false;
            setStatus(el.liveCaptionStatus, "Captioning live.");
        } catch (error) {
            setStatus(el.liveCaptionStatus, error.message);
            el.startCaptionBtn.disabled = false;
        }
    });

    el.stopCaptionBtn.addEventListener("click", async () => {
        el.stopCaptionBtn.disabled = true;
        setStatus(el.liveCaptionStatus, "Stopping captions...");
        try {
            await apiRequest("/captions/stop", { method: "POST", body: JSON.stringify({}) });
            state.captionSource?.close();
            state.captionSource = null;
            setStatus(el.liveCaptionStatus, "Captioning stopped.");
        } catch (error) {
            setStatus(el.liveCaptionStatus, error.message);
        } finally {
            el.startCaptionBtn.disabled = false;
        }
    });

    el.exportCaptionBtn.addEventListener("click", () => {
        window.open(downloadUrl("/api/captions/export?format=txt"), "_blank", "noopener,noreferrer");
    });
}

async function bootstrap() {
    try {
        await Promise.all([loadHealth(), loadLanguages(), loadMics()]);
    } catch (error) {
        setStatus(el.liveCaptionStatus, `Startup issue: ${error.message}`);
    }
    bindEvents();
    el.stopCaptionBtn.disabled = true;
    el.translateBtn.disabled = false;
}

bootstrap();
