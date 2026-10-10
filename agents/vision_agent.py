"""
Vision Agent -- Optimus's Eyes
Uses Qwen2-VL to see the screen and interact with it.
Screenshots are in-memory only -- never written to disk.

Laya Integration:
- Laya triage classifies commands BEFORE expensive VL API calls
- Direct actions (scroll, key press, hotkey) bypass VL entirely (~0ms)
- Only visually-grounded actions (click, find, describe) use VL API
"""
import os, base64, io, time, json, re
import pyautogui
from state import AgentState

CHARACTER  = "vision"
# ── Use an actual vision-language model ──
VL_MODEL   = "google/gemma-4-31B-it"

pyautogui.FAILSAFE = False

SCREEN_W = 1920
SCREEN_H = 1080


class VisionAgent:
    def __init__(self):
        self._client = None
        self._laya   = None
        print("[Vision] Vision agent ready.")

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=os.getenv("HF_TOKEN"))
        return self._client

    def _get_laya(self):
        if self._laya is None:
            from tools.laya_engine import LayaEngine
            self._laya = LayaEngine.get_instance()
        return self._laya

    def capture(self) -> str:
        """
        Take screenshot of PRIMARY monitor -> resize to 1280x720
        -> return as base64 PNG string.

        mss.monitors[0] = all monitors combined (wrong on multi-monitor)
        mss.monitors[1] = primary monitor (correct)
        """
        import mss
        from PIL import Image
        try:
            with mss.mss() as sct:
                # monitors[1] = primary screen only
                monitor = sct.monitors[1]
                raw     = sct.grab(monitor)
                img     = Image.frombytes("RGB", raw.size, raw.rgb)

            # Resize to 1280x720 -- saves API tokens, VL reads fine at this res
            img_resized = img.resize((1280, 720), Image.LANCZOS)

            buf = io.BytesIO()
            img_resized.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return b64
        except Exception as e:
            print(f"[Vision] Capture failed: {e}")
            return ""

    def _scale_coords(self, x: int, y: int) -> tuple[int, int]:
        """
        Scale VL coords (based on 1280x720 image) back to
        actual 1920x1080 screen coordinates.

        scale_x = 1920 / 1280 = 1.5
        scale_y = 1080 / 720  = 1.5
        """
        rx = int(x * (SCREEN_W / 1280))
        ry = int(y * (SCREEN_H / 720))
        # Clamp to screen bounds
        rx = max(0, min(rx, SCREEN_W - 1))
        ry = max(0, min(ry, SCREEN_H - 1))
        return rx, ry

    # ================================================================
    # LAYA TRIAGE: Classify whether VL is actually needed
    # ================================================================

    def _triage_command(self, command: str) -> dict | None:
        """
        Use Laya to classify if this command can be executed directly
        without an expensive VL API call.

        Returns:
          - None if VL is needed (visual grounding required)
          - {"action": "...", "value": "..."} if direct execution is possible
        """
        cmd = command.lower().strip()

        # ── Fast regex shortcuts (0ms, no model) ──
        # Scroll commands
        if re.search(r'\bscroll\s*(down|up)\b', cmd):
            direction = "down" if "down" in cmd else "up"
            m = re.search(r'(\d+)', cmd)
            amount = int(m.group(1)) if m else 3
            return {"action": f"scroll_{direction}", "value": str(amount)}

        # Key presses
        KEY_MAP = {
            "press escape": "escape", "press enter": "enter",
            "press space": "space", "press tab": "tab",
            "press backspace": "backspace", "press delete": "delete",
            "hit escape": "escape", "hit enter": "enter",
            "hit space": "space",
        }
        for phrase, key in KEY_MAP.items():
            if phrase in cmd:
                return {"action": "key", "value": key}

        # Hotkeys
        HOTKEY_MAP = {
            "copy": "ctrl+c", "paste": "ctrl+v", "undo": "ctrl+z",
            "redo": "ctrl+y", "select all": "ctrl+a", "save": "ctrl+s",
            "close tab": "ctrl+w", "new tab": "ctrl+t",
            "switch tab": "ctrl+tab", "fullscreen": "f11",
            "refresh": "f5", "alt tab": "alt+tab",
            "minimize": "win+d", "screenshot": "win+shift+s",
        }
        for phrase, hotkey in HOTKEY_MAP.items():
            if phrase in cmd:
                return {"action": "hotkey", "value": hotkey}

        # ── Laya classification for ambiguous commands ──
        try:
            needs = self._get_laya().classify_vision_action(cmd)
            if needs == "keyboard_or_scroll":
                print(f"[Vision] Laya triage: no VL needed for '{cmd[:40]}'")
                return None  # Fall through to VL if specific mapping unknown
            print(f"[Vision] Laya triage: VL needed for '{cmd[:40]}'")
        except Exception as e:
            print(f"[Vision] Laya triage error: {e}")

        return None

    def _execute_direct(self, action_info: dict) -> str:
        """Execute a direct keyboard/scroll action without VL."""
        action = action_info["action"]
        value  = action_info.get("value", "")

        try:
            if action == "scroll_down":
                amount = int(value) if value.isdigit() else 3
                pyautogui.scroll(-amount)
                return "Scrolled down."

            elif action == "scroll_up":
                amount = int(value) if value.isdigit() else 3
                pyautogui.scroll(amount)
                return "Scrolled up."

            elif action == "key":
                pyautogui.press(value)
                time.sleep(0.2)
                return f"Pressed {value}."

            elif action == "hotkey":
                keys = value.split("+")
                pyautogui.hotkey(*keys)
                time.sleep(0.3)
                return f"Executed {value}."

        except Exception as e:
            print(f"[Vision] Direct action failed: {e}")
            return f"Couldn't execute: {e}"

        return "Done."

    # ================================================================

    def ask_vl(self, b64_image: str, prompt: str) -> str:
        """Send screenshot + prompt to VL model, return raw response."""
        try:
            resp = self._get_client().chat_completion(
                model=VL_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }],
                max_tokens=400,
                temperature=0.1
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Vision] VL API failed: {e}")
            return ""

    def describe(self) -> str:
        """Describe what's currently on screen."""
        b64 = self.capture()
        if not b64:
            return "Couldn't capture the screen."
        prompt = (
            "Describe what you see on this screen in 2-3 sentences. "
            "Be specific -- mention the app, website, content visible, "
            "and any important UI elements. Keep it concise and natural."
        )
        result = self.ask_vl(b64, prompt)
        return result if result else "I can see your screen but couldn't describe it."

    def find_and_act(self, command: str) -> str:
        """
        Screenshot -> VL finds element -> pyautogui acts on it.
        Returns spoken confirmation.

        Now with Laya triage: direct actions bypass VL entirely.
        """
        # ── Laya triage: can we skip the VL call? ──
        direct = self._triage_command(command)
        if direct:
            print(f"[Vision] Direct action (no VL): {direct}")
            return self._execute_direct(direct)

        # ── VL path: need visual grounding ──
        b64 = self.capture()
        if not b64:
            return "Couldn't capture the screen, sir."

        prompt = f"""You are controlling a Windows computer at 1920x1080.
The screenshot has been resized to 1280x720 for you to analyze.
Coordinates you return will be scaled back to 1920x1080 automatically.

User wants to: "{command}"

Find the exact element and respond ONLY with valid JSON (no markdown, no explanation):
{{
  "action": "click" | "double_click" | "right_click" | "type" | "scroll_up" | "scroll_down" | "key" | "describe",
  "x": <integer 0-1280, center x of element in the 1280x720 image>,
  "y": <integer 0-720, center y of element in the 1280x720 image>,
  "value": "<text to type, key name like enter/escape/space, or scroll count>",
  "description": "<one sentence: what you found and what you will do>"
}}

Rules:
- x and y must be the CENTER of the button/icon/link you want to click
- For scroll actions: x and y are 0, value is number of scroll steps
- For key press: x and y are 0, value is the key name
- If element not found: action = "describe", explain what you see instead
- Be precise -- wrong coordinates mean clicking empty space"""

        raw = self.ask_vl(b64, prompt)
        if not raw:
            return "I looked at the screen but couldn't figure out what to do."

        print(f"[Vision] Raw VL response: {raw[:200]}")

        try:
            raw_clean = re.sub(r"```json|```", "", raw).strip()
            result    = json.loads(raw_clean)
        except Exception:
            # VL returned plain text -- just speak it
            print(f"[Vision] VL response not JSON, treating as description")
            return raw[:300]

        action = result.get("action", "describe")
        x      = int(result.get("x", 0))
        y      = int(result.get("y", 0))
        value  = str(result.get("value", ""))
        desc   = result.get("description", "Done.")

        print(f"[Vision] Action={action} at VL({x},{y}) -> "
              f"screen{self._scale_coords(x, y)} value='{value}'")

        try:
            if action in ("click", "double_click", "right_click"):
                rx, ry = self._scale_coords(x, y)
                print(f"[Vision] Clicking screen coords ({rx}, {ry})")
                # Move mouse first so user can see where it's going
                pyautogui.moveTo(rx, ry, duration=0.3)
                time.sleep(0.1)
                if action == "click":
                    pyautogui.click(rx, ry)
                elif action == "double_click":
                    pyautogui.doubleClick(rx, ry)
                elif action == "right_click":
                    pyautogui.rightClick(rx, ry)
                time.sleep(0.6)

            elif action == "type":
                if x and y:
                    rx, ry = self._scale_coords(x, y)
                    pyautogui.click(rx, ry)
                    time.sleep(0.3)
                # Use pyperclip for non-ASCII text (Hindi/Gujarati)
                try:
                    import pyperclip
                    pyperclip.copy(value)
                    pyautogui.hotkey("ctrl", "v")
                except Exception:
                    pyautogui.typewrite(value, interval=0.05)

            elif action == "scroll_down":
                amount = int(value) if value.isdigit() else 3
                pyautogui.scroll(-amount)

            elif action == "scroll_up":
                amount = int(value) if value.isdigit() else 3
                pyautogui.scroll(amount)

            elif action == "key":
                pyautogui.press(value)
                time.sleep(0.3)

            elif action == "describe":
                return desc

        except Exception as e:
            print(f"[Vision] Action failed: {e}")
            return f"I found it but couldn't interact: {e}"

        return desc

    def execute(self, command: str) -> str:
        """Public shortcut used by browser_agent and whatsapp_node."""
        return self.find_and_act(command)

    def run(self, state: AgentState) -> AgentState:
        command = state["command"].lower()

        if any(w in command for w in [
            "what's on screen", "what is on screen",
            "what do you see", "describe screen",
            "what's open", "what's on my screen",
            "what can you see", "look at screen"
        ]):
            response = self.describe()
        else:
            response = self.find_and_act(state["command"])

        return {**state, "response": response, "active_agent": "vision"}