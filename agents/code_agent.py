"""
Code Agent — Wheeljack
Engineer, precise, dry humor. Code-specialized model.
Generates, runs, debugs, and injects code.
"""
import os
from state import AgentState
from tools.registry import call_tool

CHARACTER = "wheeljack"
VOICE     = "en-GB-ThomasNeural"   # technical, precise
MODEL     = "Qwen/Qwen2.5-Coder-32B-Instruct"


class CodeAgent:
    def __init__(self):
        self._client = None
        print("[Wheeljack] Code agent online.")

    def _get_client(self):
        if self._client is None:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=os.getenv("HF_TOKEN"))
        return self._client

    def _ask(self, messages: list, max_tokens: int = 1024) -> str:
        try:
            resp = self._get_client().chat_completion(
                model=MODEL, messages=messages,
                max_tokens=max_tokens, temperature=0.2
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Wheeljack] LLM error: {e}")
            return "Hit a snag. Try again."

    def generate(self, command: str, language: str = "en",
                 memory_context: str = "") -> str:
        lang_map = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}
        lang     = lang_map.get(language, "English")
        system   = """You are Wheeljack, a code-specialist Transformer. 
Generate clean, working code. Add brief comments. 
If the user speaks Hindi or Gujarati, understand their intent but always respond in English with code.
Keep explanation very short — just a line or two, then the code."""
        if memory_context:
            system += f"\n\nRelevant past context:\n{memory_context}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": command}
        ]
        return self._ask(messages)

    def debug(self, code: str, error: str) -> str:
        messages = [
            {"role": "system", "content": "You are Wheeljack. Fix this code. Show only the corrected code with a one-line explanation of what was wrong."},
            {"role": "user",   "content": f"Code:\n{code}\n\nError:\n{error}"}
        ]
        return self._ask(messages)

    def explain(self, code: str) -> str:
        messages = [
            {"role": "system", "content": "You are Wheeljack. Explain this code briefly — 2-4 sentences max. No fluff."},
            {"role": "user",   "content": code}
        ]
        return self._ask(messages, max_tokens=200)

    # ── LangGraph node ──
    def run(self, state: AgentState) -> AgentState:
        command  = state["command"]
        cmd_low  = command.lower()
        mem_ctx  = state.get("memory_context", "")

        # Decide what kind of code task this is
        if any(w in cmd_low for w in ["run", "execute", "test"]):
            # Generate then run
            code     = self.generate(command, state["language"], mem_ctx)
            # Extract just the code block if wrapped in markdown
            import re
            match = re.search(r"```(?:\w+)?\n(.*?)```", code, re.DOTALL)
            raw_code = match.group(1) if match else code
            result   = call_tool("run_code", {"code": raw_code})
            response = f"Ran it. Result: {result}"

        elif any(w in cmd_low for w in ["inject", "type", "paste", "insert into"]):
            # Generate and inject into editor
            code  = self.generate(command, state["language"], mem_ctx)
            import re
            match = re.search(r"```(?:\w+)?\n(.*?)```", code, re.DOTALL)
            raw_code = match.group(1) if match else code
            call_tool("inject_to_editor", {"code": raw_code})
            response = "Injected into your editor. Check it out."

        elif any(w in cmd_low for w in ["explain", "what does", "understand"]):
            response = self.explain(command)

        else:
            # Default — just generate
            response = self.generate(command, state["language"], mem_ctx)

        return {**state, "response": response, "active_agent": "code"}