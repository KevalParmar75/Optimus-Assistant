"""
ScreenContext — lightweight log of what's currently open.
No screenshots, no overhead. Updated whenever an app is opened/closed.
Injected into supervisor so Optimus always knows current app state.
"""
import time
from typing import Optional


class ScreenContext:
    """
    Singleton that tracks what's currently open on screen.
    Any agent can update it. Supervisor reads it before routing.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._open_apps: list[str]      = []
        self._active_app: Optional[str] = None
        self._browser_open: bool        = False
        self._browser_url: str          = ""
        self._last_action: str          = ""
        self._last_updated: float       = time.time()

    # ── Writers (called by agents/tools when something changes) ──

    def app_opened(self, app_name: str):
        app = app_name.lower().strip()
        if app not in self._open_apps:
            self._open_apps.append(app)
        self._active_app  = app
        self._last_action = f"opened {app}"
        self._last_updated = time.time()
        if any(b in app for b in ["brave", "chrome", "edge", "firefox", "browser"]):
            self._browser_open = True
        print(f"[Context] App opened: {app} (browser_open={self._browser_open})")

    def app_closed(self, app_name: str):
        app = app_name.lower().strip()
        if app in self._open_apps:
            self._open_apps.remove(app)
        if self._active_app == app:
            self._active_app = self._open_apps[-1] if self._open_apps else None
        if any(b in app for b in ["brave", "chrome", "edge", "firefox", "browser"]):
            self._browser_open = False
        self._last_action  = f"closed {app}"
        self._last_updated = time.time()
        print(f"[Context] App closed: {app}")

    def browser_opened(self, url: str = ""):
        self._browser_open = True
        self._browser_url  = url
        self._active_app   = "browser"
        if "browser" not in self._open_apps:
            self._open_apps.append("browser")
        self._last_action  = f"opened browser{' at ' + url if url else ''}"
        self._last_updated = time.time()
        print(f"[Context] Browser opened: {url}")

    def browser_closed(self):
        self._browser_open = False
        self._browser_url  = ""
        if "browser" in self._open_apps:
            self._open_apps.remove("browser")
        if self._active_app == "browser":
            self._active_app = self._open_apps[-1] if self._open_apps else None
        self._last_action  = "closed browser"
        self._last_updated = time.time()
        print(f"[Context] Browser closed")

    def set_active(self, app_name: str):
        """Mark an app as currently in focus."""
        self._active_app = app_name.lower().strip()
        self._last_updated = time.time()

    # ── Reader (called by supervisor) ──

    def summary(self) -> str:
        """
        Returns a short natural-language summary injected into the
        supervisor prompt so the LLM knows what's currently open.
        """
        parts = []
        if self._active_app:
            parts.append(f"Currently active: {self._active_app}")
        if self._open_apps:
            apps = [a for a in self._open_apps if a != self._active_app]
            if apps:
                parts.append(f"Also open: {', '.join(apps)}")
        if self._browser_open and self._browser_url:
            parts.append(f"Browser showing: {self._browser_url}")
        if self._last_action:
            parts.append(f"Last action: {self._last_action}")
        return " | ".join(parts) if parts else "Nothing specific open."

    def is_open(self, app_name: str) -> bool:
        return app_name.lower() in self._open_apps

    @property
    def active_app(self) -> Optional[str]:
        return self._active_app

    @property
    def browser_open(self) -> bool:
        return self._browser_open

    @property
    def open_apps(self) -> list[str]:
        return list(self._open_apps)


# Module-level singleton — import this anywhere
screen_context = ScreenContext()