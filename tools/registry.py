"""
Tools Registry — every capability Optimus has lives here.
No if/else blocks anywhere else. Just call REGISTRY["tool_name"](**args).
"""
import webbrowser
import pyautogui
import subprocess
import os
from AppOpener import open as appopen

# ── Registry store ──
REGISTRY   = {}   # name → function
TOOL_SPECS = []   # list of {name, description, parameters} for LLM

def tool(name: str, description: str, parameters: dict):
    """Decorator — registers a function as a callable tool."""
    def decorator(fn):
        REGISTRY[name] = fn
        TOOL_SPECS.append({
            "name":        name,
            "description": description,
            "parameters":  parameters
        })
        return fn
    return decorator


# ================================================================
# WEB / SEARCH TOOLS
# ================================================================
@tool(
    name="web_search",
    description="Search the web using DuckDuckGo and return a summary.",
    parameters={"query": "string — what to search for"}
)
def web_search(query: str) -> str:
    from duckduckgo_search import DDGS
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        return " ".join([r["body"] for r in results]) if results else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


@tool(
    name="open_url",
    description="Open any URL in the default browser.",
    parameters={"url": "string — full URL to open"}
)
def open_url(url: str) -> str:
    webbrowser.open(url)
    return f"Opened {url}."


# ================================================================
# APP LAUNCHER
# ================================================================
APP_NAME_MAP = {
    "brave":           "brave",
    "chrome":          "google chrome",
    "google chrome":   "google chrome",
    "edge":            "microsoft edge",
    "vs code":         "visual studio code",
    "vscode":          "visual studio code",
    "code":            "visual studio code",
    "pycharm":         "pycharm community edition",
    "android studio":  "android studio",
    "intellij":        "intellij idea community edition",
    "spyder":          "spyder",
    "jupyter":         "jupyter notebook",
    "terminal":        "terminal",
    "powershell":      "windows powershell",
    "cmd":             "command prompt",
    "git bash":        "git bash",
    "word":            "word",
    "excel":           "excel",
    "powerpoint":      "powerpoint",
    "outlook":         "outlook",
    "onenote":         "onenote",
    "notepad":         "notepad",
    "sticky notes":    "sticky notes",
    "to do":           "microsoft to do",
    "todo":            "microsoft to do",
    "calendar":        "calendar",
    "mail":            "mail",
    "vlc":             "vlc media player",
    "capcut":          "capcut",
    "calculator":      "calculator",
    "file explorer":   "file explorer",
    "explorer":        "file explorer",
    "task manager":    "task manager",
    "settings":        "settings",
    "paint":           "paint",
    "camera":          "camera",
    "whatsapp":        "whatsapp",
    "discord":         "discord",
    "telegram":        "telegram",
    "mongodb":         "mongodb compass",
    "mysql":           "mysql workbench ce",
    "laragon":         "laragon",
    "anaconda":        "anaconda navigator",
    "winrar":          "winrar",
    "proton vpn":      "proton vpn",
    "vpn":             "proton vpn",
}

WEB_SHORTCUTS = {
    "youtube":      "https://www.youtube.com",
    "gmail":        "https://mail.google.com",
    "github":       "https://www.github.com",
    "linkedin":     "https://www.linkedin.com",
    "twitter":      "https://www.twitter.com",
    "google":       "https://www.google.com",
    "instagram":    "https://www.instagram.com",
    "chatgpt":      "https://chat.openai.com",
    "whatsapp web": "https://web.whatsapp.com",
}

@tool(
    name="open_app",
    description="Open any installed application or website by name.",
    parameters={"name": "string — app name e.g. 'brave', 'vs code', 'spotify', 'youtube'"}
)
def open_app(name: str) -> str:
    n = name.lower().strip()
    # Web shortcut
    for key, url in WEB_SHORTCUTS.items():
        if key in n:
            webbrowser.open(url)
            return f"Opened {key}."
    # App map → AppOpener exact match
    for keyword, exact in APP_NAME_MAP.items():
        if keyword in n:
            try:
                appopen(exact, match_closest=False, output=False)
                return f"Opened {exact}."
            except Exception as e:
                return f"Couldn't open {exact}: {e}"
    # Fallback
    try:
        appopen(n, match_closest=True, output=False)
        return f"Opened {n}."
    except:
        return f"Don't know how to open '{name}'."


# ================================================================
# MEDIA CONTROLS
# ================================================================
@tool(
    name="media_control",
    description="Control media playback — play, pause, skip, next, previous.",
    parameters={"action": "string — one of: play, pause, skip, next, previous, stop"}
)
def media_control(action: str) -> str:
    a = action.lower()
    if a in ("skip", "next"):
        pyautogui.press("nexttrack")
    elif a in ("previous", "prev", "back"):
        pyautogui.press("prevtrack")
    elif a in ("pause", "play", "toggle"):
        pyautogui.press("playpause")
    elif a == "stop":
        pyautogui.press("stop")
    elif a == "volume_up":
        pyautogui.press("volumeup")
    elif a == "volume_down":
        pyautogui.press("volumedown")
    return f"Media: {action}."


@tool(
    name="play_youtube",
    description="Search and play a song or video on YouTube using pywhatkit.",
    parameters={"query": "string — song or video to play"}
)
def play_youtube(query: str) -> str:
    import pywhatkit
    try:
        pywhatkit.playonyt(query)
        return f"Playing {query} on YouTube."
    except Exception as e:
        return f"Couldn't play {query}: {e}"


# ================================================================
# MEMORY TOOLS  (implementations injected by memory_agent)
# ================================================================
@tool(
    name="memory_store",
    description="Save something to long-term memory.",
    parameters={
        "text":     "string — what to remember",
        "category": "string — 'general' | 'code' | 'post'"
    }
)
def memory_store(text: str, category: str = "general") -> str:
    # Real implementation injected by memory_agent at runtime
    return "[memory_store not yet wired]"


@tool(
    name="memory_recall",
    description="Recall something from long-term memory.",
    parameters={"query": "string — what to look for"}
)
def memory_recall(query: str) -> str:
    # Real implementation injected by memory_agent at runtime
    return "[memory_recall not yet wired]"


# ================================================================
# CODE TOOLS
# ================================================================
@tool(
    name="run_code",
    description="Execute a Python code snippet and return stdout/stderr.",
    parameters={
        "code":     "string — Python code to run",
        "timeout":  "int — max seconds to wait (default 15)"
    }
)
def run_code(code: str, timeout: int = 15) -> str:
    import tempfile, sys
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                         delete=False, encoding="utf-8") as f:
            f.write(code)
            fname = f.name
        result = subprocess.run(
            [sys.executable, fname],
            capture_output=True, text=True, timeout=timeout
        )
        os.unlink(fname)
        out = result.stdout.strip()
        err = result.stderr.strip()
        if err and not out:
            return f"Error:\n{err}"
        return out or "Code ran with no output."
    except subprocess.TimeoutExpired:
        return "Code timed out."
    except Exception as e:
        return f"Run failed: {e}"


@tool(
    name="inject_to_editor",
    description="Type code directly into the currently focused code editor.",
    parameters={"code": "string — code to inject"}
)
def inject_to_editor(code: str) -> str:
    import pyperclip
    try:
        pyperclip.copy(code)
        pyautogui.hotkey("ctrl", "v")
        return "Code injected into editor."
    except Exception as e:
        return f"Injection failed: {e}"


# ================================================================
# REMINDER TOOLS  (wired by reminder_agent)
# ================================================================
@tool(
    name="set_reminder",
    description="Set a reminder that fires at a specific time with voice + notification.",
    parameters={
        "text":      "string — what to remind",
        "remind_at": "string — time in HH:MM 24h format"
    }
)
def set_reminder(text: str, remind_at: str) -> str:
    # Real implementation injected by reminder_agent at runtime
    return "[set_reminder not yet wired]"


@tool(
    name="list_reminders",
    description="List all currently scheduled reminders.",
    parameters={}
)
def list_reminders() -> str:
    # Real implementation injected by reminder_agent at runtime
    return "[list_reminders not yet wired]"


# ── Helper used by agents ──
def call_tool(name: str, args: dict) -> str:
    """Call a registered tool by name with args dict."""
    fn = REGISTRY.get(name)
    if not fn:
        return f"Unknown tool: {name}"
    try:
        return fn(**args)
    except Exception as e:
        return f"Tool '{name}' failed: {e}"


def get_tool_specs_text() -> str:
    """Return tool specs as a readable string for LLM system prompts."""
    lines = []
    for spec in TOOL_SPECS:
        params = ", ".join([f"{k}: {v}" for k, v in spec["parameters"].items()])
        lines.append(f'- {spec["name"]}({params}): {spec["description"]}')
    return "\n".join(lines)