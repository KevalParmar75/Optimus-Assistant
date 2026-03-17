"""
Reminder Agent — Ironhide
Blunt, military, no nonsense.
APScheduler + win10toast + TTS.
"""
import re, json, datetime
from state import AgentState

CHARACTER = "ironhide"
VOICE     = "en-US-GuyNeural"    # gruff, direct
MODEL     = "Qwen/Qwen2.5-72B-Instruct"


class ReminderAgent:
    def __init__(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        self.scheduler  = BackgroundScheduler(timezone="Asia/Kolkata")
        self.scheduler.start()
        self._speak_fn  = None
        self._ui_ref    = None
        self._reminders = []
        self._client    = None
        self._wire_tools()
        print("[Ironhide] Reminder agent online.")

    def set_speak(self, fn, ui_ref):
        self._speak_fn = fn
        self._ui_ref   = ui_ref

    def _get_client(self):
        if self._client is None:
            import os
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=os.getenv("HF_TOKEN"))
        return self._client

    def _wire_tools(self):
        from tools.registry import REGISTRY
        REGISTRY["set_reminder"]   = self._set_reminder_tool
        REGISTRY["list_reminders"] = self._list_reminders_tool

    def parse_time(self, command: str) -> dict | None:
        prompt = f"""Extract reminder details from: "{command}"
Current time: {datetime.datetime.now().strftime('%H:%M')}

Respond ONLY with JSON (no markdown):
{{"reminder_text": "what to remind", "remind_at": "HH:MM"}}
If no time found, set remind_at to null."""
        try:
            client = self._get_client()
            resp   = client.chat_completion(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=80, temperature=0.1
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            return json.loads(raw)
        except Exception as e:
            print(f"[Ironhide] Parse error: {e}")
            return None

    def add(self, text: str, remind_at: str) -> str:
        try:
            now     = datetime.datetime.now()
            h, m    = map(int, remind_at.split(":"))
            fire_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if fire_dt <= now:
                fire_dt += datetime.timedelta(days=1)
            job_id = f"reminder_{int(fire_dt.timestamp())}"
            self.scheduler.add_job(
                self._fire, trigger="date", run_date=fire_dt,
                args=[text], id=job_id, replace_existing=True
            )
            self._reminders.append({"id": job_id, "text": text, "time": remind_at})
            return f"Locked in. Reminding you to {text} at {remind_at}."
        except Exception as e:
            print(f"[Ironhide] Schedule error: {e}")
            return "Couldn't set that reminder."

    def _fire(self, text: str):
        print(f"[Ironhide] REMINDER: {text}")
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast("Optimus Reminder", text,
                                       duration=10, threaded=True)
        except: pass
        if self._speak_fn and self._ui_ref:
            self._ui_ref.status_text = "REMINDER"
            self._speak_fn(f"Sir, reminder: {text}", agent="reminder")

    def _set_reminder_tool(self, text: str, remind_at: str) -> str:
        return self.add(text, remind_at)

    def _list_reminders_tool(self) -> str:
        if not self._reminders:
            return "No reminders set."
        return "Reminders: " + ". ".join(
            [f"{r['time']} — {r['text']}" for r in self._reminders]
        )

    # ── LangGraph node ──
    def run(self, state: AgentState) -> AgentState:
        tool_name = state.get("tool_name", "")
        tool_args = state.get("tool_args", {})

        if tool_name == "list_reminders":
            response = self._list_reminders_tool()
        elif tool_name == "set_reminder":
            text      = tool_args.get("text", "")
            remind_at = tool_args.get("remind_at", "")
            if not remind_at:
                parsed = self.parse_time(state["command"])
                if parsed and parsed.get("remind_at"):
                    text      = parsed.get("reminder_text", text)
                    remind_at = parsed["remind_at"]
                else:
                    return {**state,
                            "response": "I need a specific time for that reminder, sir.",
                            "active_agent": "reminder"}
            response = self.add(text, remind_at)
        else:
            # Fallback — parse from raw command
            parsed = self.parse_time(state["command"])
            if parsed and parsed.get("remind_at"):
                response = self.add(parsed.get("reminder_text", state["command"]),
                                    parsed["remind_at"])
            else:
                response = "Tell me the time for that reminder."

        return {**state, "response": response, "active_agent": "reminder"}