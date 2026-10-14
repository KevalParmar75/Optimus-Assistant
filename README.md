# 🤖 Optimus — Transformers Universe AI Assistant
> *"Autobots, roll out."*

A modular, voice and text-controlled multi-agent desktop assistant built around a Transformers universe theme. Each capability is powered by a dedicated Transformer character with real-time UI status tracking, pixel art avatars, and specialized intelligence.

---

## ⚡ The Laya Engine & Live Benchmark Metrics

Optimus integrates **Laya** (`convaiinnovations/laya`), a state-of-the-art non-autoregressive decision model running **100% locally on-device**. By utilizing ModernBERT architecture for intent routing and tactical action planning, Optimus eliminates slow cloud LLM roundtrips for all operational decisions.

External LLMs (via high-speed **Groq Cloud API**) are called **only** when deep, open-ended conversational generation is strictly needed.

### 📊 Measured Benchmark Results (Verified on Windows / Python 3.12)

The metrics below are from actual end-to-end runs recorded in [`benchmark_report.md`](benchmark_report.md) (Executed: `2026-10-13 19:40:16`):

#### 1. Local Laya Decision Engine Cold vs. Warm Latency
- **Cold Start (Model Weights Load to RAM):** `33,207.14 ms` (~33.2s, occurs only once on first boot)
- **Warm Decision Inference:** `495.13 ms` (sub-second local classification with 0 network calls)
- **Sample Test Decision:** `browser`

#### 2. Direct Groq API Speed & Throughput (`qwen/qwen3.8-27b`)
| Task | Latency (ms) | Tokens Generated | Throughput (Tokens/sec) | Sample Output |
| :--- | :--- | :--- | :--- | :--- |
| **Knowledge & Fact Q&A** | `243.48 ms` | 62 tokens | **~254.6 tok/s** | *"Quantum computers leverage the principles of superposition and entanglement..."* |
| **Python Code Generation** | `323.89 ms` | 100 tokens | **~308.7 tok/s** | `def reverse_string(s: str) -> str: ...` |
| **Multimodal Screen Vision** | `324.66 ms` | 7 tokens | **~21.6 tok/s** | *"Black screen with white text, minimalistic design..."* |
| **Short Conversational** | `549.66 ms` | 14 tokens | **~25.5 tok/s** | *"I am Qwen, here to help you with any questions..."* |

#### 3. YouTube Direct Play Resolution Speed (`"play Jogi on youtube"`)
| Pipeline Step | Time Taken (ms) | Output / Details |
| :--- | :--- | :--- |
| **1. Laya Action Triage** | `478.49 ms` | Classified action as `youtube_play` |
| **2. Song Parameter Extraction** | `0.009 ms` | Extracted query: `Jogi` via zero-latency regex |
| **3. Direct Video URL Resolution** | `1,061.56 ms` | Direct `urllib` fetch + regex extraction of `watch?v=HexFqifusOk` |
| **⚡ TOTAL TIME BEFORE BROWSER LAUNCH** | **`1,540.06 ms`** | **Direct playback URL resolved in ~1.54s (vs 6–10s with vision loops)** |

#### 4. Full End-to-End Orchestrator Loop Turnaround
*Measured from user input ➔ Laya Supervisor routing ➔ Agent execution ➔ State update ➔ Asynchronous memory commit:*

| Workflow Category | Test Command | Routed Agent | Laya Routing (ms) | Execution (ms) | Memory Commit (ms) | **Full Loop (ms)** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Browser Navigation** | *"open github.com"* | `browser` (Bumblebee) | `743.46 ms` | `0.01 ms` | `0.02 ms` | **`743.5 ms`** |
| **Reminder Scheduling** | *"remind me to join team meeting at 5pm"* | `reminder` (Ironhide) | `713.17 ms` | `151.2 ms` | `0.02 ms` | **`864.4 ms`** |
| **Chat / Q&A** | *"What is the speed of light in vacuum?"* | `code` (Wheeljack)* | `451.21 ms` | `300.64 ms` | `228.88 ms` | **`980.73 ms`** |
| **Live News RSS** | *"give me brief current indian news only headlines"* | `browser` (Bumblebee)* | `703.53 ms` | `414.17 ms` | `0.02 ms` | **`1,117.73 ms`** |
| **Code Synthesis** | *"write a python function to check palindrome"* | `code` (Wheeljack) | `631.09 ms` | `561.37 ms` | `0.01 ms` | **`1,192.47 ms`** |

> *\*Note on Routing:* In isolated benchmark testing of raw model classification, Laya routed knowledge Q&A to `code` and news queries to `browser`. In the full application, Supervisor Tier-1 shortcuts and question guards override these to Optimus (`chat`) before agent dispatch.

---

## 🛡️ Failure Modes & Edge Case Recovery

Optimus includes automatic recovery and graceful degradation across all failure modes:

| Failure Scenario | Input Command | Recovery Mechanism | Recovery Latency | Status & Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Gibberish / Malformed Input** | *"zxcvbnmasdfghjkl qwertyuiop 992834"* | Laya routed to 'code', AI answered gracefully | `617.42 ms` | **PASSED (Safe conversational response)** |
| **Non-Existent App Launch** | *"open HolographicTeleporterPro2099"* | Strict AppOpener & system registry fallback | `12.51 ms` | **PASSED (Non-crashing user notification)** |
| **Empty/Malformed YouTube Query** | *"play '          '"* | Regex guard + safe fallback to YouTube default | `804.6 ms` | **PASSED (Clean URL fallback)** |
| **Simulated Primary LLM Outage** | *"User conversational prompt during primary failure"* | Automatic failover to 'openai/gpt-oss-120b' | `605.76 ms` | **PASSED (Seamless failover)** |
| **Malformed / Unparseable Reminder Time** | *"remind me to do something at someday or maybe never"* | Regex + Laya returns None, prompts user politely | `656.81 ms` | **PASSED (Safe None return, no crash)** |

---

## 🌟 The Autobot Team

| Character | Role | Engine / Model | Specialty | Color |
|---|---|---|---|---|
| **Optimus Prime** | Orchestrator & Chat | Local Laya + Groq Qwen 27B | High-level orchestration, dialog, news, app control | 🔵 Cyan |
| **Bumblebee** | Browser Agent | Laya Action Triage + Chrome/Brave | Direct tab manipulation, YouTube, Spotify, web continuity | 🟡 Yellow |
| **Wheeljack** | Code Agent | Groq `qwen/qwen3.8-27b` | Code synthesis, refactoring, debugging, execution | 🟢 Green |
| **Ironhide** | Reminder Agent | Local Regex + Laya Fallback | Fast scheduling, alerts, Windows toast notifications | 🔴 Red |
| **Perceptor** | Memory Agent | ChromaDB + LlamaIndex | Semantic conversation recall, user preferences, vector memory | 🔴 Dark Red |
| **Vision** | Visual Grounding | Groq Multimodal Vision / Local ScreenContext | Screen understanding, UI coordinate scaling, element clicking | 🟡 Gold |

---

## 🚀 Core Features & Capabilities

### 🎙️ Dual-Input Control (Voice & Live Keyboard HUD)
- **Wake Word Listening** — say *"Optimus"* to activate (hands-free active session).
- **HUD Live Text Entry** — type commands directly into the bottom HUD input bar for silent operation.
- **Auto Language Detection** — handles English, Hindi, and Gujarati with automatic language matching.
- **Voice Interruption** — say *"stop"* to cut speech mid-sentence.
- **Friendly Spoken Feedback** — automatically sanitizes raw URLs into human-friendly names (e.g. *"Opened Spotify"* instead of reading raw HTTPS strings).

### 🌐 Smart Browser Automation (Bumblebee)
- **Window & Tab Continuity** — detects existing active Chrome/Brave tabs via `ScreenContext` and focuses them instead of opening duplicates.
- **In-Page Typing** — types prompts directly into active web apps like ChatGPT or search bars.
- **Quick Tab Hotkeys** — handles *"new tab"*, *"close tab"*, *"switch to next tab"*, and *"reopen tab"* natively.
- **Instant YouTube & Music Play** — *"Play Jogi on YouTube"* directly resolves and plays the top track in `1,540.06 ms`.

### 📰 Real-Time News Briefing
- **Instant Google News RSS Engine** — pulls top headlines in `~414 ms` with zero LLM lag and no rate limits.
- **Regional & Global Support** — supports localized editions (e.g., *"give me brief current indian news only headlines"*).

### 👁️ Screen Vision & Spatial Grounding
- **RAM-Only Screen Capture** — captures high-resolution screenshots without writing to disk.
- **Coordinate Scaling** — accurately translates bounding box percentages into physical screen pixel clicks.
- **Sub-Second Groq Multimodal Vision** — screen analysis completes in `324.66 ms`.

### 📱 System & App Control
- **Strict App Launching** — leverages indexed system applications (VS Code, Spotify, Word, Calculator, etc.) with instant non-crashing validation (`12.51 ms`).
- **Word Document Automation** — direct COM automation for opening and interacting with Microsoft Word.

### 🧠 Persistent Memory & Recall (Perceptor)
- **Zero-Lag Background Commits** — saves conversational turns asynchronously in the background.
- **Semantic Vector Storage** — ChromaDB + sentence-transformers for contextual recall (`228.88 ms` commit time).
- **Low Memory Mode** — support for `OPTIMUS_LOW_MEMORY=true` with lazy model loading.

---

## 🏗️ Project Architecture

```
E:\optimus\
  ├── main.py                 ← Main orchestrator, Supervisor, UI event loop, LangGraph
  ├── screen_context.py       ← ScreenContext (tracks active apps and browser URLs)
  ├── state.py                ← Shared AgentState TypedDict
  ├── demo_laya_agent.py      ← Interactive CLI demonstration for Laya decision triage
  ├── test_benchmark_suite.py ← Comprehensive speed, loop, and failure test suite
  ├── benchmark_report.md     ← Live benchmark results and latency report
  │
  ├── agents\
  │   ├── chat_agent.py       ← Optimus   | General conversation, news, app control
  │   ├── browser_agent.py    ← Bumblebee | Browser control, window focus, tab hotkeys
  │   ├── code_agent.py       ← Wheeljack | Code generation via unified Groq LLM
  │   ├── memory_agent.py     ← Perceptor | Semantic ChromaDB + LlamaIndex memory
  │   ├── reminder_agent.py   ← Ironhide  | Fast regex/Laya time extraction & scheduling
  │   └── vision_agent.py     ← Vision    | Screen parsing and spatial element clicking
  │
  ├── tools\
  │   ├── laya_engine.py      ← Local Laya decision engine (ModernBERT classification)
  │   ├── llm.py              ← Unified LLM & Vision client (Groq qwen/qwen3.8-27b)
  │   └── registry.py         ← Central tool registry and URL sanitization
  │
  ├── ui\
  │   └── hud.py              ← CustomTkinter HUD, character strips, bottom text entry
  │
  ├── memory\
  │   ├── chromadb\           ← Local vector database
  │   ├── llamaindex\         ← Code & document indices
  │   ├── conversation_log.jsonl ← Conversation history archive
  │   └── notes.txt           ← Persistent user notes
  │
  └── .env                    ← GROQ_API_KEY, CHROME_PATH
```

---

## 🔧 Installation & Setup

### Prerequisites
- **Python 3.12** (installed from [python.org](https://www.python.org/downloads/) — avoid Microsoft Store builds)
- **Google Chrome** or **Brave Browser**

### 1. Clone & Environment Setup
```powershell
git clone https://github.com/KevalParmar75/Assistant-3.0.git
cd Assistant-3.0
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
playwright install chromium
```

### 3. Environment Configuration (`.env`)
Create a `.env` file in the root directory:
```env
# Fast LLM & Multimodal Vision Provider (Groq Cloud API)
GROQ_API_KEY=your_groq_api_key_here

# Local Browser Path
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe

# Optional: Run in low-RAM mode
OPTIMUS_LOW_MEMORY=false
```

### 4. Index Installed Applications (Run Once)
```powershell
python setup_apps.py
```

### 5. Run the Benchmark Suite (Optional)
```powershell
python test_benchmark_suite.py
```

### 6. Launch Optimus
```powershell
python main.py
```

---

## 🎮 Usage Guide & Commands

| Objective | Command Example | Routing Agent |
|---|---|---|
| **Voice Activation** | *"Optimus"* (speak wake word) | Wake Listener |
| **Instant Mute** | *"Stop"* | Audio Controller |
| **Play Music** | *"Play Jogi on YouTube"* | Bumblebee (Browser) |
| **Search the Web** | *"Search best Python libraries on Google"* | Bumblebee (Browser) |
| **Open Application** | *"Open Spotify"* / *"Open VS Code"* | Optimus (Chat) |
| **In-Browser Actions** | *"New tab"* / *"Close tab"* / *"Go to GitHub"* | Bumblebee (Browser) |
| **Current News** | *"Give me brief current Indian news only headlines"* | Optimus (Chat / RSS) |
| **Screen Inspection** | *"What is on my screen right now?"* | Vision Agent |
| **UI Interaction** | *"Click on the search button"* | Vision Agent |
| **Set Reminder** | *"Remind me to call Mom at 7:30 pm"* | Ironhide (Reminder) |
| **Take Notes** | *"Take a note: Buy groceries tomorrow morning"* | Perceptor (Memory) |
| **Recall Notes** | *"Read my notes"* | Perceptor (Memory) |
| **Generate Code** | *"Write a FastAPI route with rate limiting"* | Wheeljack (Code) |

---

## 🧠 Model Roster

| Purpose | Model | Provider / Execution | Latency |
|---|---|---|---|
| **Local System 1 Decision Engine** | `convaiinnovations/laya` | 100% Local (PyTorch / ModernBERT) | `495.13 ms` (warm) / `~33.2s` (cold boot) |
| **High-Speed Conversational LLM** | `qwen/qwen3.8-27b` | Groq Cloud API | `243.48 ms – 549.66 ms` |
| **Code Generation** | `qwen/qwen3.8-27b` | Groq Cloud API | `323.89 ms` (~308.7 tok/s) |
| **Screen Vision & Spatial Grounding** | `qwen/qwen3.8-27b` | Groq Cloud API (Multimodal Vision) | `324.66 ms` |
| **Secondary Text Fallback** | `openai/gpt-oss-120b` | Groq Cloud API | Failover Model (`605.76 ms`) |
| **Vector Memory Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Local (sentence-transformers) | `228.88 ms` (commit) |
| **Voice Synthesis (TTS)** | `Edge TTS` (Ryan / Andrew / Thomas / Guy) | Microsoft Azure Free Tier | Real-Time Stream |

---

## 📜 License
Distributed under the MIT License. Built with ❤️ for the open-source agentic AI community.
