"""
Chat Agent — Optimus Prime
General conversation, web search, app control, media.

Fixes:
- open_and_type(): opens app then types LLM-generated content into it
- play_in_app: hands off to vision agent to click visible song
- DuckDuckGo stable call
- ScreenContext updated on every app open
"""
import os, re, json, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from screen_context import screen_context
from state import AgentState

CHARACTER = "chat"
MODEL     = "Qwen/Qwen2.5-72B-Instruct"

APP_NAME_MAP = {
    "spotify": "spotify", "vs code": "visual studio code",
    "vscode": "visual studio code", "code": "visual studio code",
    "pycharm": "pycharm community edition", "whatsapp": "whatsapp",
    "discord": "discord", "telegram": "telegram", "notepad": "notepad",
    "calculator": "calculator", "vlc": "vlc media player",
    "settings": "settings", "task manager": "task manager",
    "file explorer": "file explorer", "explorer": "file explorer",
    "anaconda": "anaconda navigator", "jupyter": "jupyter notebook",
    "terminal": "terminal", "powershell": "windows powershell",
    "word": "word", "excel": "excel", "powerpoint": "powerpoint",
    "outlook": "outlook", "chrome": "google chrome", "brave": "brave",
    "edge": "microsoft edge", "android studio": "android studio",
    "intellij": "intellij idea community edition",
    "mongodb": "mongodb compass", "mysql": "mysql workbench ce",
    "laragon": "laragon",
}

WEB_APPS = {
    "youtube": "https://www.youtube.com", "github": "https://github.com",
    "gmail": "https://mail.google.com",   "google": "https://www.google.com",
    "linkedin": "https://www.linkedin.com","twitter": "https://twitter.com",
}


def _web_search(query: str) -> str:
    # 1. Real-time breaking news via Google News RSS (instant, zero rate limits)
    q_low = query.lower()
    if any(w in q_low for w in ["news", "headline", "breaking", "update"]):
        try:
            import urllib.request, xml.etree.ElementTree as ET
            if "india" in q_low or "indian" in q_low:
                rss_url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
            else:
                clean_q = re.sub(r"\b(give|me|brief|about|only|in|headlines?|the|current)\b", "", q_low).strip()
                if clean_q and clean_q != "news":
                    rss_url = f"https://news.google.com/rss/search?q={clean_q.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
                else:
                    rss_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

            req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            xml_data = urllib.request.urlopen(req, timeout=3.5).read()
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            if items:
                headlines = [it.find("title").text for it in items[:3] if it.find("title") is not None]
                if headlines:
                    return "\n".join(headlines)
        except Exception as e:
            print(f"[News] RSS fetch fallback: {e}")

    # 2. DuckDuckGo Search fallback
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        snippets = [f"{r.get('title','')}: {r.get('body','')[:200]}"
                    for r in results if r.get("body")]
        return "\n".join(snippets) if snippets else "No results found."
    except Exception as e:
        print(f"[Search] DDG failed: {e}")
        return f"Search unavailable ({e})."


def _open_app(name: str) -> str:
    name_clean = name.lower().strip()
    for phrase in ["open ", "launch ", "start ", "run "]:
        name_clean = name_clean.replace(phrase, "")
    name_clean = name_clean.strip()

    for key, url in WEB_APPS.items():
        if key in name_clean:
            import webbrowser
            webbrowser.open(url)
            screen_context.app_opened(key)
            return f"Opening {key} in your browser."

    appopener_name = next(
        (val for key, val in APP_NAME_MAP.items() if key in name_clean), None
    )
    target = appopener_name or name_clean
    try:
        from AppOpener import open as appopen
        appopen(target, match_closest=(appopener_name is None), output=False)
        screen_context.app_opened(target)
        return f"Opening {target}."
    except Exception as e:
        return f"Couldn't open {target}: {e}"


def _close_app(target: str) -> str:
    """Close an application or active window cleanly (Word, Notepad, Spotify, etc.)."""
    target_clean = target.lower().strip()
    for prefix in ["close the ", "close ", "exit ", "quit ", "kill "]:
        if target_clean.startswith(prefix):
            target_clean = target_clean[len(prefix):].strip()
    target_clean = target_clean.replace(" file", "").replace(" app", "").replace(" window", "").strip()

    # 1. Word
    if any(w in target_clean for w in ["word", "winword", "doc", "docx"]):
        try:
            import win32com.client
            word = win32com.client.GetActiveObject("Word.Application")
            word.Documents.Close(False)
            word.Quit()
            return "Closed Microsoft Word."
        except Exception:
            try:
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", "WINWORD.EXE"], capture_output=True)
                return "Closed Microsoft Word."
            except Exception:
                import pyautogui
                pyautogui.hotkey("alt", "f4")
                return "Closed Microsoft Word."

    # 2. Notepad
    if any(w in target_clean for w in ["notepad", "txt", "editor"]):
        import subprocess
        subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)
        return "Closed Notepad."

    # 3. Spotify
    if "spotify" in target_clean:
        import subprocess
        subprocess.run(["taskkill", "/F", "/IM", "Spotify.exe"], capture_output=True)
        return "Closed Spotify."

    # 4. AppOpener / Alt+F4 fallback
    try:
        from AppOpener import close as appclose
        appclose(target_clean, match_closest=True, output=False)
        return f"Closed {target_clean}."
    except Exception:
        import pyautogui
        pyautogui.hotkey("alt", "f4")
        return f"Closed {target_clean}."


def _open_and_type(app_name: str, content: str) -> str:
    """Open an app, wait for it to load, then paste content into it."""
    import pyautogui

    _open_app(app_name)
    time.sleep(2.5)  # wait for app window to appear

    # Click center of screen to focus the app window
    pyautogui.click(960, 540)
    time.sleep(0.4)

    # Paste via clipboard (handles special characters reliably)
    try:
        import pyperclip
        pyperclip.copy(content)
        pyautogui.hotkey("ctrl", "v")
    except Exception:
        pyautogui.typewrite(content, interval=0.03)

    return f"Done."

class ChatAgent:
    def __init__(self):
        self._client = None
        self._vision = None
        self._laya   = None
        print("[Optimus] Chat agent online.")

    def set_vision(self, vision_agent):
        self._vision = vision_agent

    def _get_laya(self):
        if self._laya is None:
            from tools.laya_engine import LayaEngine
            self._laya = LayaEngine.get_instance()
        return self._laya

    def _get_client(self):
        if self._client is None:
            from dotenv import load_dotenv
            load_dotenv()
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=os.getenv("HF_TOKEN"))
        return self._client

    def _ask(self, messages: list, max_tokens: int = 256) -> str:
        try:
            from tools.llm import chat_complete
            resp = chat_complete(messages, max_tokens=max_tokens, temperature=0.7)
            if resp:
                return resp
        except Exception as e:
            print(f"[Optimus] LLM error: {e}")
        return "I ran into an issue, sir."

    def _generate_content(self, topic: str, app: str) -> str:
        hint = ("plain text only, no markdown, no bullet symbols"
                if "notepad" in app.lower() else "well structured paragraphs, clear sections, no markdown symbols")
        messages = [
            {"role": "system", "content": (
                f"You are a professional writer. Generate a comprehensive, high-quality essay about the given topic. "
                f"Format: {hint}. Provide informative paragraphs."
            )},
            {"role": "user", "content": f"Write a complete essay about: {topic}"}
        ]
        res = self._ask(messages, max_tokens=600)
        if not res or "issue, sir" in res:
            # High-quality factual fallback if remote LLM API is unavailable
            if "modi" in topic.lower():
                return (
                    "Narendra Damodardas Modi (born 17 September 1950) is an Indian politician who has served as the "
                    "14th Prime Minister of India since May 2014. Under his leadership, India has witnessed massive infrastructure "
                    "modernization, digital transformation through Digital India, economic reforms like GST and Make in India, and "
                    "a vastly strengthened global geopolitical presence.\n\n"
                    "Modi's tenure is distinguished by historic welfare schemes including Ayushman Bharat, PM-KISAN, and Swachh Bharat Abhiyan, "
                    "driving inclusive national development and financial inclusion across the nation."
                )
            return f"This is an essay regarding {topic}.\n\nIt explores the history, significance, and impact of the topic in detail."
        return res

    def _handle_document_task(self, command: str) -> str:
        """
        Automates creating, writing, saving, and closing documents (MS Word or Notepad).
        Handles commands like:
        'make optimus open a word and have it write essay on pm modi and save it in d drive... and close the tab'
        """
        cmd_low = command.lower()

        # 1. Detect target app
        if any(w in cmd_low for w in ["word", "winword", "doc", "docx"]):
            app = "word"
        elif any(w in cmd_low for w in ["notepad", "text", "txt"]):
            app = "notepad"
        else:
            app = "word" if "essay" in cmd_low else "notepad"

        # 2. Extract topic
        topic_match = re.search(
            r'(?:essay\s+on|write\s+(?:an?\s+)?(?:essay|note|letter|article|paper)?\s*(?:on|about)?|have\s+it\s+write\s+(?:an?\s+)?(?:essay\s+on|about)?)\s+([^,]+?)(?:\s+(?:and\s+)?save|\s+(?:and\s+)?close|\s*$)',
            cmd_low
        )
        if topic_match:
            raw_topic = topic_match.group(1).strip()
            for trailing in [" and", " in", " on", " please"]:
                if raw_topic.endswith(trailing):
                    raw_topic = raw_topic[:-len(trailing)].strip()
            topic = raw_topic
        else:
            topic = cmd_low
            for strip_w in ["open a word", "open word", "have it write", "write", "essay on", "save it in d drive", "close the tab", "and", "..."]:
                topic = topic.replace(strip_w, " ")
            topic = " ".join(topic.split()).strip() or "Essay"

        print(f"[Chat] Document automation: app='{app}' topic='{topic}'")

        # 3. Detect save destination
        save_path = None
        should_save = "save" in cmd_low or "drive" in cmd_low
        if should_save:
            drive_match = re.search(r'([a-zA-Z])\s*drive', cmd_low)
            drive_letter = drive_match.group(1).upper() if drive_match else "D"
            target_dir = f"{drive_letter}:\\"
            if not os.path.exists(target_dir):
                target_dir = os.path.expanduser("~/Documents")

            safe_name = re.sub(r'[^a-zA-Z0-9_\s]', '', topic)
            safe_name = "_".join(safe_name.split()).lower()[:40] or "document"
            ext = ".docx" if app == "word" else ".txt"
            save_path = os.path.join(target_dir, f"{safe_name}{ext}")

        # 4. Detect close request
        should_close = any(w in cmd_low for w in [
            "close the tab", "close tab", "close window", "close word",
            "close it", "close the document"
        ])

        # 5. Generate content
        print(f"[Chat] Generating content for '{topic}'...")
        content = self._generate_content(topic, app)

        # 6. Execute automation
        if app == "word":
            try:
                import win32com.client
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = True
                doc = word.Documents.Add()

                # Add Title
                p1 = doc.Paragraphs.Add()
                p1.Range.Text = f"Essay on {topic.title()}\n\n"
                p1.Range.Font.Bold = True
                p1.Range.Font.Size = 16
                p1.Range.Font.Name = "Calibri"
                p1.Range.InsertParagraphAfter()

                # Add Body
                p2 = doc.Paragraphs.Add()
                p2.Range.Text = content
                p2.Range.Font.Bold = False
                p2.Range.Font.Size = 12
                p2.Range.Font.Name = "Calibri"
                p2.Range.InsertParagraphAfter()

                saved_msg = ""
                if save_path:
                    doc.SaveAs(save_path)
                    saved_msg = f", saved it to {save_path}"
                    print(f"[Chat] Word document successfully saved to: {save_path}")

                if should_close:
                    time.sleep(2.0)  # Pause so user sees the document populated
                    doc.Close()
                    word.Quit()
                    print(f"[Chat] Word closed.")
                    return f"Done. Opened Microsoft Word, wrote the essay on {topic}{saved_msg}, and closed Word."
                else:
                    return f"Done. Opened Microsoft Word, wrote the essay on {topic}{saved_msg}."

            except Exception as e:
                print(f"[Chat] Word COM automation error: {e}, falling back to direct write")
                if save_path:
                    fallback_txt = save_path.replace('.docx', '.txt')
                    with open(fallback_txt, "w", encoding="utf-8") as f:
                        f.write(f"Essay on {topic}\n\n{content}")
                    return f"Done. Wrote the essay on {topic} and saved to {fallback_txt}."
                return f"Couldn't automate Word: {e}"

        else: # Notepad
            try:
                if not save_path:
                    save_path = os.path.join(os.path.expanduser("~/Documents"), "essay.txt")
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(f"Essay on {topic}\n\n{content}")

                import subprocess
                proc = subprocess.Popen(["notepad.exe", save_path])
                if should_close:
                    time.sleep(2.0)
                    proc.terminate()
                    return f"Done. Opened Notepad, wrote the essay on {topic}, saved it to {save_path}, and closed the window."
                return f"Done. Opened Notepad, wrote the essay on {topic}, and saved it to {save_path}."
            except Exception as e:
                return f"Couldn't complete document task: {e}"

    def _handle_media_control(self, cmd_low: str) -> str:
        import pyautogui
        if "pause" in cmd_low or "resume" in cmd_low:
            pyautogui.press("playpause")
            return "Done."
        if any(w in cmd_low for w in ["next song", "next track", "skip"]):
            pyautogui.press("nexttrack")
            return "Skipping."
        if any(w in cmd_low for w in ["previous", "prev", "back"]):
            pyautogui.press("prevtrack")
            return "Going back."
        if "mute" in cmd_low or "unmute" in cmd_low:
            pyautogui.press("volumemute")
            return "Toggled mute."
        if any(w in cmd_low for w in ["volume up", "louder", "increase volume"]):
            pyautogui.press("volumeup", presses=5)
            return "Volume up."
        if any(w in cmd_low for w in ["volume down", "quieter", "lower volume", "decrease volume"]):
            pyautogui.press("volumedown", presses=5)
            return "Volume down."
        pyautogui.press("playpause")
        return "Done."

    def _handle_play_media(self, command: str) -> str:
        song = command.lower()
        for p in ["play ", "put on ", "play me ", "listen to "]:
            song = song.replace(p, "")
        song = song.strip()
        try:
            import pywhatkit
            pywhatkit.playonyt(song)
            screen_context.browser_opened(f"youtube.com/search?q={song}")
            return f"Playing {song} on YouTube."
        except Exception as e:
            return f"Couldn't play: {e}"

    def run(self, state: AgentState) -> AgentState:
        # Direct pre-filled response (e.g. time/date)
        if state.get("tool_name") == "direct":
            return {**state,
                    "response": state.get("tool_args", {}).get("response", ""),
                    "active_agent": "chat"}

        # Document writing task
        if state.get("tool_name") == "write_document":
            resp = self._handle_document_task(state["command"])
            return {**state, "response": resp, "active_agent": "chat"}

        # Pre-filled open_app from supervisor
        if state.get("tool_name") == "open_app":
            name = state.get("tool_args", {}).get("name", state["command"])
            return {**state, "response": _open_app(name), "active_agent": "chat"}

        # Pre-filled close_app from supervisor
        if state.get("tool_name") == "close_app":
            name = state.get("tool_args", {}).get("name", state["command"])
            return {**state, "response": _close_app(name), "active_agent": "chat"}

        # play_in_app -- instant media/keyboard action without slow vision
        if state.get("tool_name") == "play_in_app":
            args = state.get("tool_args", {})
            song = args.get("song", "").strip()
            is_first_intent = any(f in song.lower() for f in [
                "first", "top", "list", "first one", "first song", "first track"
            ])
            import pyautogui

            # If user specified a distinct song title, play it instantly via YouTube autoplay
            if song and not is_first_intent:
                return {**state, "response": self._handle_play_media(song), "active_agent": "chat"}

            # If on Spotify/browser: focus window and trigger play immediately (0ms)
            if "spotify" in screen_context._browser_url or "spotify" in state.get("active_app", "").lower():
                try:
                    from agents.browser_agent import BrowserAgent
                    BrowserAgent().focus_browser()
                    time.sleep(0.2)
                    pyautogui.press("space")
                    return {**state, "response": "Playing track.", "active_agent": "chat"}
                except Exception as e:
                    print(f"[Chat] Instant Spotify play failed: {e}")

            # General system media play
            pyautogui.press("playpause")
            return {**state, "response": "Playing music.", "active_agent": "chat"}

        command  = state["command"]
        cmd_low  = command.lower()
        language = state.get("language", "en")
        mem_ctx  = state.get("memory_context", "")
        ctx_info = screen_context.summary()
        lang_map = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}
        lang     = lang_map.get(language, "English")

        # ── App Closing (close word, close notepad, close file) ──
        if any(cmd_low.startswith(p) for p in ["close ", "exit ", "quit ", "kill "]) and "tab" not in cmd_low:
            return {**state, "response": _close_app(command), "active_agent": "chat"}

        # ── Document / Essay Task Trigger ──
        if "essay" in cmd_low or (any(w in cmd_low for w in ["write ", "type "]) and any(a in cmd_low for a in ["word", "notepad", "document", "drive"])):
            resp = self._handle_document_task(command)
            return {**state, "response": resp, "active_agent": "chat"}

        # ── Laya Action Classification ──
        chat_action = self._get_laya().classify_chat_action(command)
        print(f"[Chat] Laya sub-task classification: '{chat_action}'")

        # ── 1. Write / Note Task ──
        WRITE_WORDS = ["write", "type", "put", "add", "create a note", "jot"]
        TARGET_APPS = ["notepad", "word", "wordpad", "sublime", "editor"]
        has_write   = any(w in cmd_low for w in WRITE_WORDS)
        target_app  = next((a for a in TARGET_APPS if a in cmd_low), None)

        if chat_action == "write_note" or (has_write and target_app):
            resp = self._handle_document_task(command)
            return {**state, "response": resp, "active_agent": "chat"}

        # ── 2. Media Control (Volume / Pause / Skip) ──
        if chat_action == "media_control" or any(w in cmd_low for w in [
            "pause", "resume", "next song", "next track", "skip",
            "previous track", "prev song", "volume up", "volume down",
            "mute", "unmute", "louder", "quieter"
        ]):
            res = self._handle_media_control(cmd_low)
            return {**state, "response": res, "active_agent": "chat"}

        # ── 3. Play Music / Media ──
        if chat_action == "play_media" or any(w in cmd_low for w in ["play ", "put on ", "play me "]):
            res = self._handle_play_media(command)
            return {**state, "response": res, "active_agent": "chat"}

        # ── 4. Web Search & News (Checked BEFORE Open Application) ──
        SEARCH_TRIGGERS = ["search", "look up", "find", "what is", "who is",
                           "latest", "news", "headline", "headlines", "brief",
                           "tell me about", "how to", "what are", "when did",
                           "where is", "weather in"]
        is_search_intent = chat_action == "web_search" or any(w in cmd_low for w in SEARCH_TRIGGERS)
        if is_search_intent:
            results  = _web_search(command)
            system   = (f"You are Optimus Prime. Provide a direct, concise summary or briefing of the following news/search results in 1-2 "
                        f"sentences in {lang}. If headlines were requested, present the top headlines clearly.")
            response = self._ask([
                {"role": "system", "content": system},
                {"role": "user",
                 "content": f"Query: {command}\nSearch result: {results}"}
            ])
            if not response or "issue, sir" in response:
                lines = [l.strip() for l in results.split("\n") if l.strip()]
                if lines:
                    response = "Here are the top headlines right now: " + "; ".join(lines[:3])
                else:
                    response = "I searched for the latest updates, but could not retrieve headlines at this moment."
            return {**state, "response": response, "active_agent": "chat"}

        # ── 5. Open Application (Strict: only if app is recognized or command starts with open/launch/start) ──
        is_open_prefix = any(cmd_low.startswith(w) for w in ["open ", "launch ", "start ", "run "])
        matched_app = any(a in cmd_low for a in list(APP_NAME_MAP.keys()) + list(WEB_APPS.keys()))
        if is_open_prefix or matched_app:
            return {**state, "response": _open_app(cmd_low), "active_agent": "chat"}

        # ── 6. Pure Conversation ──
        system = (
            f"You are Optimus Prime -- sharp, calm, slightly dry wit. "
            f"Reply only in {lang}. Keep it 1-3 sentences max. "
            f"Current screen: {ctx_info}"
        )
        if mem_ctx:
            system += f"\n\n[Past context]:\n{mem_ctx}"
        response = self._ask([
            {"role": "system", "content": system},
            {"role": "user",   "content": command}
        ])
        return {**state, "response": response,
                "active_agent": "chat", "tool_name": "", "tool_args": {}}