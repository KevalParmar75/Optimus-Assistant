"""
Optimus V3 — Main Orchestrator
Transformers Universe Multi-Agent AI Assistant
"""
import asyncio, threading, time, os, re, datetime, json, sys
import customtkinter as ctk
import speech_recognition as sr
import edge_tts, pygame
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

load_dotenv()

from state  import AgentState
from agents import ChatAgent, BrowserAgent, CodeAgent, MemoryAgent, ReminderAgent, VisionAgent
from ui.hud import TransformerHUD

# ── Voice config ──
LANG_CODES = {"en": "en-IN", "hi": "hi-IN", "gu": "gu-IN"}

AGENT_VOICES = {
    "chat":     "en-GB-RyanNeural",
    "browser":  "en-US-AndrewNeural",
    "code":     "en-GB-ThomasNeural",
    "memory":   "en-GB-RyanNeural",
    "reminder": "en-US-GuyNeural",
    "vision":   "en-GB-RyanNeural",   # Optimus sees and reports
}

LANG_VOICES = {
    "hi": "hi-IN-MadhurNeural",
    "gu": "gu-IN-NiranjanNeural",
}

WAKE_WORDS     = ["optimus", "optimum", "optimas", "hey optimus"]
ACTIVE_TIMEOUT = 45
MODEL          = "google/gemma-4-31B-it"


# ================================================================
# SUPERVISOR — Laya-powered local decision engine routes commands
# ================================================================

class Supervisor:
    """
    Laya-Powered Supervisor — Routes user commands to the correct Optimus agent.

    Architecture:
    1. Instant 0ms shortcuts for time/date (no model needed)
    2. Laya local decision engine (~30ms) for all routing decisions
    3. Fallback to "chat" on any error — no external API dependency

    Replaces: keyword matching + LLM API fallback (was ~1.5s per command)
    """
    def __init__(self, browser_agent):
        self._browser_agent = browser_agent
        self._laya          = None

    def _get_laya(self):
        """Lazy-load Laya engine (singleton, loaded once into memory)."""
        if self._laya is None:
            from tools.laya_engine import LayaEngine
            self._laya = LayaEngine.get_instance()
        return self._laya

    # ── Known web shortcuts for browser navigation continuity ──
    WEB_SHORTCUTS = {
        "youtube":      "https://www.youtube.com",
        "spotify":      "https://open.spotify.com",
        "gmail":        "https://mail.google.com",
        "github":       "https://www.github.com",
        "linkedin":     "https://www.linkedin.com",
        "twitter":      "https://www.twitter.com",
        "google":       "https://www.google.com",
        "instagram":    "https://www.instagram.com",
        "chatgpt":      "https://chat.openai.com",
        "whatsapp web": "https://web.whatsapp.com",
        "reddit":       "https://www.reddit.com",
    }

    # ── Sub-pages for deep web continuity ──
    WEB_SUB_URLS = {
        "spotify": {
            "liked": "https://open.spotify.com/collection/tracks",
            "like": "https://open.spotify.com/collection/tracks",
            "favorite": "https://open.spotify.com/collection/tracks",
            "search": "https://open.spotify.com/search",
            "library": "https://open.spotify.com/collection/playlists",
            "playlist": "https://open.spotify.com/collection/playlists",
            "queue": "https://open.spotify.com/queue",
        },
        "youtube": {
            "sub": "https://www.youtube.com/feed/subscriptions",
            "history": "https://www.youtube.com/feed/history",
            "library": "https://www.youtube.com/feed/library",
            "trending": "https://www.youtube.com/feed/trending",
        }
    }

    # ── Browser app names (opening these means a browser is now active) ──
    BROWSER_APPS = ["chrome", "brave", "edge", "firefox", "browser"]

    def route(self, state: AgentState) -> AgentState:
        import datetime, re
        from screen_context import screen_context

        command = state["command"]
        cmd_low = command.lower().strip()
        active  = screen_context.active_app or ""
        browser_open = self._browser_agent.is_open() or screen_context.browser_open

        # Strip conversational assistant prefixes & temporal fillers
        for prefix in [
            "make optimus ", "tell optimus to ", "optimus please ",
            "optimus, ", "optimus ", "hey optimus, ", "hey optimus ",
            "can you please ", "can you ", "could you ", "please ",
            "now ", "just ", "also ", "then ", "and "
        ]:
            if cmd_low.startswith(prefix):
                cmd_low = cmd_low[len(prefix):].strip()

        print(f"[Supervisor] cmd='{cmd_low[:50]}' active='{active}' browser={browser_open}")

        # ═══════════════════════════════════════════════════════════
        # TIER 1: Instant 0ms shortcuts — no model needed at all
        # ═══════════════════════════════════════════════════════════

        # ── Document / Essay / Writing tasks ──
        # e.g. "open a word and have it write essay on pm modi and save it in d drive... and close the tab"
        # e.g. "write an essay on ... in word", "type a letter in notepad"
        WRITE_TRIGGERS = ["write ", "type ", "essay", "compose ", "draft "]
        DOC_APPS = ["word", "notepad", "wordpad", "document", "doc"]
        has_write_intent = any(w in cmd_low for w in WRITE_TRIGGERS)
        has_doc_app = any(a in cmd_low for a in DOC_APPS)
        if has_write_intent and (has_doc_app or "essay" in cmd_low or "save" in cmd_low):
            print(f"[Supervisor] Document writing task detected -> routing to ChatAgent")
            return {**state, "command": cmd_low, "active_agent": "chat",
                    "tool_name": "write_document", "tool_args": {"raw_command": cmd_low}}

        # ── App Closing (close word, close notepad, close spotify, close window, close file) ──
        CLOSE_TRIGGERS = ["close ", "exit ", "quit ", "kill "]
        is_close_cmd = any(cmd_low.startswith(p) for p in CLOSE_TRIGGERS)
        if is_close_cmd and not any(t in cmd_low for t in ["close tab", "close this tab", "close the tab"]):
            print(f"[Supervisor] App closing task detected -> routing to ChatAgent")
            return {**state, "command": cmd_low, "active_agent": "chat",
                    "tool_name": "close_app", "tool_args": {"name": cmd_low}}

        # ── Window Focus & Switcher (take me to browser, focus browser, switch to browser) ──
        if any(w in cmd_low for w in [
            "take me to current browser", "take me to browser", "switch to browser",
            "focus browser", "bring up browser", "open browser window", "show browser",
            "switch to brave", "switch to chrome"
        ]):
            self._browser_agent.focus_browser()
            return {**state, "active_agent": "chat",
                    "tool_name": "direct", "tool_args": {"response": "Switched to browser."}}

        # ── Tab Questions (inquiry about open tabs, not an action) ──
        is_tab_inquiry = any(q in cmd_low for q in ["what are", "which tabs", "list tabs", "show tabs", "name them", "how many tabs", "what tabs"])
        if is_tab_inquiry and "tab" in cmd_low:
            url_hint = screen_context._browser_url or "active browser"
            ans = f"You currently have your browser open on {url_hint}."
            return {**state, "active_agent": "chat",
                    "tool_name": "direct", "tool_args": {"response": ans}}

        # ── Browser Tab & Navigation Shortcuts (0ms instant execution) ──
        BROWSER_TAB_CMDS = [
            "switch tab", "next tab", "change tab", "previous tab", "prev tab",
            "new tab", "open new tab", "open a new tab", "close tab", "close this tab",
            "close the tab", "reopen tab", "restore tab", "refresh page", "refresh tab",
            "reload page", "reload tab", "go back", "go forward", "tab in the current browser",
            "tab in current browser"
        ]
        # Only treat as pure tab command if not a compound website navigation or search request
        has_search_intent = any(w in cmd_low for w in ["search for", "search ", "google "])
        if (any(b in cmd_low for b in BROWSER_TAB_CMDS) or (browser_open and "tab" in cmd_low and not is_tab_inquiry)) and not any(s in cmd_low for s in self.WEB_SHORTCUTS) and not has_search_intent:
            print(f"[Supervisor] Browser tab action shortcut -> routing to BrowserAgent")
            return {**state, "command": cmd_low, "active_agent": "browser",
                    "tool_name": "browser_action", "tool_args": {"action": cmd_low}}

        # ── News & Briefing requests (instant route to chat agent) ──
        if any(w in cmd_low for w in ["news", "headline", "headlines", "brief me", "in brief", "give me brief", "current updates"]):
            return {**state, "active_agent": "chat",
                    "tool_name": "", "tool_args": {}}

        # ── Time/Date (pure system call, zero latency) ──
        if any(w in cmd_low for w in [
            "what time", "current time", "what's the time", "time is it",
            "time it is", "tell me the time", "bata time", "kitna baje",
            "kya time", "samay kya", "what day", "what date", "today's date",
            "what is today", "current date", "aaj kya date", "aaj kya din",
        ]):
            now      = datetime.datetime.now()
            response = (f"It's {now.strftime('%I:%M %p')} on "
                        f"{now.strftime('%A, %d %B %Y')}.")
            return {**state, "active_agent": "chat",
                    "tool_name": "direct", "tool_args": {"response": response}}

        # ── Browser status check (instant query with plural/fuzzy support) ──
        is_browser_query = (
            ("browser" in cmd_low or "brave" in cmd_low or "chrome" in cmd_low) and
            any(w in cmd_low for w in ["open", "running", "active", "status"]) and
            any(w in cmd_low for w in ["is ", "are ", "any ", "check", "?", "current", "there"]) and
            not any(cmd_low.startswith(act) for act in ["open ", "close ", "launch ", "switch ", "start ", "go to "])
        )
        if is_browser_query:
            is_running = self._browser_agent.is_open() or screen_context.browser_open
            ans = "Yes, a browser is currently open." if is_running else "No, there is no browser currently open."
            return {**state, "active_agent": "chat",
                    "tool_name": "direct", "tool_args": {"response": ans}}

        # ── Vision / Screen awareness shortcuts (handles "whats on screen?" without apostrophe) ──
        clean_v = cmd_low.replace("'", "").replace("?", "").replace(",", "")
        if any(w in clean_v for w in [
            "whats on screen", "what is on screen", "what do you see",
            "describe screen", "whats open", "what is open", "whats on my screen",
            "what can you see", "look at screen", "read the screen", "read screen",
            "what does it say", "tell me whats on screen", "see on screen"
        ]):
            return {**state, "active_agent": "vision",
                    "tool_name": "", "tool_args": {}}

        # ── Notes shortcuts ──
        if any(w in cmd_low for w in [
            "take a note", "note down", "write this down",
            "add a note", "save a note", "jot down",
            "read my notes", "show my notes", "what are my notes"
        ]):
            return {**state, "active_agent": "memory",
                    "tool_name": "note", "tool_args": {"text": command}}

        # ── WhatsApp shortcuts ──
        if any(w in cmd_low for w in [
            "whatsapp", "send a message", "send message", "message to", "text to"
        ]):
            return {**state, "active_agent": "whatsapp",
                    "tool_name": "whatsapp", "tool_args": {}}

        # ── Browser close (pure hotkey, no routing needed) ──
        if any(w == cmd_low or cmd_low.startswith(w) for w in ["close browser", "close chrome",
                                       "close brave", "close window"]):
            return {**state, "active_agent": "browser",
                    "tool_name": "browser_action", "tool_args": {}}

        # ── Typing / Prompting in active browser web apps (ChatGPT, Claude, etc.) ──
        is_chatgpt_active = "chatgpt" in screen_context._browser_url or "chat.openai" in screen_context._browser_url
        has_chatgpt_keyword = any(w in cmd_low for w in ["in chatgpt", "into chatgpt", "to chatgpt", "ask chatgpt", "write in chatgpt", "tell chatgpt", "chatgpt to "])
        has_prompt_phrase = any(w in cmd_low for w in ["write a prompt", "write prompt", "type a prompt", "send prompt", "prompt it to", "tell it to"])
        
        if browser_open and (has_chatgpt_keyword or (is_chatgpt_active and has_prompt_phrase)):
            prompt_text = cmd_low
            for strip_p in [
                "now ", "write a prompt in chatgpt to ", "write a prompt in chatgpt ", 
                "prompt chatgpt to ", "type in chatgpt ", "in chatgpt ", "ask chatgpt to ",
                "write a prompt to ", "write prompt to ", "write a prompt ", "type a prompt to "
            ]:
                if strip_p in prompt_text:
                    prompt_text = prompt_text.replace(strip_p, " ")
            prompt_text = " ".join(prompt_text.split()).strip()
            print(f"[Supervisor] In-browser prompting task -> typing prompt: '{prompt_text}'")
            return {**state, "command": prompt_text, "active_agent": "browser",
                    "tool_name": "browser_type_prompt", "tool_args": {"prompt": prompt_text}}

        # ── Browser continuity for active site (e.g. on Spotify, "take me to liked songs") ──
        if browser_open:
            active_site = None
            if "spotify" in screen_context._browser_url or "spotify" in active:
                active_site = "spotify"
            elif "youtube" in screen_context._browser_url or "youtube" in active:
                active_site = "youtube"
            elif "chatgpt" in screen_context._browser_url or "chat.openai" in screen_context._browser_url:
                active_site = "chatgpt"

            if active_site and active_site in self.WEB_SUB_URLS:
                for sub_key, sub_url in self.WEB_SUB_URLS[active_site].items():
                    if sub_key in cmd_low:
                        print(f"[Supervisor] Active site continuity ({active_site}) -> navigating to {sub_url}")
                        return {**state, "command": f"open {sub_url}",
                                "active_agent": "browser",
                                "tool_name": "browser_action", "tool_args": {}}

            # Check for specific sub-pages across all apps
            for app_key, sub_map in self.WEB_SUB_URLS.items():
                if app_key in cmd_low:
                    for sub_keyword, sub_url in sub_map.items():
                        if sub_keyword in cmd_low:
                            print(f"[Supervisor] Browser continuity -> navigating to sub-page {sub_url}")
                            return {**state, "command": f"open {sub_url}",
                                    "active_agent": "browser",
                                    "tool_name": "browser_action", "tool_args": {}}
                    root_url = self.WEB_SHORTCUTS.get(app_key, "")
                    if root_url and any(w in cmd_low for w in ["open ", "go to ", "launch ", "switch to "]):
                        print(f"[Supervisor] Browser open & web shortcut detected -> navigating to {root_url}")
                        return {**state, "command": f"open {root_url}",
                                "active_agent": "browser",
                                "tool_name": "browser_action", "tool_args": {}}

            # General web shortcuts (e.g. "new tab github", "open spotify", "go to youtube")
            for name, url in self.WEB_SHORTCUTS.items():
                if name in cmd_low and any(w in cmd_low for w in ["open ", "go to ", "launch ", "switch to ", "new tab", "search for "]):
                    print(f"[Supervisor] Browser open & web shortcut detected -> navigating to {url}")
                    return {**state, "command": f"open {url}",
                            "active_agent": "browser",
                            "tool_name": "browser_action", "tool_args": {}}

            # Direct search on Google in browser ("search for ...", "google ...", "search on google")
            is_info_request = any(w in cmd_low for w in ["brief", "summarize", "tell me", "explain", "news", "headlines"])
            if not is_info_request and any(w in cmd_low for w in ["search for ", "google ", "search on google "]):
                query = cmd_low
                for prefix in ["open new tab and search for ", "open new tab and google ", "new tab and search for ", "search on google for ", "search on google ", "search for ", "google "]:
                    if prefix in query:
                        query = query.replace(prefix, "")
                        break
                query = query.strip()
                if query:
                    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                    print(f"[Supervisor] Web search detected -> navigating to {search_url}")
                    return {**state, "command": f"open {search_url}",
                            "active_agent": "browser",
                            "tool_name": "browser_action", "tool_args": {}}

        # ── Compound browser launch & action (e.g. "open brave and search for github", "open chrome and open spotify") ──
        if any(cmd_low.startswith(f"open {b} and ") for b in self.BROWSER_APPS) or cmd_low.startswith("open browser and "):
            self._browser_agent._is_open = True
            screen_context.browser_opened()
            rest = re.sub(r"^open\s+(?:brave|chrome|edge|firefox|browser)\s+and\s+", "", cmd_low).strip()
            # Check web shortcuts
            for name, url in self.WEB_SHORTCUTS.items():
                if name in rest:
                    print(f"[Supervisor] Compound browser open + '{name}' -> navigating to {url}")
                    return {**state, "command": f"open {url}",
                            "active_agent": "browser",
                            "tool_name": "browser_action", "tool_args": {}}
            # Fallback to search query
            q = rest.replace("search for ", "").replace("google ", "").strip()
            search_url = f"https://www.google.com/search?q={q.replace(' ', '+')}"
            print(f"[Supervisor] Compound browser open + search -> navigating to {search_url}")
            return {**state, "command": f"open {search_url}",
                    "active_agent": "browser",
                    "tool_name": "browser_action", "tool_args": {}}

        # ── App opening ("open X" / "launch X" / "start X") ──
        is_open_cmd = any(cmd_low.startswith(w) for w in ["open ", "launch ", "start "])
        if is_open_cmd and not (" and " in cmd_low or has_write_intent):
            # Extract the app name (strip the prefix)
            app_target = cmd_low
            for prefix in ["open ", "launch ", "start "]:
                if app_target.startswith(prefix):
                    app_target = app_target[len(prefix):].strip()
                    break

            # Is user opening a browser app? -> mark browser as active
            if any(b in app_target for b in self.BROWSER_APPS):
                self._browser_agent._is_open = True
                screen_context.browser_opened()
                print(f"[Supervisor] Opening browser app -> marking browser as active")
                return {**state, "active_agent": "chat",
                        "tool_name": "open_app", "tool_args": {"name": cmd_low}}

            # Is browser already open AND target is a known web app?
            # -> Navigate in the existing browser (continuity!)
            if browser_open:
                for name, url in self.WEB_SHORTCUTS.items():
                    if name in app_target:
                        print(f"[Supervisor] Browser open -> navigating to {url}")
                        return {**state, "command": f"open {url}",
                                "active_agent": "browser",
                                "tool_name": "browser_action", "tool_args": {}}

            # Regular app opening -> chat + open_app
            return {**state, "active_agent": "chat",
                    "tool_name": "open_app", "tool_args": {"name": cmd_low}}

        # ═══════════════════════════════════════════════════════════
        # TIER 2: Context-aware pre-routing (state-dependent, still 0ms)
        # These need browser/music state that Laya doesn't have access to
        # ═══════════════════════════════════════════════════════════

        # ── Music app open -> media controls / play-in-app ──
        MUSIC_APPS = ["spotify", "vlc", "media player",
                      "youtube music", "gaana", "jiosaavn"]
        is_music_open = (
            any(m in active for m in MUSIC_APPS) or
            (browser_open and
             any(m in screen_context._browser_url for m in MUSIC_APPS))
        )
        if is_music_open:
            if any(w in cmd_low for w in ["pause", "resume", "next",
                                           "skip", "previous", "mute", "volume"]):
                return {**state, "active_agent": "chat",
                        "tool_name": "media_control", "tool_args": {}}
            if any(w in cmd_low for w in ["play ", "put on ", "play me ",
                                           "play the ", "play first",
                                           "first song", "first track"]):
                song = cmd_low
                for phrase in ["play the ", "play ", "put on ", "play me ",
                               "first song", "first track", "song", "track"]:
                    song = song.replace(phrase, "")
                song = song.strip()
                return {**state, "active_agent": "chat",
                        "tool_name": "play_in_app",
                        "tool_args": {"app": active, "song": song}}

        # ── Browser open context routing ──
        if browser_open:
            # Vision-in-browser: clicking/interacting with visible elements
            VISION_IN_BROWSER = [
                "click", "click on", "click the", "find and click",
                "press the", "select", "first song", "first video",
                "first result", "first item", "play the first",
                "scroll", "tap", "hit the button",
            ]
            if any(w in cmd_low for w in VISION_IN_BROWSER):
                return {**state, "active_agent": "vision",
                        "tool_name": "", "tool_args": {}}

            # Standalone known web name (no "open" prefix) -> navigate in browser
            # e.g. user says "spotify" while Brave is open -> go to spotify.com
            for name, url in self.WEB_SHORTCUTS.items():
                if cmd_low.strip() == name or cmd_low.strip() == f"go to {name}":
                    print(f"[Supervisor] Browser open + '{name}' -> navigating to {url}")
                    return {**state, "command": f"open {url}",
                            "active_agent": "browser",
                            "tool_name": "browser_action", "tool_args": {}}

        # ═══════════════════════════════════════════════════════════
        # TIER 3: LAYA LOCAL DECISION ENGINE (~30ms)
        # Replaces all keyword matching + LLM API fallback
        # ═══════════════════════════════════════════════════════════
        try:
            laya  = self._get_laya()
            agent = laya.route_supervisor_agent(command, active)
            print(f"[Supervisor] Laya routed -> {agent}")
        except Exception as e:
            print(f"[Supervisor] Laya error, defaulting to chat: {e}")
            agent = "chat"

        # ── Post-Laya Sanity Checks ──
        # Guard: questions/inquiries should never mistakenly run browser actions
        if agent == "browser":
            is_question = any(cmd_low.startswith(q) for q in [
                "is ", "are ", "can you ", "could you ", "do you ", "what is ",
                "what are ", "who is ", "where is ", "why ", "how is ", "how do ",
                "how can ", "tell me about ", "tell me if ", "check if ", "which "
            ]) or cmd_low.endswith("?")
            has_browser_action = any(w in cmd_low for w in [
                "open", "go to", "search", "google", "look up", "play", "youtube",
                "watch", "visit", "browse", "navigate", ".com", ".org", "http"
            ])
            if is_question and not has_browser_action:
                print(f"[Supervisor] Guard override: '{cmd_low}' -> chat (question, not browser action)")
                agent = "chat"

        # ── Post-routing: fill tool_name/tool_args for downstream agents ──
        tool_name = ""
        tool_args = {}

        if agent == "memory":
            if any(w in cmd_low for w in ["remember this", "save this", "note that",
                                           "don't forget this", "memory stats"]):
                tool_name = "memory_store"
                tool_args = {"text": command, "category": "general"}
            else:
                tool_name = "memory_recall"
                tool_args = {"query": command}

        elif agent == "reminder":
            tool_name = "set_reminder"
            tool_args = {}

        elif agent == "whatsapp":
            tool_name = "whatsapp"
            tool_args = {}

        elif agent == "browser":
            tool_name = "browser_action"
            tool_args = {}

        elif agent == "code":
            tool_name = "generate_code"
            tool_args = {}

        elif agent == "chat":
            # Write-in-app task detection
            WRITE_WORDS = ["write", "type", "put", "add", "create a note", "jot"]
            TARGET_APPS = ["notepad", "word", "wordpad", "sublime", "editor"]
            if any(w in cmd_low for w in WRITE_WORDS) and \
               any(a in cmd_low for a in TARGET_APPS):
                tool_name = ""
                tool_args = {}

        print(f"[Supervisor] -> {agent} (tool={tool_name})")
        return {**state, "active_agent": agent,
                "tool_name": tool_name, "tool_args": tool_args}


# ================================================================
# MAIN APP
# ================================================================
ctk.set_appearance_mode("Dark")


class OptimusApp(TransformerHUD):  # <-- NOW INHERITS FROM THE NEW HUD
    def __init__(self):
        # This automatically creates the window, 5-char canvas, drag mechanics,
        # and starts the new HUD animation loop!
        super().__init__()

        # Add extra height for language buttons and temporary text command area
        total_h = self._strip_h + 100
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self._strip_w) // 2
        y  = sh - total_h - 40
        self.geometry(f"{self._strip_w}x{total_h}+{x}+{y}")

        # ── State (AI Logic) ──
        self.is_processing = False
        self.stop_speaking = False

        # ── Agents ──
        self.memory_agent = MemoryAgent()
        self.browser_agent = BrowserAgent()
        self.code_agent = CodeAgent()
        self.reminder_agent = ReminderAgent()
        self.chat_agent = ChatAgent()
        self.vision_agent = VisionAgent()
        self.supervisor = Supervisor(self.browser_agent)

        self.browser_agent.set_vision(self.vision_agent)
        self.chat_agent.set_vision(self.vision_agent)
        self.reminder_agent.set_speak(self.speak, self)

        # ── Build LangGraph ──
        self._build_graph()

        # ── Bottom Control Area (packed cleanly below character canvas) ──
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#0d0d0d", corner_radius=0)
        self.bottom_frame.pack(fill="x", padx=10, pady=(2, 6))

        # Row 1: Language Buttons
        self.lang_frame = ctk.CTkFrame(self.bottom_frame, fg_color="#141414", corner_radius=16)
        self.lang_frame.pack(pady=(2, 6))

        self.lang_btns = {}
        for label, code in [("ENG", "en"), ("HIN", "hi"), ("GUJ", "gu")]:
            btn = ctk.CTkButton(
                self.lang_frame, text=label, width=65, height=24,
                font=("Consolas", 11, "bold"),
                command=lambda c=code: self._set_lang(c)
            )
            btn.pack(side="left", padx=5, pady=3)
            self.lang_btns[code] = btn
        self._update_lang_buttons()

        # Row 2: Text Command Input Area
        self.input_frame = ctk.CTkFrame(self.bottom_frame, fg_color="#141414", corner_radius=10)
        self.input_frame.pack(fill="x", pady=(2, 4))

        self.cmd_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Type command here and press Enter...",
            height=30,
            font=("Consolas", 11),
            fg_color="#1e1e1e",
            text_color="#00eaff",
            border_color="#333333"
        )
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(8, 6), pady=4)
        self.cmd_entry.bind("<Return>", self._on_text_submit)

        self.send_btn = ctk.CTkButton(
            self.input_frame,
            text="Send",
            width=60,
            height=30,
            font=("Consolas", 11, "bold"),
            fg_color="#006699",
            hover_color="#0088cc",
            command=self._on_text_submit
        )
        self.send_btn.pack(side="right", padx=(0, 8), pady=4)

        self.after(500, self._start_threads)

    def _on_text_submit(self, event=None):
        text = self.cmd_entry.get().strip()
        if text:
            self.cmd_entry.delete(0, "end")
            print(f"[Typed] ({self.current_lang}) {text}")
            self._process(text)

    def _start_threads(self):
        threading.Thread(target=self._safe_listen_loop, daemon=True).start()
        print("[Optimus] Background threads started.")

    def _safe_listen_loop(self):
        time.sleep(1.0)
        try:
            self._listen_loop()
        except Exception as e:
            print(f"[Listen] Fatal error: {e}")
            import traceback
            traceback.print_exc()

    def _set_lang(self, code):
        self.set_language(code)  # Safely updates the HUD
        self.set_status(f"STANDBY_{code.upper()}")
        self._update_lang_buttons()

    def _update_lang_buttons(self):
        colors = {"en": "#00eaff", "hi": "#ff9900", "gu": "#00ff9c"}
        for code, btn in self.lang_btns.items():
            if code == self.current_lang:
                btn.configure(fg_color=colors[code], text_color="#000000")
            else:
                btn.configure(fg_color="#222222", text_color="#888888")

    def _switch_character(self, agent: str):
        """Triggers the scale-up and glow effect for the active character."""
        self.set_agent(agent)

        # ── LangGraph ──
    def _build_graph(self):
            workflow = StateGraph(AgentState)
            workflow.add_node("supervisor", self.supervisor.route)
            workflow.add_node("chat", self.chat_agent.run)
            workflow.add_node("browser", self.browser_agent.run)
            workflow.add_node("code", self.code_agent.run)
            workflow.add_node("memory", self.memory_agent.run)
            workflow.add_node("reminder", self.reminder_agent.run)
            workflow.add_node("vision", self.vision_agent.run)
            workflow.add_node("whatsapp", self._whatsapp_node)
            workflow.set_entry_point("supervisor")
            workflow.add_conditional_edges(
                "supervisor",
                lambda s: s["active_agent"],
                {"chat": "chat", "browser": "browser",
                 "code": "code", "memory": "memory",
                 "reminder": "reminder", "vision": "vision",
                 "whatsapp": "whatsapp"}
            )
            for node in ["chat", "browser", "code", "memory", "reminder", "vision", "whatsapp"]:
                workflow.add_edge(node, END)
            self.graph = workflow.compile()

    # ── Processing ──
    def _process(self, command: str):
        if self.is_processing:
            return
        self.is_processing = True

        # Set status based on likely agent
        cmd = command.lower()
        if any(w in cmd for w in ["do you remember", "recall", "remember this",
                                    "save this", "memory"]):
            self.status_text = "REMEMBERING"
        elif any(w in cmd for w in ["remind me", "reminder", "alert me"]):
            self.status_text = "REMINDER"
        elif any(w in cmd for w in ["what's on screen", "what do you see",
                                     "click on", "click the", "describe screen",
                                     "what can you see", "look at screen"]):
            self.status_text = "SEEING"
        elif any(w in cmd for w in ["open chrome", "open brave", "open youtube",
                                     "search on", "go to website"]) or self.browser_agent.is_open():
            self.status_text = "BROWSING"
        elif any(w in cmd for w in ["write code", "debug", "script", "function",
                                     "python", "javascript", "build a"]):
            self.status_text = "CODING"
        else:
            self.status_text = "PROCESSING"

        def _run():
            try:
                # Inject memory context if recall keywords present
                mem_ctx = ""
                if any(w in cmd for w in ["do you remember", "recall",
                                           "what did we", "last time"]):
                    mem_ctx = self.memory_agent.recall(command, top_k=3)

                initial_state: AgentState = {
                    "command":        command,
                    "language":       self.current_lang,
                    "active_agent":   "",
                    "response":       "",
                    "tool_name":      "",
                    "tool_args":      {},
                    "memory_context": mem_ctx,
                    "error":          "",
                }
                result = self.graph.invoke(initial_state, {"recursion_limit": 10})
                agent  = result.get("active_agent", "chat")
                reply  = result.get("response", "")

                # Direct response — supervisor answered directly (e.g. time/date)
                if not reply and result.get("tool_name") == "direct":
                    reply = result.get("tool_args", {}).get("response", "")

                # Safety — always reset if no reply
                if not reply or not reply.strip():
                    self.is_processing = False
                    self.status_text = f"STANDBY_{self.current_lang.upper()}"
                    return

                # Switch character
                try:
                    self.after(0, lambda a=agent: self._switch_character(a))
                except Exception:
                    pass

                # Speak first — don't wait for memory store
                self.speak(reply, agent=agent)

                # Auto-save to memory in background AFTER speaking starts
                from agents.memory_agent import memory_category
                threading.Thread(
                    target=self.memory_agent.store,
                    args=(command, reply, memory_category(command)),
                    daemon=True
                ).start()

            except Exception as e:
                print(f"[Orchestrator] Error: {e}")
                self.is_processing = False
                self.status_text = f"STANDBY_{self.current_lang.upper()}"

        threading.Thread(target=_run, daemon=True).start()

    def process_sync(self, command: str) -> dict:
        """Synchronously execute a command through Optimus LangGraph pipeline."""
        cmd = command.lower()
        mem_ctx = ""
        if any(w in cmd for w in ["do you remember", "recall", "what did we", "last time"]):
            mem_ctx = self.memory_agent.recall(command, top_k=3)

        initial_state: AgentState = {
            "command":        command,
            "language":       self.current_lang,
            "active_agent":   "",
            "response":       "",
            "tool_name":      "",
            "tool_args":      {},
            "memory_context": mem_ctx,
            "error":          "",
        }
        result = self.graph.invoke(initial_state, {"recursion_limit": 10})
        agent  = result.get("active_agent", "chat")
        reply  = result.get("response", "")
        if not reply and result.get("tool_name") == "direct":
            reply = result.get("tool_args", {}).get("response", "")
        
        # Save to memory
        try:
            from agents.memory_agent import memory_category
            self.memory_agent.store(command, reply or "Executed", memory_category(command))
        except Exception:
            pass
            
        return {"agent": agent, "response": reply, "state": result}

    # ── TTS ──
    def speak(self, text: str, agent: str = "chat"):
        if not text or not text.strip():
            self.is_processing = False
            self.status_text   = f"STANDBY_{self.current_lang.upper()}"
            return

        # Sanitize speech: never speak raw URLs (https://...) or markdown symbols
        def _clean_speech(raw: str) -> str:
            if not raw:
                return ""
            def _url_repl(match):
                u = match.group(0).lower()
                if "spotify.com/collection/tracks" in u:
                    return "Spotify Liked Songs"
                if "spotify.com" in u:
                    return "Spotify"
                if "youtube.com/watch" in u:
                    return "the YouTube video"
                if "youtube.com" in u:
                    return "YouTube"
                if "chat.openai.com" in u or "chatgpt.com" in u:
                    return "ChatGPT"
                if "google.com" in u:
                    return "Google"
                if "github.com" in u:
                    return "GitHub"
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(match.group(0)).netloc
                    domain = re.sub(r"^(www\.|open\.|app\.)", "", domain)
                    name = domain.split(".")[0]
                    if name:
                        return name.capitalize()
                except Exception:
                    pass
                return "the requested page"

            s = re.sub(r"https?://[^\s)\]]+", _url_repl, raw)
            s = re.sub(r"[*_`#]", "", s)
            return s.strip()

        spoken_text = _clean_speech(text)
        if not spoken_text:
            self.is_processing = False
            self.status_text   = f"STANDBY_{self.current_lang.upper()}"
            return

        self.status_text   = "SPEAKING"
        self.stop_speaking = False

        # Pick voice — non-English overrides agent voice
        if self.current_lang in LANG_VOICES:
            voice = LANG_VOICES[self.current_lang]
        else:
            voice = AGENT_VOICES.get(agent, AGENT_VOICES["chat"])

        def _tts():
            try:
                fname = f"optimus_{int(time.time())}.mp3"
                asyncio.run(edge_tts.Communicate(spoken_text, voice).save(fname))
                if os.path.exists(fname) and os.path.getsize(fname) > 0:
                    pygame.mixer.init()
                    pygame.mixer.music.load(fname)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        if self.stop_speaking:
                            pygame.mixer.music.stop()
                            break
                        time.sleep(0.1)
                    pygame.mixer.quit()
                    try: os.remove(fname)
                    except: pass
            except Exception as e:
                print(f"[TTS] Error: {e}")

            # Return to Optimus after speaking
            try:
                self.after(0, lambda: self._switch_character("chat"))
            except Exception:
                pass
            self.is_processing = False
            self.status_text   = f"STANDBY_{self.current_lang.upper()}"

        threading.Thread(target=_tts, daemon=True).start()

    # ── Wake word listener ──
    def _interrupt_listen(self):
        """Dedicated thread — only listens for stop words while speaking."""
        try:
            recognizer = sr.Recognizer()
            recognizer.energy_threshold         = 400
            recognizer.dynamic_energy_threshold = False
            recognizer.pause_threshold          = 0.4

            STOP_WORDS = ["stop", "hey stop", "stop it", "quiet", "silence",
                          "shut up", "enough", "cancel", "ruko", "bas"]

            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("[Interrupt] Stop-word listener ready.")
                while True:
                    try:
                        if self.status_text not in ("SPEAKING", "PROCESSING",
                                                    "BROWSING", "SEEING", "CODING"):
                            time.sleep(0.3)
                            continue
                        audio = recognizer.listen(source, timeout=2,
                                                  phrase_time_limit=2)
                        text  = recognizer.recognize_google(
                            audio, language="en-IN"
                        ).lower()
                        if any(w in text for w in STOP_WORDS):
                            print(f"[Interrupt] STOP: '{text}'")
                            self.stop_speaking = True
                            self.is_processing = False
                            self.status_text   = f"STANDBY_{self.current_lang.upper()}"
                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        print(f"[Interrupt] Error: {e}")
                        time.sleep(0.5)
        except Exception as e:
            print(f"[Interrupt] Failed to start: {e}")

    def _listen_loop(self):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold         = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold          = 0.8

        try:
            mic = sr.Microphone()
        except Exception as e:
            print(f"[Listen] Microphone init failed: {e}")
            return

        with mic as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
            except Exception as e:
                print(f"[Listen] Ambient noise adjust failed: {e}")
            print("[Optimus] Wake word mode — say 'Optimus' to activate.")

            active       = False
            active_until = 0
            greeted      = False

            while True:
                if self.is_processing or self.status_text == "SPEAKING":
                    time.sleep(0.2)
                    continue

                # Expire active window
                if active and time.time() > active_until:
                    active = False
                    self.status_text = f"STANDBY_{self.current_lang.upper()}"
                    print("[Optimus] Active window expired.")
                    self.speak("Going standby, sir.")

                try:
                    plimit = 8 if active else 4
                    tout   = None if not active else ACTIVE_TIMEOUT
                    audio  = recognizer.listen(source, timeout=tout,
                                               phrase_time_limit=plimit)

                    # Transcribe
                    best_text, best_lang = None, self.current_lang
                    for lang in ([self.current_lang] +
                                 [l for l in ["en","hi","gu"] if l != self.current_lang]):
                        try:
                            text = recognizer.recognize_google(
                                audio, language=LANG_CODES[lang])
                            if text:
                                best_text, best_lang = text.lower(), lang
                                break
                        except: continue

                    if not best_text:
                        continue

                    # ── Stop word — interrupt speaking/processing ──
                    STOP_WORDS = ["stop", "hey stop", "stop it", "quiet",
                                  "silence", "shut up", "enough", "cancel", "ruko", "bas"]
                    if any(w in best_text for w in STOP_WORDS) and self.status_text == "SPEAKING":
                        print(f"[Interrupt] STOP: '{best_text}'")
                        self.stop_speaking = True
                        self.is_processing = False
                        self.status_text   = f"STANDBY_{self.current_lang.upper()}"
                        continue

                    is_wake = any(w in best_text for w in WAKE_WORDS)

                    if not active:
                        if is_wake:
                            active       = True
                            active_until = time.time() + ACTIVE_TIMEOUT
                            self.status_text = "LISTENING"
                            print("[Optimus] Activated.")
                            if not greeted:
                                greeted = True
                                self.speak("Optimus online. How can I help you, sir?")
                            else:
                                self.speak("Yes sir?")
                        continue

                    # Active window
                    active_until = time.time() + ACTIVE_TIMEOUT

                    if is_wake and len(best_text.split()) <= 3:
                        self.speak("I'm listening.")
                        continue

                    if best_lang != self.current_lang:
                        self.current_lang = best_lang
                        try:
                            self.after(0, self._update_lang_buttons)
                        except Exception:
                            pass

                    print(f"[Heard] ({best_lang}) {best_text}")
                    self._process(best_text)

                except sr.WaitTimeoutError:
                    if active:
                        active = False
                        self.status_text = f"STANDBY_{self.current_lang.upper()}"
                        self.speak("Going standby.")
                except Exception as e:
                    print(f"[Listen] Error: {e}")
                    time.sleep(0.5)


    def _whatsapp_node(self, state: AgentState) -> AgentState:
        """
        WhatsApp — vision powered.
        Opens WhatsApp Desktop, finds contact, types and sends message.
        """
        command  = state["command"]
        lang_map = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}
        lang     = lang_map.get(state["language"], "English")

        # Parse contact and message using LLM
        from huggingface_hub import InferenceClient
        import re as _re, json as _json
        client = InferenceClient(token=os.getenv("HF_TOKEN"))
        try:
            parse_resp = client.chat_completion(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[{
                    "role": "user",
                    "content": f"""Extract the contact name and message from this command: "{command}"
Respond ONLY with JSON:
{{"contact": "name", "message": "message text"}}"""
                }],
                max_tokens=100, temperature=0.1
            )
            raw     = _re.sub(r"```json|```", "",
                              parse_resp.choices[0].message.content.strip()).strip()
            parsed  = _json.loads(raw)
            contact = parsed.get("contact", "")
            message = parsed.get("message", "")
        except Exception as e:
            print(f"[WhatsApp] Parse failed: {e}")
            return {**state, "response": "Couldn't understand who to message or what to say.",
                    "active_agent": "whatsapp"}

        if not contact or not message:
            return {**state, "response": "Please tell me who to message and what to say.",
                    "active_agent": "whatsapp"}

        # Open WhatsApp Desktop
        try:
            from AppOpener import open as appopen
            appopen("whatsapp", match_closest=True, output=False)
            time.sleep(3)
        except Exception as e:
            print(f"[WhatsApp] Launch failed: {e}")
            return {**state, "response": "Couldn't open WhatsApp.",
                    "active_agent": "whatsapp"}

        # Use vision to find search bar and contact
        vision = self.vision_agent
        vision.execute(f"click on the search bar or new chat icon in WhatsApp")
        time.sleep(1)

        # Type contact name
        import pyautogui
        pyautogui.typewrite(contact, interval=0.05)
        time.sleep(1.5)

        # Vision click on the contact
        vision.execute(f"click on the contact named {contact} in the search results")
        time.sleep(1)

        # Type message
        vision.execute("click on the message input box at the bottom")
        time.sleep(0.5)
        pyautogui.typewrite(message, interval=0.05)
        time.sleep(0.5)
        pyautogui.press("enter")

        response = f"Message sent to {contact}."
        self.memory_agent.store(command, response, "general")
        return {**state, "response": response, "active_agent": "whatsapp"}

    def _handle_notes(self, command: str) -> str:
        """Save or read notes."""
        import os
        notes_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "memory", "notes.txt"
        )
        cmd = command.lower()

        # Read notes
        if any(w in cmd for w in ["read", "show", "what are", "list"]):
            if os.path.exists(notes_file):
                with open(notes_file, "r", encoding="utf-8") as f:
                    notes = f.read().strip()
                return f"Your notes: {notes}" if notes else "No notes saved yet."
            return "No notes saved yet."

        # Save note — strip trigger phrases
        note_text = command
        for phrase in ["take a note", "note down", "write this down",
                       "add a note", "save a note", "jot down", "note that"]:
            note_text = note_text.lower().replace(phrase, "").strip()

        if note_text:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(notes_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {note_text}\n")
            # Also save to memory
            self.memory_agent.store(command, f"Note saved: {note_text}", "general")
            return f"Got it. Note saved: {note_text}"
        return "What would you like me to note down?"


if __name__ == "__main__":
    pygame.mixer.pre_init(44100, -16, 2, 512)
    app = OptimusApp()
    app.mainloop()