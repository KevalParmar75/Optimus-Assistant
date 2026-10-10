"""
Browser Agent — Bumblebee
Opens URLs in your existing Chrome via os.startfile.
Uses Vision Agent for all clicking/interaction — no guessing.
"""
import re, json, threading, time, os, webbrowser
from state import AgentState

CHARACTER = "bumblebee"
VOICE     = "en-US-AndrewNeural"
MODEL     = "Qwen/Qwen2.5-72B-Instruct"


def friendly_url_name(url: str) -> str:
    """Convert raw URL into a clean, human-friendly spoken name."""
    u = url.lower().strip()
    if "spotify.com/collection/tracks" in u:
        return "Spotify Liked Songs"
    if "spotify.com" in u:
        return "Spotify"
    if "youtube.com/watch" in u:
        return "YouTube video"
    if "youtube.com" in u:
        return "YouTube"
    if "chat.openai.com" in u or "chatgpt.com" in u:
        return "ChatGPT"
    if "google.com/search" in u:
        return "Google Search"
    if "google.com" in u:
        return "Google"
    if "github.com" in u:
        return "GitHub"
    if "twitter.com" in u or "x.com" in u:
        return "Twitter"
    if "reddit.com" in u:
        return "Reddit"
    if "netflix.com" in u:
        return "Netflix"
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        domain = re.sub(r"^(www\.|open\.|app\.)", "", domain)
        name = domain.split(".")[0]
        if name:
            return name.capitalize()
    except Exception:
        pass
    return "the page"


class BrowserAgent:
    def __init__(self):
        self._lock       = threading.Lock()
        self._client     = None
        self._is_open    = False
        self._last_url   = ""
        self._vision     = None   # injected by main after init
        print("[Bumblebee] Browser agent ready.")

    def set_vision(self, vision_agent):
        """Inject vision agent after both are initialized."""
        self._vision = vision_agent

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=os.getenv("HF_TOKEN"))
        return self._client

    def _get_browser_exe(self):
        """Find the executable path for the currently running or installed browser (preferring Brave)."""
        import subprocess
        try:
            out = subprocess.check_output(['tasklist', '/FI', 'STATUS eq RUNNING'], text=True, timeout=1.0).lower()
        except Exception:
            out = ""

        candidates = [
            ("brave.exe", [
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            ]),
            ("chrome.exe", [
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]),
            ("msedge.exe", [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ]),
        ]

        # 1. Prefer browser currently running
        for proc, paths in candidates:
            if proc in out:
                for p in paths:
                    if os.path.exists(p):
                        return p

        # 2. Prefer any installed browser
        for proc, paths in candidates:
            for p in paths:
                if os.path.exists(p):
                    return p
        return None

    def is_open(self) -> bool:
        if self._is_open:
            return True
        try:
            import subprocess
            out = subprocess.check_output(
                ["tasklist", "/FI", "STATUS eq RUNNING"], text=True, timeout=1.0
            ).lower()
            if any(b in out for b in ["brave.exe", "chrome.exe", "msedge.exe", "firefox.exe"]):
                self._is_open = True
                return True
        except Exception:
            pass
        return False

    def _open_url(self, url: str, wait: float = 2.5):
        """Open URL in active or preferred browser (Brave/Chrome/Edge) as a new tab."""
        exe = self._get_browser_exe()
        if exe:
            import subprocess
            try:
                subprocess.Popen([exe, url])
            except Exception:
                try:
                    os.startfile(url)
                except Exception:
                    webbrowser.open(url)
        else:
            try:
                os.startfile(url)
            except Exception:
                webbrowser.open(url)
        self._is_open  = True
        self._last_url = url
        try:
            from screen_context import screen_context
            screen_context.browser_opened(url)
        except Exception:
            pass
        time.sleep(wait)

    def _search_youtube(self, query: str, autoplay: bool = False):
        """Open YouTube search or directly autoplay the top video result."""
        q = query.strip().replace(" ", "+")
        if autoplay:
            try:
                import urllib.request, re
                url = f"https://www.youtube.com/results?search_query={q}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                html = urllib.request.urlopen(req, timeout=4.0).read().decode('utf-8')
                vids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
                if vids:
                    top_video_url = f"https://www.youtube.com/watch?v={vids[0]}"
                    print(f"[Bumblebee] Direct YouTube Autoplay -> {top_video_url}")
                    self._open_url(top_video_url, wait=2.5)
                    return
            except Exception as e:
                print(f"[Bumblebee] Direct video resolution failed, falling back to search page: {e}")

        # Default search page
        self._open_url(f"https://www.youtube.com/results?search_query={q}", wait=3.0)

    def _search_google(self, query: str):
        q = query.strip().replace(" ", "+")
        self._open_url(f"https://www.google.com/search?q={q}")

    def execute_plan(self, command: str) -> str:
        cmd_strip = command.strip()

        # Instant direct hotkey action (tabs, navigation, refresh)
        hotkey_msg = self.handle_browser_hotkey(command)
        if hotkey_msg:
            return hotkey_msg

        # Instant direct URL open (bypasses any model for 0ms navigation)
        if cmd_strip.startswith("open http://") or cmd_strip.startswith("open https://"):
            url = cmd_strip[5:].strip()
            self._open_url(url)
            return f"Opened {friendly_url_name(url)}."
        if cmd_strip.startswith("http://") or cmd_strip.startswith("https://"):
            self._open_url(cmd_strip)
            return f"Opened {friendly_url_name(cmd_strip)}."

        with self._lock:
            client = self._get_client()

            plan_prompt = f"""You are Bumblebee, a browser assistant.

Current session: {self._is_open}
Last URL: {self._last_url or 'none'}
Vision available: {self._vision is not None}

User command: "{command}"

Choose the right action:
- "youtube_play"   -> search YouTube AND auto-click first video to play it
- "youtube_search" -> search YouTube, show results only (no autoplay)
- "google_search"  -> search Google
- "open_url"       -> open a specific website URL
- "vision_act"     -> use screen vision to find and click/interact with something on screen
- "scroll"         -> scroll the page (value: positive=down, negative=up in pixels)
- "hotkey"         -> keyboard shortcut (value: "k"=yt pause, "j"=back 10s, "l"=fwd 10s, "m"=mute, "f"=fullscreen, "ctrl+t"=new tab)
- "press"          -> single key press
- "done"           -> finished

RULES:
- Translate Hindi/Gujarati intent to English
- "play X", "play X on youtube" -> youtube_play
- "search X on youtube" -> youtube_search  
- "pause", "resume", "forward", "rewind", "fullscreen" on a video -> use vision_act (VL will find the button)
- "click X", "find X on page", "scroll to X" -> vision_act
- Always end with done

Return ONLY JSON array:
[{{"action": "...", "value": "...", "description": "..."}}]"""

            # ⚡ Fast non-autoregressive decision via local LayaEngine
            try:
                from tools.laya_engine import LayaEngine
                laya = LayaEngine.get_instance()
                action = laya.choose_browser_action(command)
                
                # Extract search query or URL argument from command
                val = command.strip()
                for prefix in ["play ", "search for ", "search ", "open ", "go to ", "look up ", "find "]:
                    if val.lower().startswith(prefix):
                        val = val[len(prefix):].strip()
                        break
                for suffix in [" on youtube", " on google", " in browser"]:
                    if val.lower().endswith(suffix):
                        val = val[:-len(suffix)].strip()
                        break
                
                if val.startswith("http://") or val.startswith("https://"):
                    action = "open_url"
                
                plan = [
                    {"action": action, "value": val, "description": f"Executing {action}"},
                    {"action": "done", "value": "", "description": "Finished action"}
                ]
                print(f"[Bumblebee] Local Laya Plan: {json.dumps(plan, indent=2)}")
            except Exception as e:
                print(f"[LayaEngine] Local decision fallback, trying remote client: {e}")
                try:
                    from tools.llm import chat_complete
                    raw = chat_complete([{"role": "user", "content": plan_prompt}], max_tokens=400, temperature=0.1)
                    raw = re.sub(r"```json|```", "", raw).strip()
                    plan = json.loads(raw)
                    print(f"[Bumblebee] Remote Plan: {json.dumps(plan, indent=2)}")
                except Exception as ex:
                    print(f"[Bumblebee] Plan failed: {ex}")
                    return "Couldn't figure out the steps for that."

            last_desc = "Done."
            for step in plan:
                action = step.get("action", "")
                value  = str(step.get("value", ""))
                desc   = step.get("description", "")
                print(f"[Bumblebee] {action} -> {value}")

                try:
                    if action == "youtube_play":
                        self._search_youtube(value, autoplay=True)

                    elif action == "youtube_search":
                        self._search_youtube(value, autoplay=False)

                    elif action == "google_search":
                        self._search_google(value)

                    elif action == "open_url":
                        self._open_url(value)

                    elif action == "vision_act":
                        # Hand off to vision agent
                        if self._vision:
                            result = self._vision.find_and_act(value or desc)
                            last_desc = result
                        else:
                            print("[Bumblebee] Vision not available")

                    elif action == "scroll":
                        import pyautogui
                        px = int(value) if value.lstrip("-").isdigit() else 300
                        pyautogui.scroll(-(px // 100))

                    elif action == "hotkey":
                        import pyautogui
                        time.sleep(0.5)
                        keys = value.split("+")
                        pyautogui.hotkey(*keys)

                    elif action == "press":
                        import pyautogui
                        time.sleep(0.5)
                        pyautogui.press(value)

                    elif action == "done":
                        last_desc = desc or "Done."
                        break

                except Exception as e:
                    print(f"[Bumblebee] Step failed ({action}={value}): {e}")
                    continue

            return last_desc

    def focus_browser(self):
        """Bring the active browser window (Brave, Chrome, Edge) to foreground before key action."""
        try:
            import win32gui, win32con
            def enum_cb(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    for b in ["brave", "chrome", "edge", "firefox"]:
                        if b in title:
                            extra.append(hwnd)
                            break
            hwnds = []
            win32gui.EnumWindows(enum_cb, hwnds)
            if hwnds:
                try:
                    win32gui.ShowWindow(hwnds[0], win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnds[0])
                    time.sleep(0.15)
                except Exception:
                    pass
        except Exception:
            pass

    def handle_browser_hotkey(self, command: str) -> str | None:
        """
        Instantly executes standard browser tab and navigation hotkeys (0ms).
        Handles: switch tab, new tab, close tab, refresh, back, forward, fullscreen.
        """
        import pyautogui
        cmd = command.lower().strip()

        HOTKEYS = {
            "switch tab": (["ctrl", "tab"], "Switched tab."),
            "next tab": (["ctrl", "tab"], "Switched to next tab."),
            "change tab": (["ctrl", "tab"], "Switched tab."),
            "tab switch": (["ctrl", "tab"], "Switched tab."),
            "previous tab": (["ctrl", "shift", "tab"], "Switched to previous tab."),
            "prev tab": (["ctrl", "shift", "tab"], "Switched to previous tab."),
            "last tab": (["ctrl", "shift", "tab"], "Switched to previous tab."),
            "new tab": (["ctrl", "t"], "Opened a new tab."),
            "open new tab": (["ctrl", "t"], "Opened a new tab."),
            "open a new tab": (["ctrl", "t"], "Opened a new tab."),
            "tab in the current browser": (["ctrl", "t"], "Opened a new tab in current browser."),
            "tab in current browser": (["ctrl", "t"], "Opened a new tab in current browser."),
            "new tab in the current browser": (["ctrl", "t"], "Opened a new tab in current browser."),
            "close tab": (["ctrl", "w"], "Closed tab."),
            "close this tab": (["ctrl", "w"], "Closed tab."),
            "close the tab": (["ctrl", "w"], "Closed tab."),
            "reopen tab": (["ctrl", "shift", "t"], "Reopened closed tab."),
            "undo close tab": (["ctrl", "shift", "t"], "Restored closed tab."),
            "restore tab": (["ctrl", "shift", "t"], "Restored closed tab."),
            "refresh page": (["ctrl", "r"], "Refreshed page."),
            "refresh tab": (["ctrl", "r"], "Refreshed page."),
            "reload page": (["ctrl", "r"], "Reloaded page."),
            "reload tab": (["ctrl", "r"], "Reloaded page."),
            "reload": (["ctrl", "r"], "Reloaded page."),
            "refresh": (["ctrl", "r"], "Refreshed page."),
            "go back": (["alt", "left"], "Navigated back."),
            "back": (["alt", "left"], "Navigated back."),
            "go forward": (["alt", "right"], "Navigated forward."),
            "forward": (["alt", "right"], "Navigated forward."),
            "fullscreen": (["f11"], "Toggled fullscreen."),
        }

        # 1. Exact or substring match
        for phrase, (keys, msg) in HOTKEYS.items():
            if phrase in cmd:
                self.focus_browser()
                pyautogui.hotkey(*keys)
                if "close tab" in phrase:
                    self._last_url = ""
                return msg

        # 2. Heuristic match for conversational tab requests
        if "tab" in cmd:
            self.focus_browser()
            if any(w in cmd for w in ["switch", "next", "change", "cycle"]):
                pyautogui.hotkey("ctrl", "tab")
                return "Switched tab."
            if any(w in cmd for w in ["previous", "prev", "back"]):
                pyautogui.hotkey("ctrl", "shift", "tab")
                return "Switched to previous tab."
            if any(w in cmd for w in ["new", "open", "another"]):
                pyautogui.hotkey("ctrl", "t")
                return "Opened a new tab."
            if any(w in cmd for w in ["close", "kill", "remove"]):
                pyautogui.hotkey("ctrl", "w")
                return "Closed tab."

        return None

    def close_tab(self):
        import pyautogui
        self.focus_browser()
        pyautogui.hotkey("ctrl", "w")
        self._is_open  = False
        self._last_url = ""

    def type_prompt_in_browser(self, prompt: str) -> str:
        """Types prompt text into active browser app (ChatGPT, etc.) and presses Enter."""
        import pyautogui, pyperclip
        self.focus_browser()
        time.sleep(0.5)
        sw, sh = pyautogui.size()
        # Click near bottom-center of screen to focus input box
        pyautogui.click(sw // 2, sh - 140)
        time.sleep(0.3)
        pyperclip.copy(prompt)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        return f"Typed prompt into ChatGPT: {prompt}"

    def run(self, state: AgentState) -> AgentState:
        command = state["command"].lower()
        if any(w in command for w in ["close browser", "close chrome", "close brave", "close window"]):
            self.close_tab()
            return {**state, "response": "Browser closed.", "active_agent": "browser"}

        # Dedicated browser in-page prompt typing
        if state.get("tool_name") == "browser_type_prompt":
            prompt = state.get("tool_args", {}).get("prompt", state["command"])
            resp = self.type_prompt_in_browser(prompt)
            return {**state, "response": resp, "active_agent": "browser"}

        # Fast path for browser hotkey actions (tabs, navigation, refresh)
        hotkey_res = self.handle_browser_hotkey(state["command"])
        if hotkey_res:
            return {**state, "response": hotkey_res, "active_agent": "browser"}

        response = self.execute_plan(state["command"])
        return {**state, "response": response, "active_agent": "browser"}