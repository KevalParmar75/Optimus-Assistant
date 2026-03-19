# 🤖 Optimus — Transformers Universe AI Assistant
> *"Autobots, roll out."*

A voice-controlled AI assistant built around a Transformers universe theme. Each capability is handled by a different Transformer character with their own pixel art face, personality, and voice.

---

## 🌟 The Team

| Character | Role | Specialty | Color |
|---|---|---|---|
| **Optimus Prime** | Orchestrator | General chat, web search, app control | 🔵 Cyan |
| **Bumblebee** | Browser Agent | Web browsing, YouTube, Google | 🟡 Yellow |
| **Wheeljack** | Code Agent | Code generation, debugging, execution | 🟢 Green |
| **Ironhide** | Reminder Agent | Reminders, scheduling, alerts | 🔴 Red |
| **Perceptor** | Memory Agent | Long-term memory, notes, recall | 🔴 Dark Red |

---

## ✅ What It Can Do Right Now

### 🎙️ Voice Control
- **Wake word** — say *"Optimus"* to activate (45 second active window)
- **Always listening** for wake word in background — zero CPU when idle
- **Auto language detection** — English, Hindi, Gujarati
- **Voice interrupt** — say *"stop"* to cut speech mid-sentence
- **Multi-language responses** — replies in whichever language you spoke

### 🌐 Browser Automation (Bumblebee)
- *"Open YouTube and search lofi music"*
- *"Play Jogi on YouTube"* — searches and auto-plays first result
- *"Search LeetCode on Google"*
- *"Open GitHub"* / *"Go to gmail"*
- *"Close tab"* — closes the browser tab
- Uses your existing Chrome — no new window, no login needed

### 👁️ Screen Vision (Qwen VL)
- *"What's on my screen?"* — describes everything visible
- *"Click on the search bar"* — finds and clicks exact element
- *"Click the first video"* — vision-guided click
- *"What does it say?"* — reads text on screen
- Screenshots stay in RAM — never written to disk

### 📱 App Control
- *"Open VS Code"* / *"Open Spotify"* / *"Open WhatsApp"*
- *"Open calculator"* / *"Open file explorer"*
- All apps indexed via AppOpener — works with your installed apps

### 🔍 Web Search
- *"Search who is Elon Musk"*
- *"Tell me about quantum computing"*
- Uses DuckDuckGo — no API key needed

### 🧠 Memory System
- **Auto-saves** every conversation silently in background
- **ChromaDB** for general conversations and preferences
- **LlamaIndex** for code and posts
- **Raw log** at `memory/conversation_log.jsonl` — always backed up
- *"Do you remember when we talked about..."* — semantic recall
- *"Remember this"* — explicitly save current exchange

### 📝 Notes
- *"Take a note — I have a meeting at 3pm"*
- *"Note down call mom tomorrow"*
- *"Read my notes"* / *"Show my notes"*
- Saved to `memory/notes.txt` with timestamps

### ⏰ Reminders
- *"Remind me to go to market at 5:45"*
- *"Set a reminder at 9pm to call mom"*
- *"List my reminders"*
- Windows toast notification + Optimus speaks it at trigger time

### 💻 Code Agent (Wheeljack)
- *"Write a Flask API with two endpoints"*
- *"Debug this Python code"*
- *"Explain what this function does"*
- Uses `Qwen2.5-Coder-32B` — specialized code model

### 📱 WhatsApp
- *"WhatsApp Rahul and say I'll be late"*
- *"Send a message to Mom saying I'm on my way"*
- Vision-powered — finds contact, types, sends

---

## 🏗️ Architecture

```
E:\optimus\
  ├── main.py                 ← Orchestrator, UI, wake word, LangGraph
  ├── state.py                ← Shared AgentState TypedDict
  ├── agents\
  │   ├── chat_agent.py       ← Optimus  | Qwen 2.5 72B
  │   ├── browser_agent.py    ← Bumblebee| subprocess + pyautogui
  │   ├── code_agent.py       ← Wheeljack| Qwen 2.5 Coder 32B
  │   ├── memory_agent.py     ← Perceptor| ChromaDB + LlamaIndex
  │   ├── reminder_agent.py   ← Ironhide | APScheduler
  │   └── vision_agent.py     ← Eyes     | Qwen 2.5 VL
  ├── tools\
  │   └── registry.py         ← All tools registered here
  ├── ui\
  │   └── hud.py              ← All 5 pixel art characters + HUD states
  ├── memory\
  │   ├── chromadb\           ← Vector embeddings
  │   ├── llamaindex\         ← Code/post index
  │   ├── conversation_log.jsonl  ← Raw backup
  │   └── notes.txt           ← Quick notes
  └── .env                    ← HF_TOKEN, CHROME_PATH
```

### LangGraph Flow
```
Voice Input
    ↓
Supervisor (routes to correct agent)
    ↓
Agent runs (chat/browser/code/memory/reminder/vision)
    ↓
Response spoken (Edge TTS)
    ↓
Auto-saved to memory (background thread)
```

---

## 🎨 HUD States

| State | Color | When |
|---|---|---|
| STANDBY | 🔵 Cyan | Idle, waiting for wake word |
| LISTENING | 🔴 Red | Wake word heard, active window |
| PROCESSING | 🟡 Yellow | Thinking / calling API |
| SPEAKING | 🟢 Green | TTS playing |
| BROWSING | 🟠 Orange | Bumblebee controlling browser |
| CODING | 🟢 Bright | Wheeljack generating code |
| REMEMBERING | 🟣 Purple | Memory operation |
| REMINDER | 🩷 Pink | Reminder firing |
| SEEING | 🟡 Gold | Vision agent reading screen |

---

## 🔧 Setup

### Requirements
```
Python 3.12 (from python.org — NOT Microsoft Store)
```

### Install
```powershell
cd E:\optimus
python -m venv venv
.\venv\Scripts\activate
pip install customtkinter speechrecognition pywhatkit edge-tts pygame pyautogui
pip install langgraph huggingface-hub duckduckgo-search AppOpener python-dotenv
pip install chromadb sentence-transformers llama-index
pip install playwright apscheduler win10toast mss Pillow f5-tts gradio_client
playwright install chromium
```

### .env file
```
HF_TOKEN=your_huggingface_token_here
CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

### First run setup
```powershell
# Index your installed apps (run once)
python setup_apps.py

# Run Optimus
python main.py
```

---

## 🎙️ Voice Commands Reference

| Say | What happens |
|---|---|
| *"Optimus"* | Activates assistant |
| *"Stop"* | Interrupts speech |
| *"Open YouTube"* | Opens YouTube in Chrome |
| *"Play [song] on YouTube"* | Searches and plays |
| *"Search [query] on Google"* | Opens Google search |
| *"What's on my screen?"* | Vision describes screen |
| *"Click on [element]"* | Vision finds and clicks |
| *"Open [app name]"* | Launches app |
| *"Remind me to [X] at [time]"* | Sets reminder |
| *"Note down [text]"* | Saves a note |
| *"Read my notes"* | Reads notes back |
| *"Do you remember [X]"* | Searches memory |
| *"Remember this"* | Saves last exchange |
| *"What time is it?"* | Instant system time |
| *"What's today's date?"* | Instant system date |
| *"Write a [code] function"* | Wheeljack generates code |
| *"WhatsApp [name] and say [msg]"* | Sends WhatsApp message |
| *"Close tab"* | Closes browser tab |

---

## 🔲 Coming Soon

- [ ] Taskbar multi-character HUD (all 5 visible, active one scales up)
- [ ] Eye blinking + head movement animations
- [ ] Voice cloning (ElevenLabs — character-accurate voices)
- [ ] Transformation sound effects
- [ ] Twitter / LinkedIn posting
- [ ] IDE code injection (type directly into VS Code)
- [ ] Voice authentication (your voice only)
- [ ] Screen vision fully integrated into all browser actions

---

## ⚠️ Known Issues

| Issue | Cause | Fix |
|---|---|---|
| Memory embedding fails | Microsoft Store Python can't load `fbgemm.dll` | Install Python from python.org |
| Interrupt listener fails | Two microphones can't open simultaneously | Stop words detected in main loop instead |
| Browser opens new window | Chrome debug port not configured | Add `CHROME_PATH` to `.env` |

---

## 🧠 Models Used

| Purpose | Model | Provider |
|---|---|---|
| General chat | Qwen/Qwen2.5-72B-Instruct | HuggingFace (free) |
| Code generation | Qwen/Qwen2.5-Coder-32B-Instruct | HuggingFace (free) |
| Screen vision | Qwen/Qwen2.5-VL-7B-Instruct | HuggingFace (free) |
| Memory embeddings | all-MiniLM-L6-v2 | Local (sentence-transformers) |
| Text to speech | Edge TTS (Ryan/Andrew/Thomas/Guy) | Microsoft (free) |

---

*Built with ❤️ by Keval Parmar for the open-source AI community.*
