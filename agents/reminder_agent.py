"""
Reminder Agent -- Ironhide
Blunt, military, no nonsense.
APScheduler + win10toast + TTS.

Laya Integration:
- Time parsing is now 100% local (regex patterns + Laya structured decide)
- Zero LLM API calls needed for any reminder operation
"""
import re, json, datetime
from state import AgentState

CHARACTER = "ironhide"
VOICE     = "en-US-GuyNeural"    # gruff, direct


class ReminderAgent:
    def __init__(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        self.scheduler  = BackgroundScheduler(timezone="Asia/Kolkata")
        self.scheduler.start()
        self._speak_fn  = None
        self._ui_ref    = None
        self._reminders = []
        self._laya      = None
        self._wire_tools()
        print("[Ironhide] Reminder agent online.")

    def set_speak(self, fn, ui_ref):
        self._speak_fn = fn
        self._ui_ref   = ui_ref

    def _get_laya(self):
        if self._laya is None:
            from tools.laya_engine import LayaEngine
            self._laya = LayaEngine.get_instance()
        return self._laya

    def _wire_tools(self):
        from tools.registry import REGISTRY
        REGISTRY["set_reminder"]   = self._set_reminder_tool
        REGISTRY["list_reminders"] = self._list_reminders_tool

    # ================================================================
    # LOCAL TIME PARSING (regex first, Laya fallback -- zero LLM API)
    # ================================================================

    def parse_time(self, command: str) -> dict | None:
        """
        Extract reminder time + text from natural language, fully local.

        Strategy:
          1. Regex patterns for common English time expressions
          2. Laya structured decide() as fallback
          3. Never calls a remote LLM API
        """
        cmd = command.lower().strip()
        now = datetime.datetime.now()

        # ── Pattern 1: "in X minutes/hours" ──
        m = re.search(r'in\s+(\d+)\s*(min(?:ute)?s?|hour?s?|hr?s?)', cmd)
        if m:
            amount = int(m.group(1))
            unit   = m.group(2)
            if unit.startswith('h'):
                fire = now + datetime.timedelta(hours=amount)
            else:
                fire = now + datetime.timedelta(minutes=amount)
            text = self._extract_reminder_text(cmd)
            return {"reminder_text": text, "remind_at": fire.strftime("%H:%M")}

        # ── Pattern 2: "in half an hour" / "in an hour" ──
        if re.search(r'in\s+(half\s+an?\s+hour|30\s+min)', cmd):
            fire = now + datetime.timedelta(minutes=30)
            text = self._extract_reminder_text(cmd)
            return {"reminder_text": text, "remind_at": fire.strftime("%H:%M")}
        if re.search(r'in\s+an?\s+hour', cmd):
            fire = now + datetime.timedelta(hours=1)
            text = self._extract_reminder_text(cmd)
            return {"reminder_text": text, "remind_at": fire.strftime("%H:%M")}

        # ── Pattern 3: "at HH:MM" or "at H:MM" ──
        m = re.search(r'at\s+(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?', cmd)
        if m:
            h, mi = int(m.group(1)), int(m.group(2))
            ampm = (m.group(3) or "").replace(".", "")
            if ampm == "pm" and h < 12:
                h += 12
            elif ampm == "am" and h == 12:
                h = 0
            text = self._extract_reminder_text(cmd)
            return {"reminder_text": text, "remind_at": f"{h:02d}:{mi:02d}"}

        # ── Pattern 4: "at 3 pm" / "at 10 am" (no colon) ──
        m = re.search(r'at\s+(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)', cmd)
        if m:
            h = int(m.group(1))
            ampm = m.group(2).replace(".", "")
            if ampm == "pm" and h < 12:
                h += 12
            elif ampm == "am" and h == 12:
                h = 0
            text = self._extract_reminder_text(cmd)
            return {"reminder_text": text, "remind_at": f"{h:02d}:00"}

        # ── Pattern 5: bare "HH:MM" anywhere ──
        m = re.search(r'(\d{1,2}):(\d{2})', cmd)
        if m:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                text = self._extract_reminder_text(cmd)
                return {"reminder_text": text, "remind_at": f"{h:02d}:{mi:02d}"}

        # ── Pattern 6: "after X minutes" ──
        m = re.search(r'after\s+(\d+)\s*(min(?:ute)?s?|hour?s?|hr?s?)', cmd)
        if m:
            amount = int(m.group(1))
            unit   = m.group(2)
            if unit.startswith('h'):
                fire = now + datetime.timedelta(hours=amount)
            else:
                fire = now + datetime.timedelta(minutes=amount)
            text = self._extract_reminder_text(cmd)
            return {"reminder_text": text, "remind_at": fire.strftime("%H:%M")}

        # ── Laya fallback: structured question extraction ──
        try:
            laya = self._get_laya()
            questions = {
                "has_time": {
                    "instructions": "Does this reminder request contain a specific time?",
                    "type": "choice",
                    "criteria": ["yes", "no"]
                },
                "time_type": {
                    "instructions": "What type of time specification is used?",
                    "type": "choice",
                    "criteria": ["relative_minutes", "relative_hours", "absolute_clock", "none"]
                }
            }
            res = laya.agent.decide(cmd, questions=questions)
            has_time = res.get("has_time", {}).get("choice", "no")
            if has_time == "no":
                print("[Ironhide] Laya says no time found in command")
                return None
            print(f"[Ironhide] Laya detected time but regex missed it: {res}")
        except Exception as e:
            print(f"[Ironhide] Laya fallback failed: {e}")

        return None

    def _extract_reminder_text(self, cmd: str) -> str:
        """Strip time phrases and common prefixes to get the reminder content."""
        text = cmd
        # Remove common prefixes
        for prefix in ["remind me to ", "remind me ", "set a reminder to ",
                       "set reminder to ", "set a reminder for ",
                       "set reminder for ", "reminder to ", "reminder for ",
                       "alert me to ", "notify me to ",
                       "don't let me forget to ", "don't forget to "]:
            if text.startswith(prefix):
                text = text[len(prefix):]
                break

        # Remove time expressions
        text = re.sub(r'\s*(?:at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)', '', text)
        text = re.sub(r'\s*(?:in\s+(?:\d+\s*(?:min(?:ute)?s?|hour?s?|hr?s?)|half\s+an?\s+hour|an?\s+hour))', '', text)
        text = re.sub(r'\s*(?:after\s+\d+\s*(?:min(?:ute)?s?|hour?s?|hr?s?))', '', text)
        text = text.strip(" .,;")
        return text if text else cmd

    # ================================================================

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
            [f"{r['time']} -- {r['text']}" for r in self._reminders]
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
            # Fallback -- parse from raw command
            parsed = self.parse_time(state["command"])
            if parsed and parsed.get("remind_at"):
                response = self.add(parsed.get("reminder_text", state["command"]),
                                    parsed["remind_at"])
            else:
                response = "Tell me the time for that reminder."

        return {**state, "response": response, "active_agent": "reminder"}