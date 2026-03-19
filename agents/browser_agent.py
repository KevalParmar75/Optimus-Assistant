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

    def is_open(self) -> bool:
        return self._is_open

    def _open_url(self, url: str, wait: float = 2.5):
        """Open URL in existing Chrome as new tab."""
        try:
            os.startfile(url)
        except:
            webbrowser.open(url)
        self._is_open  = True
        self._last_url = url
        time.sleep(wait)

    def _search_youtube(self, query: str, autoplay: bool = False):
        """Open YouTube search. If autoplay=True, vision clicks first result."""
        q = query.strip().replace(" ", "+")
        self._open_url(f"https://www.youtube.com/results?search_query={q}", wait=3.0)
        if autoplay and self._vision:
            print("[Bumblebee] Using vision to click first video...")
            self._vision.find_and_act("click the first video in the search results")

    def _search_google(self, query: str):
        q = query.strip().replace(" ", "+")
        self._open_url(f"https://www.google.com/search?q={q}")

    def execute_plan(self, command: str) -> str:
        with self._lock:
            client = self._get_client()

            plan_prompt = f"""You are Bumblebee, a browser assistant.

Current session: {self._is_open}
Last URL: {self._last_url or 'none'}
Vision available: {self._vision is not None}

User command: "{command}"

Choose the right action:
- "youtube_play"   → search YouTube AND auto-click first video to play it
- "youtube_search" → search YouTube, show results only (no autoplay)
- "google_search"  → search Google
- "open_url"       → open a specific website URL
- "vision_act"     → use screen vision to find and click/interact with something on screen
- "scroll"         → scroll the page (value: positive=down, negative=up in pixels)
- "hotkey"         → keyboard shortcut (value: "k"=yt pause, "j"=back 10s, "l"=fwd 10s, "m"=mute, "f"=fullscreen, "ctrl+t"=new tab)
- "press"          → single key press
- "done"           → finished

RULES:
- Translate Hindi/Gujarati intent to English
- "play X", "play X on youtube" → youtube_play
- "search X on youtube" → youtube_search  
- "pause", "resume", "forward", "rewind", "fullscreen" on a video → use vision_act (VL will find the button)
- "click X", "find X on page", "scroll to X" → vision_act
- Always end with done

Return ONLY JSON array:
[{{"action": "...", "value": "...", "description": "..."}}]"""

            try:
                resp = client.chat_completion(
                    model=MODEL,
                    messages=[{"role": "user", "content": plan_prompt}],
                    max_tokens=400, temperature=0.1
                )
                raw  = resp.choices[0].message.content.strip()
                raw  = re.sub(r"```json|```", "", raw).strip()
                plan = json.loads(raw)
                print(f"[Bumblebee] Plan: {json.dumps(plan, indent=2)}")
            except Exception as e:
                print(f"[Bumblebee] Plan failed: {e}")
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

    def close_tab(self):
        import pyautogui
        pyautogui.hotkey("ctrl", "w")
        self._is_open  = False
        self._last_url = ""

    def run(self, state: AgentState) -> AgentState:
        command = state["command"].lower()
        if any(w in command for w in ["close tab", "close browser",
                                       "close chrome", "close window"]):
            self.close_tab()
            return {**state, "response": "Tab closed.", "active_agent": "browser"}
        response = self.execute_plan(state["command"])
        return {**state, "response": response, "active_agent": "browser"}