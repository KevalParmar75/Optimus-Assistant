from typing import TypedDict, Optional

class AgentState(TypedDict):
    command:        str            # raw voice command from user
    language:       str            # "en" | "hi" | "gu"
    active_agent:   str            # "chat" | "browser" | "code" | "memory" | "reminder"
    response:       str            # final spoken response
    tool_name:      str            # tool picked by supervisor
    tool_args:      dict           # args for that tool
    memory_context: str            # injected by memory agent if relevant
    error:          str            # any error message