#Omnix-Ai
**AUTONOMOUS · SELF-EXTENDING · LOCAL-FIRST · TERMUX-NATIVE**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Termux](https://img.shields.io/badge/Termux-Android-000000?style=for-the-badge&logo=android&logoColor=3DDC84)](https://termux.dev)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge)](https://ollama.com)
[![Stdlib](https://img.shields.io/badge/Stdlib-Only-2E8B57?style=for-the-badge)](https://docs.python.org/3/library/)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](#-license)
[![Author](https://img.shields.io/badge/Author-SYLHETYHACKVENGER-red?style=for-the-badge)](#-author)

**Omnix-Ai** — a fully autonomous, self-extending AI operator that lives inside Termux.  
Runs entirely on-device with a local Ollama model. Audits code, browses the web, drives your phone,  
manages a personal knowledge base, performs authorized security recon, and **builds new tools for itself** when it hits a wall.

[Features](#-features) · [Install](#-installation) · [Usage](#-usage) · [Tools](#-tool-reference) · [Security Model](#-security-model) · [Legal](#-legal--ethical-notice)

</div>

---

## 📖 Overview

**Omnix-Ai** is a *singular Python file* that turns any rooted-or-not Android phone running Termux into an autonomous AI agent. There is no cloud, no API key, no telemetry — every token is generated locally by [Ollama](https://ollama.com), every tool runs on your device, every file stays on your disk.

The agent thinks in structured JSON steps, calls **exactly one tool per turn**, reads the result, and adapts. When it lacks a capability, it **writes its own plugin**. When it breaks its own code, it **rolls back automatically**. When it needs to prove something works, it **verifies before answering**.

> Built for red-teamers, blue-teamers, CTF players, mobile researchers, and anyone who wants a personal AI operator on an Android phone — without ever sending data off-device.

---

## ⚡ Features

### 🧠 Autonomous Core
| Capability | Description |
|---|---|
| **Local-first LLM** | Runs on `huihui_ai/qwen2.5-coder-abliterate:1.5b` (configurable) via Ollama. No cloud calls. |
| **One tool per turn** | Structured JSON loop — `{"thought","tool","args"}` — with repeat & failure detection. |
| **Self-extending** | Writes new Python plugins into `~/.omnix_ai/tools/` and loads them live. |
| **Self-editing** | Rewrites its own source with syntax validation + backup + `/rollback`. |
| **Auto-recovery** | Broken writes are reverted; missing Ollama server is auto-started. |
| **Verify-before-answer** | Every changed file is re-checked; agent must call `verify` → `READY` before `finish`. |

### 🛡️ Security & Recon Toolkit
| Tool | Function |
|---|---|
| `cve_check` | NVD 2.0 API lookup for product/version pairs. Auto-parses `nmap -sV` output. |
| `envinfo` | Detects Termux vs Kali chroot vs Debian, root availability, 30+ installed security tools. |
| **Auto scan-logging** | `nmap`, `gobuster`, `sqlmap`, `hydra`, `nikto`, `ffuf`, `wpscan`, `masscan`, `whatweb`, `dirb` output → saved to `notes/scans/` + indexed in the KB. |
| **exploitdb bridge** | If `searchsploit` is installed, PoC availability is flagged next to each CVE. |
| **Kali-in-Termux reference** | Built-in cheatsheet (`proot-distro`, `kali-tools-*`, tool syntax, wordlist sources). |
| **CVE-safe by design** | Read-only lookups. Never fetches, executes, or transfers exploits. |

### 🌐 Browser Automation (CDP)
Real JavaScript-capable browser over Chrome DevTools Protocol — stdlib WebSocket client, no `selenium`, no `playwright`.

- `open` · `elements` · `click` · `type` · `press` · `select` · `scroll` · `wait` · `find` · `back`
- `text` · `html` · `links` · `js` · `network` · `response` · `console` · `storage` · `screenshot`
- Works headless (Termux `chromium`) **or** against your real rooted Chrome.

### 📱 Phone as a Platform (needs `su`)
- **UI automation** — `uiautomator dump` → node tree → tap/type/scroll by text or index.
- **Apps** — `open_app`, list installed packages, resolve friendly names to package IDs.
- **Messaging** — SMS via `termux-sms-send`, WhatsApp via `wa.me` + UI tap (with confirmation).
- **Calls** — `dial`, `hangup`, `answer`, `status` (emergency numbers blocked).
- **Inbox** — read SMS, call log, WhatsApp/Telegram notifications (`termux-notification-list`).
- **Contacts** — resolve name → number via `termux-contact-list`.
- **Clipboard / screenshot / keys** — full control with `input keyevent`, `screencap`.

### 📚 Knowledge Base (RAG, offline)
- `learn` — ingest a file **or an entire folder** into a permanent, searchable index.
- Supports `.pdf .docx .epub .pptx .odt .rtf .html .txt .md .csv .json .py …` + **OCR** for images and scanned PDFs.
- BM25 ranking + domain tagging from subfolder names (`security/`, `allopathy/`, `dictionary/`, …).
- `recall` — best passages with source attribution, auto-injected into tasks.
- **Fast dictionary** — `translate` does instant English↔Bangla lookup from plain text lists.
- **Study mode** — reads a whole book chunk-by-chunk, builds running notes, folds them into the KB.

### 🔧 Developer & Code Intelligence
- `audit` — chunked, line-by-line review of an **entire codebase**. Static analyzers (AST + pyflakes) *plus* a local model for real bugs, with hallucination guards (model must quote the exact line).
- `patch_lines` — replace a line range safely (with auto syntax check + auto rollback).
- `debug` — runs code, parses the traceback, shows the failing code context.
- `view` — numbered lines, load-once cache prevents redundant reads.
- `verify` — syntax + optional `test_cmd` runner before `finish`.
- `undo` · `nano` — restore prior versions or hand the file to you.

### 🖥️ Console Experience
- Futuristic neon TUI: rounded panels, live status bar, uptime, mode indicator.
- Chat mode (**instant, streamed, no tools**) vs Agent mode (`!task` prefix or `/agent`).
- Single-threaded stdin owner — approvals never fight a busy REPL.
- Full session log of **every** tool result, uncut, at `~/.omnix_ai/logs/session_*.log`.

---

## 🖼️ Architecture

```

┌─────────┐      ┌─────────────┐         ┌─────────────┐    ┌──────────┐
│  SHELL  │      │   BROWSER   │         │   PHONE     │    │    KB    │
│  root   │      │     CDP     │         │  su + API   │    │  BM25    │
└─────────┘      └─────────────┘         └─────────────┘    └──────────┘
│                  │                       │                  │
▼                  ▼                       ▼                  ▼
nmap, hydra,     real Chrome /            SMS · call ·       chunks.jsonl
sqlmap, etc.     headless chromium        apps · inbox       sources.json
│
▼
┌─────────────────────────────────────────────────────┐
│  notes/scans/  →  auto-indexed in the KB (security) │
└─────────────────────────────────────────────────────┘

```

---

## 🚀 Installation

### 1. Prerequisites

```bash
pkg update && pkg upgrade -y
pkg install python git ollama
```

2. Pull a local model

```bash
ollama pull huihui_ai/qwen2.5-coder-abliterate:1.5b
```

Any Ollama model works. Swap with AGENT_MODEL=llama3.1:8b python omnix_ai.py on faster phones.

3. Clone & run

```bash
git clone https://github.com/SYLHETYHACKVENGER/Omnix-Ai.git
cd Omnix-Ai
python omnix_ai.py
```

4. Optional power-ups

Component Command Unlocks
Phone control pkg install termux-api + install Termux:API (F-Droid) + grant permissions SMS, calls, contacts, notifications
Root toolbox Rooted device + pkg install tsu ui automation, pm, am, input, dumpsys
Real browser pkg install x11-repo tur-repo && pkg install chromium browser tool (headless)
Real Chrome Rooted + su -c 'socat TCP-LISTEN:9222,bind=127.0.0.1,fork,reuseaddr ABSTRACT-CONNECT:chrome_devtools_remote &' Drive your logged-in Chrome session
Code audit pip install pyflakes --break-system-packages Undefined-name detection in audits
Documents pkg install poppler tesseract PDFs, scans, images
Kali tooling pkg install proot-distro && proot-distro install kali Full Kali toolset inside Termux
exploitdb pkg install exploitdb PoC availability flagged next to CVEs

---

🎮 Usage

Interactive console

```bash
python omnix_ai.py
```

You land in CHAT mode — type normally, get instant streamed answers with no tool overhead.

Force agent mode

Prefix with ! for a single task, or switch persistently:

```
!scan my LAN and tell me which hosts run outdated Apache
/agent
```

One-shot (non-interactive)

```bash
python omnix_ai.py "audit ./src for real bugs and fix them"
```

Commands

Command Action
/help Show all commands
/status System panel (mode, uptime, tools)
/doctor Ollama + model health check
/auto Toggle auto-approval for tool calls
/agent /chat Switch modes
/reset Clear conversation memory
`/raw on off`
/log Show path to full session log
/tools List custom plugins
/audit <path> Full-codebase audit with live progress
/study <file> Read a whole book, build notes
/learn <path> Instant-ingest a file/folder into the KB
/recall <query> Search everything you've learned
`/kb list stats
/rollback Restore last self-edit backup
exit Shut down

Environment variables

Variable Default Purpose
AGENT_MODEL huihui_ai/qwen2.5-coder-abliterate:1.5b Ollama model name
AUDIT_MODEL same as AGENT_MODEL Model used for audit / study
OLLAMA_URL http://127.0.0.1:11434/api/chat Ollama endpoint
BROWSER_CDP 127.0.0.1:9222 Chrome DevTools host
GITHUB_TOKEN (none) Raises GitHub API rate limits
AGENT_NAME OMNIX-AI Console banner title
NO_COLOR (none) Disable ANSI colors

---

🧰 Tool Reference

Files & Code

Tool Args Description
read_file path Read a file (load-cached)
write_file path, content Write with auto syntax-check + revert-on-break
edit_file path, old, new Targeted string replace
patch_lines path, start, end?, new Range replace, safest fix path
view path, start?, end? Numbered lines
check path Lint/syntax for .py .js .sh .json
debug path, args? Run + show failing line context
audit action, path?, id? start \| next \| status \| report \| show \| fix \| skip
verify test_cmd? Confirm all changed files are READY
undo path Restore previous version
nano path, line? Open nano for the user

Web & Network

Tool Description
search DuckDuckGo HTML search
fetch Plain-text page fetch
research Search + read top pages
browser Full CDP browser (open/click/type/js/network/…)
http Raw HTTP for API testing
github search \| readme \| tree \| file \| clone

Security

Tool Description
cve_check NVD lookup; auto-parses scan output; flags local exploitdb PoCs
envinfo Termux/Kali/root + tool inventory
shell / root Command execution (blocked patterns refused)

Phone

Tool Description
ui Full automation: dump \| read \| open_app \| tap_text \| tap_index \| type \| scroll_to \| wait_for \| screenshot
message SMS (default) or WhatsApp, approval required
inbox SMS, notifications, call log
call dial \| hangup \| answer \| status
contacts Name → number
clipboard get \| set

Knowledge

Tool Description
learn Ingest file/folder, skip unchanged
recall BM25 search with source + domain
kb list \| stats \| forget \| domains
read_doc Paginated text extraction
study Chunked book reading → notes → KB
translate Instant EN↔BN dictionary

Meta

Tool Description
create_tool Author a new plugin live
self_edit Edit its own source
restart Reload after self-edit
remember Append to long-term memory
finish Final answer (after verify)

---

🔐 Security Model

Omnix-Ai is defensive by default — it is an assistant, not a weapon.

🚫 Built-in protections

· Dangerous shell block — refuses rm -rf /, mkfs, fastboot, dd of=/dev/*, /dev/block, fork bombs, reboot bootloader.
· Root always asks — root and sudo/su in shell require explicit per-command approval (never auto-approved).
· Every message approved — message and call require user "y" even with /auto on.
· Emergency call block — 911, 112, 999, 000, etc. are hard-refused.
· Irreversible UI taps — Send, Pay, Confirm, Delete, Post, Tweet trigger a second confirmation.
· Account/verification guard — refuses to create accounts, solve CAPTCHAs, or pass SMS/email verification.
· CVE tool is read-only — NVD lookups only. Never downloads, executes, or transfers exploits.
· Scan output is logged, not weaponized — saved to notes/scans/ and indexed locally so recall can answer "what did my last nmap find?".
· Every write is backed up — auto-reverted if the new file breaks syntax.
· All output is session-logged — ~/.omnix_ai/logs/session_*.log holds every tool result uncut.

🧭 Threat model

You are… Omnix-Ai can help with…
A CTF player Reading service banners, correlating CVEs, triaging nmap output, drafting payloads against the lab target only
A pentester on an authorized engagement Saving scan artifacts, tracking CVEs, using envinfo to confirm which tools exist before assuming
A mobile researcher Driving apps via ui, screenshotting, capturing logcat, dumping package data on your own device
A developer Auditing your own codebase line-by-line with a local reviewer
A student Building a personal knowledge base from books and PDFs

It will not — scan the internet, exploit a target without you running the command, exfiltrate data, install persistence, or bypass a login/CAPTCHA.

---

📚 Knowledge Base & Documents

Drop your library into ~/.omnix_ai/knowledge/<domain>/:

```
knowledge/
├── security/          ← nmap cheatsheets, CVE notes, scan summaries
├── allopathy/         ← medical PDFs, formulary, notes
├── ayurveda/
├── homeopathy/
├── dictionary/        ← plain-text EN↔BN (one entry per line)
├── general/
└── <any-name>/        ← folder name becomes the domain tag
```

Formats auto-detected: .pdf .docx .pptx .odt .rtf .epub .html .txt .md .csv .json .py + images/scanned PDFs via OCR.

On startup, only changed files are re-ingested — stat-checked, so the second run is instant.

Use learn for fast searchable ingestion, study when you want the model to actually read a whole book and produce notes.

---

🖥️ Screenshot

```
╔══════════════════════════════════════════════════════════════════════╗
║ ▄▀█ █▀▄▀█ █▄ █ █ ▀▄▀ ▄▀█ █                                        ║
║ █▀█ █ ▀ █ █ ▀█ █ █ █ █▀█ █                                        ║
║                                                                      ║
║ neural interface online  ●                                           ║
║                                                                      ║
║ TOOLS 3 custom   PID 8116                                            ║
║                                                                      ║
║ ⌨  just type to chat  ·  !task uses tools  ·  /help                  ║
╚══════════════════════════════════════════════════════════════════════╝

┊ ● READY ┊ CHAT ┊ AUTO○ ┊ turns:0 ┊ up 00:00:12 ┊ 14:22:07
╭─[OMNIX-AI]
└─λ !run nmap -sV 192.168.1.1 and check the Apache version for CVEs

  ▸ nmap ... 
  ▸ cve_check ...
  ▸ finish
╭─◀ AGENT
│ Apache 2.4.49 is vulnerable to CVE-2021-41773 (path traversal,
│ CVSS 7.5). PoC available in local exploitdb: "Apache 2.4.49 - Path
│ Traversal". This is against your own network 192.168.1.0/24 only.
╰──────────────────────────────────────────────────────────────────
```

---

⚖️ Legal & Ethical Notice

Omnix-Ai is provided for authorized security testing, CTFs, research, and personal automation only.

You — the operator — are solely responsible for how you use it.

· Scanning, probing, exploiting, or accessing any system without written authorization is illegal in most jurisdictions (CFAA, Computer Misuse Act, IT Act, etc.).
· Practice only against deliberately vulnerable targets you own or that are provided for that purpose: DVWA, OWASP Juice Shop, Metasploitable, TryHackMe, HackTheBox, your own lab VMs.
· cve_check and envinfo are read-only lookups. shell, root, browser, ui, and http execute your commands — you bear the consequences.
· When using AI-generated code, always read it before running it. The agent tries, but a 1.5B local model is not infallible.
· Do not use this tool to break the law, harass, stalk, spy, or bypass any authentication or consent mechanism.

The author assumes zero liability for misuse, damage, or legal consequence.

---

🤝 Contributing

Contributions are welcome — bug reports, plugin ideas, cheatsheet additions.

1. Fork the repo.
2. Add your plugin under ~/.omnix_ai/tools/ (must define NAME, DESC, run(args)).
3. Open a PR with a clear description and a legal-target scenario.

Found a security issue? Open a private advisory, not a public issue.

---

📜 License

MIT License — see LICENSE for full terms.

---

👤 Author

<div align="center">

SYLHETYHACKVENGER

aka THE-ERROR808

https://img.shields.io/badge/GitHub-SYLHETYHACKVENGER-181717?style=for-the-badge&logo=github

Omnix-Ai — built in a phone, for the phone, guarded by you.

```
"The best AI is one you own end-to-end."
```

⭐ Star the repo if Omnix-Ai gave you an edge.
🐛 Report bugs — the agent will try to fix itself, but a human catches more.
🔐 Stay legal — the tools are sharp; the ethics are yours.

</div>

---

<div align="center">
<sub>Built with ❤️ on Android · Termux · Ollama · Python 3 · zero cloud dependencies</sub>
</div>
```
