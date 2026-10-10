"""
Laya Local Engine — Non-Autoregressive Decision Engine
Provides fast (<50ms) local classification for Supervisor routing & Browser agent planning.
"""
import threading, re

class LayaEngine:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        print("[LayaEngine] Initializing local Laya decision model...")
        import os, torch, laya
        # Maximize CPU core utilization for faster inference
        cpu_threads = os.cpu_count() or 8
        torch.set_num_threads(cpu_threads)
        print(f"[LayaEngine] PyTorch CPU threads configured: {cpu_threads}")
        self.agent = laya.load()
        print("[LayaEngine] Local Laya engine ready.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = LayaEngine()
        return cls._instance

    def choose_browser_action(self, command: str) -> str:
        """
        Classifies browser command into action type using Laya choice primitive.
        Returns: 'youtube_play', 'youtube_search', 'google_search', 'open_url', 'vision_act', 'scroll', 'hotkey', or 'press'
        """
        try:
            questions = {
                "action": {
                    "instructions": "Choose the best browser action for the user request.",
                    "type": "choice",
                    "criteria": [
                        "youtube_play",
                        "youtube_search",
                        "google_search",
                        "open_url",
                        "vision_act",
                        "scroll",
                        "hotkey",
                        "press"
                    ]
                }
            }
            res = self.agent.decide(command, questions=questions)
            action = res.get("action", {}).get("choice", "google_search")
            print(f"[LayaEngine] Browser Action decision: {action}")
            return action
        except Exception as e:
            print(f"[LayaEngine] Decision error: {e}")
            return "google_search"

    def route_supervisor_agent(self, command: str, active_app: str = "") -> str:
        """
        Routes user intent to the appropriate Optimus sub-agent.
        Returns: 'chat', 'browser', 'vision', 'code', 'memory', 'reminder', 'whatsapp'
        """
        try:
            questions = {
                "agent": {
                    "instructions": "Determine which specialized AI agent should handle this request.",
                    "type": "choice",
                    "criteria": [
                        "chat",
                        "browser",
                        "vision",
                        "code",
                        "memory",
                        "reminder",
                        "whatsapp"
                    ]
                }
            }
            context = f"Active window: {active_app}. User command: '{command}'"
            res = self.agent.decide(context, questions=questions)
            agent_choice = res.get("agent", {}).get("choice", "chat")
            print(f"[LayaEngine] Supervisor Route decision: {agent_choice}")
            return agent_choice
        except Exception as e:
            print(f"[LayaEngine] Supervisor decision error: {e}")
            return "chat"

    def classify_chat_action(self, command: str) -> str:
        """
        Classifies incoming chat command into specific action intent:
        'conversation', 'web_search', 'open_app', 'write_note', 'media_control', 'play_media'
        """
        try:
            questions = {
                "action": {
                    "instructions": (
                        "Classify the user intent: general conversation, searching web for info, "
                        "opening/launching an application, writing text into a notepad/editor, "
                        "adjusting or toggling media playback (pause/volume/next), or playing a song/video."
                    ),
                    "type": "choice",
                    "criteria": [
                        "conversation",
                        "web_search",
                        "open_app",
                        "write_note",
                        "media_control",
                        "play_media"
                    ]
                }
            }
            res = self.agent.decide(command, questions=questions)
            action = res.get("action", {}).get("choice", "conversation")
            print(f"[LayaEngine] Chat Action decision: {action}")
            return action
        except Exception as e:
            print(f"[LayaEngine] Chat action decision error: {e}")
            return "conversation"

    def classify_vision_action(self, command: str) -> str:
        """
        Determines whether a command requires visual grounding (Qwen2-VL)
        or can be satisfied via local keyboard/scroll shortcut.
        Returns: 'needs_vision' or 'keyboard_or_scroll'
        """
        try:
            questions = {
                "needs_vision": {
                    "instructions": (
                        "Does this command require looking at the screen to find "
                        "a visual element (button, text, icon, link), or can it "
                        "be executed with a keyboard shortcut or scroll?"
                    ),
                    "type": "choice",
                    "criteria": ["needs_vision", "keyboard_or_scroll"]
                }
            }
            res = self.agent.decide(command, questions=questions)
            choice = res.get("needs_vision", {}).get("choice", "needs_vision")
            print(f"[LayaEngine] Vision triage decision: {choice}")
            return choice
        except Exception as e:
            print(f"[LayaEngine] Vision triage error: {e}")
            return "needs_vision"

