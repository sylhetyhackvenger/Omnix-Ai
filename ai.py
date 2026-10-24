#!/usr/bin/env python3
import json, os, re, subprocess, sys, html, tempfile, shutil, time, importlib.util
import socket, base64, struct, threading, shlex, ast, difflib, zipfile, queue
import xml.etree.ElementTree as ET
import urllib.request, urllib.parse, urllib.error

TOOL_NAME = "Omnix-Ai"
AUTHOR = "SYLHETYHACKVENGER (THE-ERROR808)"

MODEL = os.environ.get("AGENT_MODEL", "huihui_ai/qwen2.5-coder-abliterate:1.5b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MAX_STEPS = 25
MAX_OUT = 20000
SELF = os.path.abspath(__file__)
HOME_DIR = os.path.expanduser("~/.omnix_ai")
TOOLS_DIR = os.path.join(HOME_DIR, "tools")
BACKUPS = os.path.join(HOME_DIR, "backups")
MEM = os.path.join(HOME_DIR, "memory.txt")
for d in (TOOLS_DIR, BACKUPS):
    os.makedirs(d, exist_ok=True)
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"

SAFE = ("ls", "pwd", "cat", "echo", "date", "whoami", "uname", "df", "free", "head", "tail",
        "grep", "find", "wc", "which", "termux-battery-status", "termux-wifi-connectioninfo",
        "termux-clipboard-get", "git status", "git log", "pip list", "python3 --version")
BLOCK = (
    r"(?i)rm\s+-[a-z]*r[a-z]*\s+[\"']?(/|/system|/vendor|/boot|/data|/storage|/sdcard|~|\$HOME)/?\*?[\"']?(\s|;|&|\||$)",
    r"(?i)mkfs|make_ext4fs|flash_image|fastboot|\bwipe\b",
    r"(?i)dd\s+.*of=\s*/dev/",
    r"/dev/block",
    r"(?i)reboot\s+(bootloader|recovery|download|edl)",
    r":\(\)\s*\{",
    r">\s*/dev/(sd|block|mmc)",
)

PLUGINS = {}


def load_plugins():
    PLUGINS.clear()
    for f in sorted(os.listdir(TOOLS_DIR)):
        if not f.endswith(".py"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f[:-3], os.path.join(TOOLS_DIR, f))
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            PLUGINS[m.NAME] = (m.DESC, m.run)
        except Exception as e:
            print(f"  [plugin {f} failed to load: {e}]")


BASE = """You are Omnix-Ai, an autonomous agent inside Termux on an Android phone. Finish the user's task by using tools, one step per turn.

Reply with ONLY one JSON object:
{"thought": "short reasoning", "tool": "<name>", "args": {...}}

Core tools:
- shell {"cmd"}: run a Termux command (pkg, pip, python3, git, curl, termux-* API). Words like am, pm, monkey, input, svc are shell COMMANDS, never tool names: run them through shell or root. To open an app use ui {"action":"open_app","package":"..."}
- python {"code"}: run a Python snippet
- read_file {"path"} | write_file {"path","content"} | edit_file {"path","old","new"}
- view {"path","start?","end?"}: show a file WITH LINE NUMBERS
- check {"path"}: syntax check and lint a file (.py .js .sh .json)
- debug {"path","args?"}: run a program and return the exact error plus the code around the failing line
- cve_check {"product?","version?","text?","path?"}: look up known CVEs for a service (NVD). scan tool output (nmap/gobuster/sqlmap/hydra/etc) run via shell is auto-saved to notes/scans/ and indexed - only use real, authorized-target scope.
- patch_lines {"path","start","end?","new"}: replace a line range. The safest way to fix a bug.
- audit {"action","path?","id?"}: review a BIG codebase chunk by chunk so every line is examined. start{path} | next | status | report | show{id} | fix{id} | skip{id}
- read_doc {"path","start_word?","end_word?"}: extract readable text from a pdf, docx, epub, txt, md, html, or csv file
- study {"action","path?"}: read a WHOLE book/document chunk by chunk and build running notes, so you actually gather knowledge from something bigger than context allows. start{path} | next{chunks?} | status | notes | remember_all
- learn {"path","force?"}: add a file OR a whole folder (books, notes, docs, code, images with OCR) to your permanent, searchable knowledge base. Fast, no model calls. Unchanged files are skipped.
- recall {"query","k?"}: search EVERYTHING you have learned and return the best passages with their source. Use it before answering questions that may be covered by the user's documents or earlier studied books.
- kb {"action": "list|stats|forget|domains","source?"}: see or manage what you know, grouped by domain (a knowledge/<domain>/ subfolder)
- translate {"word"}: fast exact English<->Bangla lookup from knowledge/dictionary/, falling back to the knowledge base for anything not in the word list
- envinfo {}: check what's actually here before guessing - Termux vs a Kali/Debian chroot, pkg vs apt, root availability, and which common security tools (nmap, hydra, john, sqlmap, gobuster, aircrack-ng, msfconsole, ...) are really on PATH right now. Call this FIRST for any Termux/Kali/pentest-tooling task instead of assuming a command or package name; recall "termux kali" for the cheat sheet of exact command syntax, chroot setup, and tool categories.
- verify {"test_cmd?"}: check every file you changed (syntax + optional tests). Returns READY or NOT READY.
- undo {"path"}: restore a file's previous version | nano {"path","line?"}: open nano so the USER can review
- search {"query"}: web search | fetch {"url"}: quick plain-text download (no JavaScript)
- browser {"action",...}: a REAL browser with JavaScript. open{url} | elements | click{index or text or selector} | type{index or selector,text,submit?,append?} | press{key} | select{index,value} | scroll{direction} | wait{text or seconds} | find{text} | back | text{selector?} | links | html{selector?} | js{code} | network | response{index} | console | storage | screenshot | close
  Workflow: open a page, read the numbered clickable elements it prints, then click/type by number or visible text, and read the result. Use network/response/html to see how a site works.
- http {"method","url","headers","body"}: raw HTTP request, for testing APIs and your own backends
- research {"query"}: search the web AND read the top pages. Use it whenever you do not know how to do something.
- github {"action",...}: search{query} | readme{repo} | tree{repo,path?} | file{repo,path} | clone{repo,dest?}
- install {"manager":"pkg|pip|npm","name"}: install a package or tool
- download {"url","path"}: save a file from the internet
- contacts {"query"}: find a person's phone number by name
- message {"to","text","app?"}: send an SMS (default) or app=whatsapp message. "to" is a name or number. The user approves every message.
- inbox {"source?":"sms|notifications|calls","from?","app?","unread?","limit?"}: read received texts, chat-app notifications (WhatsApp, Telegram, email...) or the call log
- call {"action":"dial|hangup|answer|status","to?"}: phone calls. dial asks the user to approve.
- clipboard {"action":"get|set","text"}: read or set the phone clipboard
- ui {"action",...}: use the phone like a human (needs root). dump | read | current | apps{query} | open_app{package or name} | tap_text{text,nth?,wait?} | tap_index{index} | tap{x,y} | long_press{text} | swipe{x1,y1,x2,y2} | scroll_down | scroll_up | scroll_to{text} | wait_for{text,seconds?} | type{text,into?,clear?,submit?} | key{name: back/home/enter/paste/copy/recent} | wait{seconds} | screenshot{path?}. Every action returns the new screen, read it before your next step.
- remember {"note"}: save a lesson or fact to long-term memory
- create_tool {"name","description","code"}: give yourself a NEW tool. code must define run(args) that takes a dict and returns a string.
- self_edit {"old","new"}: change your own source code (applies after restart)
- root {"cmd"}: run a command as ROOT (device is rooted). Use for anything Termux alone cannot do.
- restart {}: reload yourself after self_edit
- finish {"answer"}: final answer after you verified the result

Knowledge: a knowledge/ folder on disk holds subfolders by topic (e.g. security, allopathy, ayurveda, homeopathy, dictionary - the user may add more); everything in it is studied automatically on startup and kept in your searchable knowledge base, tagged by that folder's name as its "domain". Relevant stored passages are sometimes appended to the task automatically. When asked about a topic the user's documents may cover, call recall first and cite the domain and source title. For medical/remedy topics, treat what is stored as reference material to cite, not as something to turn into personalized diagnosis or dosing - point the user to a professional or the label for that. When the user gives you a book, folder or document to absorb, call learn (instant search), and for deep understanding also use study. Documents and books: never try to read_doc a whole large file at once, it will be truncated. For a short document, read_doc once or twice is enough. For a real book or long PDF, use study start then study next repeatedly until status shows 100%, then study notes has what you learned (or study remember_all to keep it long-term). Big codebases: never view whole files. Use audit start, then audit next repeatedly, then audit report, then audit show/fix one finding at a time. Before finish, if you changed any files, call verify and only finish when it says READY. Bug fixing: call debug, read the error and the failing line, use view if you need more, fix ONLY that spot with patch_lines, then debug again until it runs clean. Never rewrite a whole file to fix one bug. Every write is syntax-checked automatically, and a change that breaks working code is reverted. Rules: if you do not know how to do something, call research or github search BEFORE guessing, then remember the method that worked. To operate apps: open_app, ui dump, tap_text/type/scroll, and dump again to confirm each result. To post or upload to the user's own accounts, use their installed apps through ui (or the official API). Never create accounts, solve CAPTCHAs, or pass SMS/email verification, and never use passwords you were not given: tell the user to do that step, then continue afterwards. One tool per turn. Read each result, then adapt. If a step fails, change approach, never repeat the same failing command. Write code, run it, fix errors until it works. Verify before finish. If you lack a capability, build it with create_tool. Always end with finish. Never guess file paths: if you are not sure a file exists, run shell ls or find first. Once a file is loaded, do not read it again, use what you already have.
Phone playbook: to text someone use message {to,text} (a name works, contacts is only needed to look a number up). If several contacts match, ask the user which. To read replies use inbox (source=notifications for WhatsApp/Telegram). To call: call dial, then call status, call hangup when done. For any other chat app drive it with ui (open_app, tap_text the chat, type, then ask the user before tapping Send). Web playbook: browser open, act by element number or visible text, read each result; if a page needs a login, code or CAPTCHA, tell the user to do that step.
Root toolbox (use with the root tool): pm list packages / pm install / pm disable-user, am start / am force-stop, input tap X Y / input swipe / input text / input keyevent, screencap -p /sdcard/s.png, uiautomator dump /sdcard/ui.xml (read the screen), settings get/put, svc wifi|data enable|disable, dumpsys battery|activity|window, getprop, logcat -d, cat/ls on /data/data/<pkg>, cmd package, ip / iptables.
Phone: termux-notification, termux-toast, termux-clipboard-set, termux-location, termux-camera-photo, termux-torch, termux-vibrate, termux-open-url, termux-sms-send.
"""


def build_system():
    s = BASE + f"\nHome: {os.path.expanduser('~')}  Cwd: {os.getcwd()}"
    if PLUGINS:
        s += "\n\nYour own custom tools (call by name):\n" + "\n".join(
            f"- {n}: {d}" for n, (d, _) in PLUGINS.items())
    if os.path.exists(MEM):
        s += "\n\nLong-term memory:\n" + open(MEM).read()[-1200:]
    return s


def think(system, hist):
    msgs = hist[-14:]
    while msgs and msgs[0]["role"] != "user":
        msgs = msgs[1:]
    body = {"model": MODEL, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": system}] + msgs,
            "keep_alive": "30m", "options": {"temperature": 0.2, "num_ctx": 8192}}
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)["message"]["content"]


RAW = {"full": False}
LOG_PATH = os.path.join(HOME_DIR, "logs")
os.makedirs(LOG_PATH, exist_ok=True)
SESSION_LOG = os.path.join(LOG_PATH, "session_" + time.strftime("%Y%m%d_%H%M%S") + ".log")


def _log_raw(tag, text):
    try:
        with open(SESSION_LOG, "a") as f:
            f.write(f"\n----- {tag} @ {time.strftime('%H:%M:%S')} -----\n{text}\n")
    except Exception:
        pass


def clip(s, n=MAX_OUT):
    s = s if isinstance(s, str) else str(s)
    if RAW["full"]:
        return s
    return s if len(s) <= n else s[:n] + f"\n...[{len(s)-n} more chars - full text is in {SESSION_LOG}, or type /raw on]"


def http_get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def t_fetch(a):
    t = http_get(a["url"])
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return clip(re.sub(r"\s+", " ", html.unescape(t)).strip(), 4000)


def t_search(a):
    page = http_get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(a["query"]))
    out = []
    for href, title in re.findall(r'class="result__a"[^>]*href="(.*?)"[^>]*>(.*?)</a>', page, re.S)[:8]:
        m = re.search(r"uddg=([^&]+)", href)
        link = urllib.parse.unquote(m.group(1)) if m else href
        out.append(html.unescape(re.sub(r"<[^>]+>", "", title)).strip() + " - " + link)
    return "\n".join(out) or "No results."


def t_shell(a):
    p = subprocess.run(a["cmd"], shell=True, capture_output=True, text=True, timeout=180)
    out = f"exit={p.returncode}\n{p.stdout}{p.stderr}"
    logged = _maybe_log_scan(a["cmd"], out)
    if logged:
        out += f"\n[saved to {logged} and indexed in knowledge base]"
    return clip(out)


def t_root(a):
    p = subprocess.run(["su", "-c", a["cmd"]], capture_output=True, text=True, timeout=180)
    out = f"exit={p.returncode}\n{p.stdout}{p.stderr}"
    logged = _maybe_log_scan(a["cmd"], out)
    if logged:
        out += f"\n[saved to {logged} and indexed in knowledge base]"
    return clip(out)


SCAN_DIR = os.path.join(HOME_DIR, "notes", "scans")
_SCAN_TOOLS = ("nmap", "masscan", "gobuster", "nikto", "sqlmap", "hydra", "whatweb", "dirb", "ffuf", "wpscan")


def _maybe_log_scan(cmd, output):
    head = cmd.strip().split()[0] if cmd.strip() else ""
    tool = os.path.basename(head)
    if tool not in _SCAN_TOOLS:
        return None
    try:
        os.makedirs(SCAN_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_cmd = re.sub(r"[^a-zA-Z0-9_.-]+", "_", cmd.strip())[:60]
        fn = os.path.join(SCAN_DIR, f"{ts}_{tool}_{safe_cmd}.txt")
        with open(fn, "w") as f:
            f.write(f"# cmd: {cmd}\n# time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{output}")
        kb_learn(fn, domain="security")
        return fn
    except Exception:
        return None


_VERSION_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9._+-]{1,30})[\s/]v?(\d+(?:\.\d+){1,3})\b")


def _extract_services(text):
    seen, out = set(), []
    for m in _VERSION_RE.finditer(text):
        prod, ver = m.group(1), m.group(2)
        if prod.lower() in ("http", "https", "tcp", "udp", "ssl", "tls", "ip", "cve", "for", "report",
                            "scan", "on", "at", "nmap", "host", "port", "open", "closed", "filtered"):
            continue
        key = (prod.lower(), ver)
        if key in seen:
            continue
        seen.add(key)
        out.append((prod, ver))
    return out[:15]


def _cve_lookup_one(product, version, k=3):
    try:
        import urllib.request, urllib.parse
        q = urllib.parse.quote(f"{product} {version}")
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={q}&resultsPerPage={k}"
        req = urllib.request.Request(url, headers={"User-Agent": "omnix-ai"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        items = []
        for v in data.get("vulnerabilities", [])[:k]:
            c = v.get("cve", {})
            cid = c.get("id", "?")
            desc = next((d["value"] for d in c.get("descriptions", []) if d.get("lang") == "en"), "")
            sev = ""
            metrics = c.get("metrics", {})
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(key):
                    sev = str(metrics[key][0]["cvssData"].get("baseScore", ""))
                    break
            items.append(f"  {cid} (CVSS {sev or '?'}): {desc[:160]}")
        return items
    except Exception as e:
        return [f"  lookup failed: {e}"]


def _poc_check(cve_id):
    if not shutil.which("searchsploit"):
        return None
    try:
        r = subprocess.run(["searchsploit", "--cve", cve_id], capture_output=True, text=True, timeout=20)
        lines = [l for l in r.stdout.splitlines() if l.strip() and "---" not in l and "Exploit Title" not in l
                 and "Shellcodes" not in l and "No Results" not in l and "Papers" not in l]
        if not lines:
            return "no PoC in local exploitdb"
        titles = [l.split("|")[0].strip() for l in lines[:3] if "|" in l]
        return "PoC AVAILABLE (exploitdb): " + "; ".join(titles) if titles else "PoC AVAILABLE (exploitdb)"
    except Exception:
        return None


def t_cve_check(a):
    product, version = a.get("product"), a.get("version")
    text = a.get("text") or ""
    path = a.get("path")
    if path:
        try:
            text = open(resolve(path), errors="ignore").read()
        except Exception as e:
            return f"Could not read {path}: {e}"
    pairs = [(product, version)] if product and version else _extract_services(text)
    if not pairs:
        return "No product/version pairs given or detected. Pass {\"product\",\"version\"} or {\"text\"}/{\"path\"} with scan output."
    out = [f"CVE lookup for {len(pairs)} service(s) (NVD, informational only):"]
    poc_hint_shown = False
    for prod, ver in pairs:
        out.append(f"- {prod} {ver}:")
        items = _cve_lookup_one(prod, ver)
        out.extend(items)
        for it in items:
            m = re.search(r"(CVE-\d{4}-\d+)", it)
            if not m:
                continue
            poc = _poc_check(m.group(1))
            if poc:
                out.append(f"    -> {m.group(1)}: {poc}")
            elif not shutil.which("searchsploit") and not poc_hint_shown:
                out.append("    (install exploitdb/searchsploit to also check for public PoCs: pkg install exploitdb)")
                poc_hint_shown = True
    return clip("\n".join(out), 4000)


def t_python(a):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(a["code"])
    p = subprocess.run([sys.executable, f.name], capture_output=True, text=True, timeout=180)
    os.unlink(f.name)
    return clip(f"exit={p.returncode}\n{p.stdout}{p.stderr}")


def _ctx(path, line, n=4):
    try:
        L = open(path, errors="ignore").read().splitlines()
    except Exception:
        return ""
    lo, hi = max(0, line - 1 - n), min(len(L), line + n)
    return "\n".join(f"{'>>' if i + 1 == line else '  '} {i + 1}: {L[i]}" for i in range(lo, hi))


def _bad(msg):
    return bool(msg) and not msg.startswith("Lint")


def _syntax(path):
    p = os.path.expanduser(path)
    ext = os.path.splitext(p)[1].lower()
    try:
        if ext == ".py":
            try:
                compile(open(p).read(), p, "exec")
            except SyntaxError as e:
                return f"SyntaxError: {e.msg} (line {e.lineno})\n" + _ctx(p, e.lineno or 1)
            r = subprocess.run([sys.executable, "-m", "pyflakes", p], capture_output=True, text=True, timeout=30)
            if "No module named" not in r.stderr and r.stdout.strip():
                return "Lint warnings (undefined names, unused imports, etc.):\n" + clip(r.stdout, 900)
        elif ext == ".json":
            try:
                json.load(open(p))
            except json.JSONDecodeError as e:
                return f"JSON error: {e.msg} (line {e.lineno})\n" + _ctx(p, e.lineno)
        elif ext in (".sh", ".bash"):
            r = subprocess.run(["bash", "-n", p], capture_output=True, text=True, timeout=20)
            if r.returncode:
                return "Shell syntax error: " + r.stderr.strip()
        elif ext in (".js", ".mjs") and shutil.which("node"):
            r = subprocess.run(["node", "--check", p], capture_output=True, text=True, timeout=20)
            if r.returncode:
                return "JS syntax error:\n" + clip(r.stderr, 800)
    except Exception as e:
        return f"(check could not run: {e})"
    return ""


def _safe_write(path, new):
    p = os.path.expanduser(path)
    existed = os.path.exists(p)
    old = open(p, errors="ignore").read() if existed else None
    before = _syntax(p) if existed else ""
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    bk = None
    if existed:
        bk = os.path.join(BK_DIR, f"{int(time.time() * 1000)}__" + p.replace("/", "%"))
        shutil.copy(p, bk)
    open(p, "w").write(new)
    after = _syntax(p)
    if existed and _bad(after) and not _bad(before):
        open(p, "w").write(old)
        if bk:
            os.remove(bk)
        return "REVERTED: that change broke the syntax, so the file is unchanged.\n" + after + "\nFix it and try again."
    TOUCHED.add(p)
    if _bad(after):
        return f"Saved {p}, but it has a SYNTAX ERROR to fix:\n{after}"
    return f"Saved {p} ({len(new)} chars). Syntax OK." + (("\n" + after) if after else "")


_STEP = [0]
_SEEN = {}


def resolve(path):
    p = os.path.expanduser(str(path))
    if os.path.exists(p):
        return p
    name = os.path.basename(p.rstrip("/"))
    bases = [os.getcwd(), os.path.expanduser("~"), HOME_DIR, NOTES_DIR, KNOWLEDGE_DIR]
    for b in bases:
        c = os.path.join(b, p.lstrip("/"))
        if os.path.exists(c):
            return c
    found = []
    for b in bases:
        for root, dirs, files in os.walk(b):
            dirs[:] = [d for d in dirs if not d.startswith(".") or d == ".omnix_ai"]
            for f in files:
                if f == name:
                    found.append(os.path.join(root, f))
            if name in dirs:
                found.append(os.path.join(root, name))
            if len(found) >= 5:
                break
        if found:
            break
    if len(found) == 1:
        return found[0]
    if found:
        raise RuntimeError(f"File not found: {p}. Several matches, pick one: " + "; ".join(found))
    stem = os.path.splitext(name)[0][:8]
    raise RuntimeError(f"File not found: {p}. Do NOT guess paths. Run shell: find ~ -iname '*{stem}*' | head   "
                       f"(notes are in {NOTES_DIR}, knowledge in {KNOWLEDGE_DIR})")


def already_loaded(kind, p, extra=""):
    try:
        st = os.stat(p)
        key = (kind, p, st.st_mtime, st.st_size, extra)
    except OSError:
        return False
    last = _SEEN.get(key)
    _SEEN[key] = _STEP[0]
    return last is not None and _STEP[0] - last <= 6


LOADED_MSG = "Already loaded a moment ago and unchanged - its content is in the conversation above. Use it (or ask for a different range) instead of reading it again."


def t_write(a):
    return _safe_write(a["path"], a.get("content", ""))


def t_edit(a):
    p = resolve(a["path"])
    s = open(p).read()
    if a["old"] not in s:
        return "Edit failed: old text not found. Use view to see the exact text, or use patch_lines."
    return _safe_write(p, s.replace(a["old"], a["new"], 1))


def t_patch_lines(a):
    p = resolve(a["path"])
    L = open(p).read().split("\n")
    start = int(a["start"])
    end = int(a.get("end", start))
    if not (1 <= start <= end <= len(L)):
        return f"Bad range. File has {len(L)} lines."
    new = a.get("new", "")
    L[start - 1:end] = new.split("\n") if new != "" else []
    return _safe_write(p, "\n".join(L))


def t_view(a):
    p = resolve(a["path"])
    if already_loaded("view", p, f"{a.get('start')}-{a.get('end')}"):
        return LOADED_MSG
    L = open(p, errors="ignore").read().split("\n")
    s, e = int(a.get("start", 1)), int(a.get("end", min(len(L), int(a.get("start", 1)) + 79)))
    return clip(f"{p} ({len(L)} lines)\n" + "\n".join(f"{i}: {L[i-1]}" for i in range(max(1, s), min(len(L), e) + 1)), 4500)


def t_check(a):
    r = _syntax(a["path"])
    return r if r else "No problems found."


def t_debug(a):
    p = resolve(a["path"])
    runner = {".py": [sys.executable], ".js": ["node"], ".sh": ["bash"]}.get(os.path.splitext(p)[1].lower())
    if not runner:
        return "Unsupported file type (use .py, .js, .sh)."
    syn = _syntax(p)
    if _bad(syn):
        return "Fix the syntax first:\n" + syn
    try:
        r = subprocess.run(runner + [p] + shlex.split(a.get("args", "")), capture_output=True, text=True,
                           timeout=int(a.get("timeout", 60)), cwd=os.path.dirname(os.path.abspath(p)))
    except subprocess.TimeoutExpired:
        return "Timed out: the program is still running or waiting for input."
    out = f"exit={r.returncode}\n--- stdout\n{clip(r.stdout, 1200)}\n--- stderr\n{clip(r.stderr, 1500)}"
    frames = [(f, int(l)) for f, l in re.findall(r'File "([^"]+)", line (\d+)', r.stderr)
              if os.path.exists(f) and "site-packages" not in f and "/lib/python" not in f]
    if frames:
        f, l = frames[-1]
        out += f"\n--- failing code ({f}):\n" + _ctx(f, l)
    else:
        m = re.search(re.escape(os.path.basename(p)) + r":(\d+)", r.stderr)
        if m:
            out += "\n--- failing code:\n" + _ctx(p, int(m.group(1)))
    if r.returncode == 0 and not r.stderr.strip():
        out += "\nRan without errors."
    return clip(out, 4500)


CODE_EXT = {".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".java", ".kt", ".c", ".h", ".cpp",
            ".hpp", ".cs", ".go", ".rs", ".php", ".rb", ".lua", ".html", ".css", ".json", ".yml", ".yaml", ".sql"}
SKIP_DIRS = {"node_modules", "venv", "__pycache__", "build", "dist", "target", "site-packages"}
AUDIT_DIR = os.path.join(HOME_DIR, "audit")
BK_DIR = os.path.join(HOME_DIR, "filebackups")
for _d in (AUDIT_DIR, BK_DIR):
    os.makedirs(_d, exist_ok=True)
TOUCHED = set()
CHUNK, OVERLAP = 60, 6
AUDIT_MODEL = os.environ.get("AUDIT_MODEL", MODEL)

SYS_REVIEW = ("You are a meticulous code reviewer. Review ONLY the numbered lines you are given. Report REAL bugs: "
              "syntax errors, wrong logic, undefined names, off-by-one errors, division by zero, resource leaks, wrong "
              "types, unsafe operations. Do NOT report style or naming. For each bug quote the EXACT text of the "
              "offending line. Reply with JSON only: "
              '{"issues":[{"line":<number>,"code":"<exact text of that line>","problem":"<short>","fix":"<the corrected full line, or empty>"}]}'
              ' If there are no bugs reply {"issues":[]}.')


def _collect(root):
    root = os.path.expanduser(root)
    if os.path.isfile(root):
        return [root]
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for f in files:
            p = os.path.join(d, f)
            if os.path.splitext(f)[1].lower() not in CODE_EXT:
                continue
            try:
                if os.path.getsize(p) > 2_000_000:
                    continue
                with open(p, errors="ignore") as fh:
                    if any(len(fh.readline()) > 1500 for _ in range(5)):
                        continue
            except Exception:
                continue
            out.append(p)
    return sorted(out)


def _py_static(src):
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"line": e.lineno or 1, "problem": f"SyntaxError: {e.msg}", "fix": ""}]
    out = []

    def add(node, msg):
        out.append({"line": getattr(node, "lineno", 1), "problem": msg, "fix": ""})

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in list(node.args.defaults) + [x for x in node.args.kw_defaults if x]:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    add(d, f"mutable default argument in {node.name}() is shared between calls")
        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                add(node, "bare 'except:' hides every error")
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                add(node, "exception silently swallowed (except ...: pass)")
        elif isinstance(node, ast.Compare):
            for op, c in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(c, ast.Constant) and c.value is None:
                    add(node, "comparison to None with ==/!=, use 'is None'")
                if (isinstance(op, (ast.Is, ast.IsNot)) and isinstance(c, ast.Constant)
                        and isinstance(c.value, (str, int, float)) and not isinstance(c.value, bool)):
                    add(node, "'is' used with a literal, use ==")
        elif isinstance(node, ast.Assert) and isinstance(node.test, ast.Tuple) and node.test.elts:
            add(node, "assert on a tuple is always true")
        elif (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
              and isinstance(node.value, ast.Name) and node.targets[0].id == node.value.id):
            add(node, "self-assignment has no effect")
        for field in ("body", "orelse", "finalbody"):
            body = getattr(node, field, None)
            if isinstance(body, list):
                for i, st in enumerate(body[:-1]):
                    if isinstance(st, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                        add(body[i + 1], "unreachable code after return/raise/break/continue")
                        break
        if isinstance(node, (ast.Module, ast.ClassDef)):
            seen = {}
            for st in node.body:
                if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if st.name in seen and not st.decorator_list:
                        add(st, f"function '{st.name}' redefined (first defined at line {seen[st.name]})")
                    seen[st.name] = st.lineno
    return out


def _pyflakes(files):
    res = {}
    for i in range(0, len(files), 40):
        r = subprocess.run([sys.executable, "-m", "pyflakes"] + files[i:i + 40], capture_output=True, text=True, timeout=300)
        if "No module named" in r.stderr:
            return None
        for ln in r.stdout.splitlines():
            m = re.match(r"(.+?):(\d+):(?:\d+:?)? (.*)", ln)
            if m:
                res.setdefault(m.group(1), []).append({"line": int(m.group(2)), "problem": "pyflakes: " + m.group(3), "fix": ""})
    return res


def _outline(path, src, lines):
    items = []
    if path.endswith(".py"):
        try:
            for n in ast.walk(ast.parse(src)):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    items.append((n.lineno, f"{n.name}({n.lineno}-{getattr(n, 'end_lineno', n.lineno)})"))
        except SyntaxError:
            pass
    else:
        for i, l in enumerate(lines, 1):
            m = re.match(r"\s*(?:export\s+)?(?:async\s+)?(?:def|class|function|func|fn)\s+(\w+)", l)
            if m:
                items.append((i, f"{m.group(1)}({i})"))
    return clip(", ".join(x for _, x in sorted(items)), 500) or "(none)"


def _chunks(lines):
    n, out, s = len(lines), [], 1
    while s <= n:
        e = min(s + CHUNK - 1, n)
        if e < n:
            for k in range(e, max(s + 20, e - 15), -1):
                if not lines[k - 1].strip():
                    e = k
                    break
        out.append([s, e, False])
        if e >= n:
            break
        s = max(e - OVERLAP + 1, s + 1)
    return out


def _llm_json(system, user):
    body = {"model": AUDIT_MODEL, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0, "num_ctx": 4096}}
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        raw = json.load(r)["message"]["content"]
    return json.JSONDecoder().raw_decode(raw[raw.find("{"):])[0]


def _review_chunk(rel, outline, lines, s, e, is_py):
    numbered = "\n".join(f"{i}: {lines[i - 1]}" for i in range(s, e + 1))
    d = _llm_json(SYS_REVIEW, f"File: {rel}\nFile outline: {outline}\nLines {s}-{e}:\n{numbered}")
    found = []
    for it in (d.get("issues") or [])[:6]:
        try:
            ln, code = int(it["line"]), str(it.get("code", ""))
            prob, fix = str(it.get("problem", "")).strip(), str(it.get("fix") or "")
        except Exception:
            continue
        if not (s <= ln <= e) or not prob:
            continue
        actual = lines[ln - 1]
        a, c = " ".join(actual.split()), " ".join(code.split())
        if len(c) < 3 or not a or not (c in a or a in c):
            continue
        fixline = ""
        if fix and "\n" not in fix.strip() and " ".join(fix.split()) != a:
            cand = fix if fix[:1] in (" ", "\t") else actual[:len(actual) - len(actual.lstrip())] + fix.strip()
            if is_py:
                try:
                    compile("\n".join(lines[:ln - 1] + [cand] + lines[ln:]), "x", "exec")
                    fixline = cand
                except SyntaxError:
                    fixline = ""
            else:
                fixline = cand
        found.append({"line": ln, "problem": prob[:200], "fix": fixline})
    return found


def _save(st):
    json.dump(st, open(os.path.join(AUDIT_DIR, st["id"] + ".json"), "w"))
    open(os.path.join(AUDIT_DIR, "latest"), "w").write(st["id"])


def _load(aid=None):
    try:
        aid = aid or open(os.path.join(AUDIT_DIR, "latest")).read().strip()
        return json.load(open(os.path.join(AUDIT_DIR, aid + ".json")))
    except Exception:
        return None


def _add_finding(st, path, f, kind):
    if any(x["file"] == path and x["line"] == f["line"] and (x["problem"] == f["problem"] or kind == "model")
           for x in st["findings"]):
        return False
    st["findings"].append({"id": st["nid"], "file": path, "line": f["line"], "kind": kind,
                           "problem": f["problem"], "fix": f.get("fix", ""), "status": "open"})
    st["nid"] += 1
    return True


def _audit_start(path):
    files = _collect(path)
    if not files:
        return None
    st = {"id": time.strftime("%Y%m%d_%H%M%S"), "root": os.path.expanduser(path), "files": [], "findings": [], "nid": 1}
    py = [f for f in files if f.endswith(".py")]
    pf = _pyflakes(py) if py else None
    total = 0
    for p in files:
        try:
            src = open(p, errors="ignore").read()
        except Exception:
            continue
        lines = src.split("\n")
        total += len(lines)
        st["files"].append({"path": p, "n": len(lines), "chunks": _chunks(lines), "py": p.endswith(".py")})
        if p.endswith(".py"):
            stat = _py_static(src) + (pf or {}).get(p, [])
        else:
            msg = _syntax(p)
            m = re.search(r"line (\d+)", msg)
            stat = [{"line": int(m.group(1)) if m else 1, "problem": msg.splitlines()[0], "fix": ""}] if _bad(msg) else []
        for f in stat:
            _add_finding(st, p, f, "static")
    st["lines"] = total
    st["pyflakes"] = pf is not None
    _save(st)
    return st


def _coverage(st):
    done = tot = 0
    for f in st["files"]:
        tot += f["n"]
        cur = 0
        for s, e in sorted((c[0], c[1]) for c in f["chunks"] if c[2]):
            s = max(s, cur + 1)
            if e >= s:
                done += e - s + 1
                cur = e
    return done, tot


def _pending(st):
    return sum(1 for f in st["files"] for c in f["chunks"] if not c[2])


def _audit_next(st, count, progress=None):
    n = new = 0
    base = st["root"] if os.path.isdir(st["root"]) else os.path.dirname(st["root"])
    allc = sum(len(f["chunks"]) for f in st["files"])
    for f in st["files"]:
        todo = [c for c in f["chunks"] if not c[2]]
        if not todo:
            continue
        src = open(f["path"], errors="ignore").read()
        lines = src.split("\n")
        outline = _outline(f["path"], src, lines)
        rel = os.path.relpath(f["path"], base)
        for c in todo:
            try:
                iss = _review_chunk(rel, outline, lines, c[0], c[1], f["py"])
            except Exception as e:
                return n, new, f"model error: {e} (is ollama running?)"
            for it in iss:
                new += _add_finding(st, f["path"], it, "model")
            c[2] = True
            n += 1
            _save(st)
            if progress:
                progress(allc - _pending(st), allc, rel, c[0], c[1], len(st["findings"]))
            if n >= count:
                return n, new, ""
    return n, new, ""


def _sev(f):
    p = f["problem"].lower()
    if "syntax" in p:
        return 0
    if "undefined name" in p:
        return 1
    if f["kind"] == "model":
        return 2
    if any(k in p for k in ("mutable default", "bare 'except", "swallowed", "unreachable", "redefined", "'is' used", "tuple")):
        return 3
    return 4


def _fmt(f):
    return (f"#{f['id']} {f['file']}:{f['line']} [{f['kind']}] {f['problem']}"
            + (f"\n     fix: {f['fix'].strip()}" if f["fix"] else ""))


def t_audit(a, auto):
    act = a.get("action", "")
    if act == "start":
        st = _audit_start(resolve(a["path"]))
        if not st:
            return "No source files found there."
        chunks = sum(len(f["chunks"]) for f in st["files"])
        sev = sum(1 for f in st["findings"] if _sev(f) <= 1)
        return (f"Audit {st['id']}: {len(st['files'])} files, {st['lines']} lines, {chunks} chunks to review.\n"
                f"Static scan already found {len(st['findings'])} issues ({sev} syntax/undefined-name)."
                + ("" if st["pyflakes"] else " (pip install pyflakes adds undefined-name detection.)")
                + "\nNext: audit next (8 chunks per call), or run /audit in the terminal to do everything.")
    st = _load(a.get("audit_id"))
    if not st:
        return "No audit yet. Use audit start with a path."
    done, tot = _coverage(st)
    head = f"Reviewed {done} of {tot} lines ({100 * done // max(tot, 1)}%), {_pending(st)} chunks left, {len(st['findings'])} findings."
    if act == "status":
        return head
    if act == "next":
        n, new, err = _audit_next(st, int(a.get("chunks", 8)))
        done, tot = _coverage(st)
        return (f"Processed {n} chunks, {new} new model findings. Reviewed {done}/{tot} lines, {_pending(st)} chunks left."
                + (f"\n{err}" if err else "") + ("\nAll lines reviewed. Run audit report." if not _pending(st) else ""))
    if act == "report":
        op = sorted((f for f in st["findings"] if f["status"] == "open"), key=lambda f: (_sev(f), f["file"], f["line"]))
        full = head + "\n\n" + "\n".join(_fmt(f) for f in op)
        open(os.path.expanduser("~/audit_report.md"), "w").write(full)
        lim = int(a.get("limit", 20))
        return clip(head + f"\nShowing {min(lim, len(op))} of {len(op)} open (full list: ~/audit_report.md)\n\n"
                    + "\n".join(_fmt(f) for f in op[:lim]), 4500)
    fid = int(a["id"]) if str(a.get("id", "")).isdigit() else None
    f = next((x for x in st["findings"] if x["id"] == fid), None)
    if act in ("show", "fix", "skip"):
        if not f:
            return "Give the finding number as id."
        if act == "show":
            return _fmt(f) + "\n" + _ctx(f["file"], f["line"], 6)
        if act == "skip":
            f["status"] = "skipped"
            _save(st)
            return "Skipped."
        if not f["fix"]:
            return "No automatic fix for this one. Use view and patch_lines."
        L = open(f["file"], errors="ignore").read().split("\n")
        old = "\n".join(L)
        L[f["line"] - 1] = f["fix"]
        new = "\n".join(L)
        diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "before", "after", n=2))
        if not approve(f"APPLY FIX #{f['id']} in {f['file']}\n{f['problem']}\n{clip(diff, 1200)}", auto):
            return "User denied."
        r = _safe_write(f["file"], new)
        if r.startswith("Saved") and "SYNTAX" not in r:
            f["status"] = "fixed"
            _save(st)
        return r
    return "Unknown audit action. Use: start{path}, next{chunks?}, status, report{limit?}, show{id}, fix{id}, skip{id}."


def audit_cli(arg):
    auto = {"on": False}
    if arg in ("status", "report"):
        print(t_audit({"action": arg}, auto))
        return
    if arg in ("", "resume"):
        st = _load()
        if not st:
            print("Usage: /audit <path>")
            return
    else:
        print("Scanning...")
        st = _audit_start(arg)
        if not st:
            print("No source files found.")
            return
        print(f"{len(st['files'])} files, {st['lines']} lines, {len(st['findings'])} static findings. "
              "Reviewing every chunk with the model (Ctrl-C to pause, /audit resume to continue).")

    def prog(done, total, rel, s, e, nf):
        print(f"  [{done}/{total}] {rel}:{s}-{e}  findings so far: {nf}", flush=True)

    try:
        while _pending(st):
            n, new, err = _audit_next(st, 1, prog)
            if err:
                print(err)
                return
    except KeyboardInterrupt:
        print("\nPaused. /audit resume to continue.")
        return
    done, tot = _coverage(st)
    print(f"\nDone: reviewed {done}/{tot} lines.\n" + t_audit({"action": "report", "limit": 15}, auto))
    print("\nThen tell me: 'fix audit findings' (or use audit fix with an id).")


def t_verify(a, auto):
    if not TOUCHED:
        return "No files were modified this session."
    problems = []
    for p in sorted(TOUCHED):
        if os.path.exists(p):
            r = _syntax(p)
            if _bad(r):
                problems.append(f"{p}:\n{r}")
    cmd = a.get("test_cmd")
    if cmd:
        if not approve("run tests: " + cmd, auto):
            return "User denied the test run."
        out = t_shell({"cmd": cmd})
        if not out.startswith("exit=0"):
            problems.append("Tests failed:\n" + out)
    if problems:
        return "NOT READY:\n" + clip("\n\n".join(problems), 3500)
    return (f"READY: {len(TOUCHED)} modified file(s) pass syntax checks"
            + (" and the tests pass." if cmd else ". No tests were run (pass test_cmd to run them)."))


def t_undo(a):
    p = os.path.expanduser(a["path"])
    key = "__" + p.replace("/", "%")
    files = sorted(f for f in os.listdir(BK_DIR) if f.endswith(key))
    if not files:
        return "No backup for that file."
    shutil.copy(os.path.join(BK_DIR, files[-1]), p)
    os.remove(os.path.join(BK_DIR, files[-1]))
    return f"Restored {p} from backup."


def t_nano(a):
    p = os.path.expanduser(a["path"])
    if not shutil.which("nano"):
        return "nano is not installed. Run: pkg install nano"
    if not sys.stdin.isatty():
        return "No interactive terminal available."
    subprocess.run(["nano"] + ([f"+{int(a['line'])}"] if a.get("line") else []) + [p])
    TOUCHED.add(p)
    chk = _syntax(p)
    return "nano closed. " + (chk if chk else "Syntax OK.")


def _proposed(name, a):
    try:
        p = os.path.expanduser(a["path"])
        if not os.path.exists(p):
            return ""
        old = open(p, errors="ignore").read()
        if name == "write_file":
            new = a.get("content", "")
        elif name == "edit_file":
            if a["old"] not in old:
                return ""
            new = old.replace(a["old"], a["new"], 1)
        else:
            L = old.split("\n")
            s = int(a["start"])
            e = int(a.get("end", s))
            if not (1 <= s <= e <= len(L)):
                return ""
            n = a.get("new", "")
            L[s - 1:e] = n.split("\n") if n != "" else []
            new = "\n".join(L)
        return "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "before", "after", n=2))
    except Exception:
        return ""


def _desc(name, a, base):
    d = _proposed(name, a)
    return base + ("\n" + clip(d, 1500) if d else "")


STUDY_DIR = os.path.join(HOME_DIR, "study")
NOTES_DIR = os.path.join(HOME_DIR, "notes")
for _d in (STUDY_DIR, NOTES_DIR):
    os.makedirs(_d, exist_ok=True)
STUDY_MODEL = os.environ.get("AUDIT_MODEL", MODEL)
DOC_WORDS, DOC_OVERLAP_WORDS = 550, 60

SYS_STUDY = ("You are reading a document chunk by chunk to build study notes. You are given the running notes so "
             "far (may be empty) and the next chunk of text. Update the notes: add new facts, arguments, names, "
             "numbers, and definitions from this chunk; do not repeat what is already noted; do not summarize chunk "
             "by chunk, instead fold new information into the existing notes as organized bullet points under "
             "relevant headings. Keep it factual and concise. Reply with JSON only: "
             '{"notes":"<the full updated notes in markdown>"}')


def _extract_pdf(p):
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    try:
        import pypdf
        t = "\n\n".join((pg.extract_text() or "") for pg in pypdf.PdfReader(p).pages)
        if t.strip():
            return t
    except ImportError:
        if not shutil.which("pdftotext"):
            raise RuntimeError("Can't read PDFs yet. Run: pkg install poppler   (or: pip install pypdf --break-system-packages)")
    return _ocr_pdf(p)


def _ocr_pdf(p, max_pages=300):
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        raise RuntimeError("This PDF is scanned images. For OCR run: pkg install poppler tesseract")
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run(["pdftoppm", "-r", "150", "-l", str(max_pages), "-png", p, os.path.join(tmp, "pg")],
                       capture_output=True, timeout=1800)
        out = []
        for f in sorted(os.listdir(tmp)):
            r = subprocess.run(["tesseract", os.path.join(tmp, f), "stdout"], capture_output=True, text=True, timeout=300)
            out.append(r.stdout)
        return "\n\n".join(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _extract_pptx(p):
    with zipfile.ZipFile(p) as z:
        names = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                       key=lambda n: int(re.findall(r"\d+", n)[-1]))
        parts = []
        for n in names:
            x = z.read(n).decode("utf-8", "ignore")
            x = re.sub(r"</a:p>", "\n", x)
            parts.append(html.unescape(re.sub(r"<[^>]+>", "", x)))
    return "\n\n".join(parts)


def _extract_odt(p):
    with zipfile.ZipFile(p) as z:
        x = z.read("content.xml").decode("utf-8", "ignore")
    x = re.sub(r"</text:(p|h)>", "\n", x)
    return html.unescape(re.sub(r"<[^>]+>", "", x))


def _extract_rtf(p):
    t = open(p, errors="ignore").read()
    t = re.sub(r"\\par[d]?", "\n", t)
    t = re.sub(r"\\'[0-9a-f]{2}", "", t)
    t = re.sub(r"\\[a-z]+-?\d* ?|[{}]", "", t)
    return t


def _extract_docx(p):
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^/]*/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return html.unescape(text)


def _extract_epub(p):
    with zipfile.ZipFile(p) as z:
        opf_path = None
        try:
            cxml = z.read("META-INF/container.xml").decode("utf-8", "ignore")
            opf_path = re.search(r'full-path="([^"]+)"', cxml).group(1)
        except Exception:
            pass
        if not opf_path:
            opf_path = next((n for n in z.namelist() if n.endswith(".opf")), None)
        if not opf_path:
            raise RuntimeError("Not a valid EPUB (no .opf manifest found).")
        base = os.path.dirname(opf_path)
        opf = z.read(opf_path).decode("utf-8", "ignore")
        ids = dict(re.findall(r'<item[^>]*id="([^"]+)"[^>]*href="([^"]+)"[^>]*media-type="application/xhtml\+xml"', opf))
        ids.update(dict(re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"[^>]*media-type="application/xhtml\+xml"', opf)))
        order = re.findall(r'<itemref[^>]*idref="([^"]+)"', opf)
        hrefs = re.findall(r'<item[^>]+href="([^"]+)"[^>]+id="([^"]+)"', opf) + re.findall(r'<item[^>]+id="([^"]+)"[^>]+href="([^"]+)"', opf)
        id2href = {}
        for m in re.finditer(r"<item\b[^>]*>", opf):
            tag = m.group(0)
            idm, hm, tm = re.search(r'id="([^"]+)"', tag), re.search(r'href="([^"]+)"', tag), re.search(r'media-type="([^"]+)"', tag)
            if idm and hm and tm and "html" in tm.group(1):
                id2href[idm.group(1)] = hm.group(1)
        parts = []
        seq = order if order else list(id2href.keys())
        for item_id in seq:
            href = id2href.get(item_id)
            if not href:
                continue
            path = os.path.normpath(os.path.join(base, href)).replace("\\", "/")
            try:
                raw = z.read(path).decode("utf-8", "ignore")
            except KeyError:
                continue
            raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw)
            raw = re.sub(r"(?i)</p>|</div>|<br\s*/?>", "\n", raw)
            parts.append(html.unescape(re.sub(r"<[^>]+>", " ", raw)))
        return "\n\n".join(parts)


TEXT_EXT = {".txt", ".md", ".markdown", ".csv", ".tsv", ".log", ".rst", ".json", ".jsonl", ".yaml", ".yml",
            ".toml", ".ini", ".cfg", ".xml", ".tex", ".py", ".js", ".ts", ".sh", ".java", ".c", ".h", ".cpp",
            ".go", ".rs", ".php", ".rb", ".sql", ".css"}


def _extract(path):
    p = os.path.expanduser(path)
    if not os.path.exists(p):
        raise RuntimeError("File not found: " + p)
    ext = os.path.splitext(p)[1].lower()
    if ext == ".pdf":
        text = _extract_pdf(p)
    elif ext == ".docx":
        text = _extract_docx(p)
    elif ext == ".epub":
        text = _extract_epub(p)
    elif ext in TEXT_EXT:
        text = open(p, errors="ignore").read()
    elif ext == ".pptx":
        text = _extract_pptx(p)
    elif ext == ".odt":
        text = _extract_odt(p)
    elif ext == ".rtf":
        text = _extract_rtf(p)
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"):
        if not shutil.which("tesseract"):
            raise RuntimeError("Reading images needs OCR. Run: pkg install tesseract")
        text = subprocess.run(["tesseract", p, "stdout"], capture_output=True, text=True, timeout=300).stdout
    elif ext == ".html" or ext == ".htm":
        raw = open(p, errors="ignore").read()
        raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw)
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    elif ext == ".doc":
        raise RuntimeError("Old .doc format isn't supported, only .docx. Convert it first (e.g. with LibreOffice) if you have it.")
    else:
        raise RuntimeError(f"Unsupported file type '{ext}'. Supported: pdf, docx, pptx, odt, rtf, epub, html, images (OCR), "
                           "and text/code/data files.")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise RuntimeError("No extractable text found (the file may be scanned images with no OCR layer).")
    return text


def t_read_doc(a):
    a = dict(a, path=resolve(a["path"]))
    if already_loaded("doc", a["path"], f"{a.get('start_word')}-{a.get('end_word')}"):
        return LOADED_MSG
    text = _extract(a["path"])
    words = text.split()
    start = int(a.get("start_word", 1))
    end = int(a.get("end_word", start + 2500))
    chunk = " ".join(words[start - 1:end])
    more = f"\n\n[{len(words) - end} more words — call again with start_word={end+1} to continue]" if end < len(words) else "\n\n[end of document]"
    return clip(f"{os.path.basename(a['path'])}: {len(words)} words total.\n\n{chunk}{more}", 6000)


def _word_chunks(words):
    n, out, s = len(words), [], 0
    while s < n:
        e = min(s + DOC_WORDS, n)
        out.append([s, e, False])
        if e >= n:
            break
        s = e - DOC_OVERLAP_WORDS
    return out


def _llm_notes(system, user, model):
    body = {"model": model, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0.1, "num_ctx": 4096}}
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        raw = json.load(r)["message"]["content"]
    d = json.JSONDecoder().raw_decode(raw[raw.find("{"):])[0]
    return str(d.get("notes", "")).strip()


def _study_save(st):
    json.dump(st, open(os.path.join(STUDY_DIR, st["id"] + ".json"), "w"))
    open(os.path.join(STUDY_DIR, "latest"), "w").write(st["id"])


def _study_load(sid=None):
    try:
        sid = sid or open(os.path.join(STUDY_DIR, "latest")).read().strip()
        return json.load(open(os.path.join(STUDY_DIR, sid + ".json")))
    except Exception:
        return None


def _notes_path(st):
    base = re.sub(r"[^\w.-]+", "_", os.path.basename(st["path"]))[:60]
    return os.path.join(NOTES_DIR, f"{st['id']}_{base}.md")


def t_study(a, auto):
    act = a.get("action", "")
    if act == "start":
        text = _extract(a["path"])
        words = text.split()
        st = {"id": time.strftime("%Y%m%d_%H%M%S"), "path": os.path.expanduser(a["path"]), "words": words,
              "chunks": _word_chunks(words), "notes": ""}
        _study_save(st)
        try:
            kb_learn(st["path"])
        except Exception:
            pass
        return (f"Study {st['id']}: {os.path.basename(st['path'])}, {len(words)} words, "
                f"{len(st['chunks'])} chunks to read.\nNext: study next (reads a few chunks and builds notes), "
                "or run /study in the terminal to read the whole thing.")
    st = _study_load(a.get("study_id"))
    if not st:
        return "No study session yet. Use study start with a path."
    done = sum(1 for c in st["chunks"] if c[2])
    head = f"Read {done} of {len(st['chunks'])} chunks ({100*done//max(len(st['chunks']),1)}%)."
    if act == "status":
        return head + f" {len(st['notes'].split())} words of notes so far."
    if act == "next":
        n, err = 0, ""
        count = int(a.get("chunks", 3))
        for c in st["chunks"]:
            if c[2]:
                continue
            chunk_text = " ".join(st["words"][c[0]:c[1]])
            try:
                st["notes"] = _llm_notes(SYS_STUDY, f"NOTES SO FAR:\n{st['notes'] or '(empty)'}\n\nNEXT CHUNK:\n{chunk_text}", STUDY_MODEL) or st["notes"]
            except Exception as e:
                err = f"model error: {e} (is ollama running?)"
                break
            c[2] = True
            n += 1
            _study_save(st)
            if n >= count:
                break
        done = sum(1 for c in st["chunks"] if c[2])
        r = f"Read {n} more chunks. {done}/{len(st['chunks'])} total." + (f"\n{err}" if err else "")
        if done >= len(st["chunks"]):
            p = _notes_path(st)
            open(p, "w").write(f"# Notes: {os.path.basename(st['path'])}\n\n" + st["notes"])
            r += f"\nFinished the whole document. Notes saved to {p}"
            try:
                kb_add_many([("notes:" + st["id"], "Notes on " + os.path.basename(st["path"]), "notes", "",
                              st["notes"], "general")])
                r += "\nNotes are now in the knowledge base (use recall to search them)."
            except Exception:
                pass
        return r
    if act == "notes":
        return clip(st["notes"], 5500) or "No notes yet, call study next first."
    if act == "remember_all":
        if not approve(f"save all study notes ({len(st['notes'].split())} words) to long-term memory", auto):
            return "User denied."
        name = os.path.basename(st["path"])
        kb_add_many([("notes:" + st["id"], "Notes on " + name, "notes", "", st["notes"], "general")])
        open(MEM, "a").write(f"\n[Studied '{name}': {len(st['notes'].split())} words of notes are in the knowledge base. Use recall to look things up.]\n")
        return "Saved to the knowledge base (searchable with recall) and a pointer added to long-term memory."
    return "Unknown study action. Use: start{path}, next{chunks?}, status, notes, remember_all."


def study_cli(arg):
    auto = {"on": False}
    if arg in ("status", "notes"):
        print(t_study({"action": arg}, auto))
        return
    if arg in ("", "resume"):
        st = _study_load()
        if not st:
            print("Usage: /study <path to pdf/docx/epub/txt>")
            return
    else:
        print("Extracting text...")
        try:
            t_study({"action": "start", "path": arg}, auto)
        except Exception as e:
            print("Error:", e)
            return
        st = _study_load()
        print(f"{len(st['chunks'])} chunks. Reading and taking notes (Ctrl-C to pause, /study resume to continue).")
    try:
        while True:
            st = _study_load()
            if all(c[2] for c in st["chunks"]):
                break
            r = t_study({"action": "next", "chunks": 1}, auto)
            done = sum(1 for c in _study_load()["chunks"] if c[2])
            print(f"  [{done}/{len(st['chunks'])}] notes: {len(_study_load()['notes'].split())} words", flush=True)
            if "model error" in r:
                print(r)
                return
    except KeyboardInterrupt:
        print("\nPaused. /study resume to continue.")
        return
    print("\nDone.\n" + t_study({"action": "status"}, auto))
    print("Tell me 'remember the study notes' to add them to long-term memory, or ask me questions about it.")


import math
from collections import Counter

KB_DIR = os.path.join(HOME_DIR, "kb")
KB_CHUNKS = os.path.join(KB_DIR, "chunks.jsonl")
KB_SOURCES = os.path.join(KB_DIR, "sources.json")
os.makedirs(KB_DIR, exist_ok=True)
KB_WORDS, KB_OVERLAP = 220, 40
KB_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".cache", ".venv", "venv"}
KB_KINDS_EXT = TEXT_EXT | {".pdf", ".docx", ".pptx", ".odt", ".rtf", ".epub", ".html", ".htm",
                           ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
KB_STOP = set("the a an and or of to in is it that for on with as are was be this by at from i you we they what "
              "how why when who which do does did can could should would about please me my your".split())
_KB = {"sig": None, "docs": [], "chunks": [], "df": {}, "avg": 1.0}


def _tok(s):
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w
            for w in re.findall(r"\w+", s.lower()) if len(w) > 1 and w not in KB_STOP]


def _kb_sources():
    try:
        return json.load(open(KB_SOURCES))
    except Exception:
        return {}


def _kb_read():
    out = []
    try:
        for line in open(KB_CHUNKS):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    except FileNotFoundError:
        pass
    return out


def kb_add_many(entries):
    chunks, srcs = _kb_read(), _kb_sources()
    keys = {e[0] for e in entries}
    chunks = [c for c in chunks if c["s"] not in keys]
    for key, title, kind, sig, text, domain in entries:
        words = text.split()
        n, s = 0, 0
        while s < len(words):
            e = min(s + KB_WORDS, len(words))
            chunks.append({"s": key, "i": n, "w": s, "t": " ".join(words[s:e])})
            n += 1
            if e >= len(words):
                break
            s = e - KB_OVERLAP
        srcs[key] = {"title": title, "kind": kind, "sig": sig, "words": len(words), "chunks": n,
                     "domain": domain, "added": time.strftime("%Y-%m-%d")}
    with open(KB_CHUNKS + ".tmp", "w") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    os.replace(KB_CHUNKS + ".tmp", KB_CHUNKS)
    json.dump(srcs, open(KB_SOURCES + ".tmp", "w"))
    os.replace(KB_SOURCES + ".tmp", KB_SOURCES)


def _kb_load():
    try:
        st = os.stat(KB_CHUNKS)
        sig = (st.st_mtime_ns, st.st_size)
    except FileNotFoundError:
        return _KB
    if _KB["sig"] != sig:
        chunks = _kb_read()
        docs, df = [], Counter()
        for c in chunks:
            tf = Counter(_tok(c["t"]))
            docs.append((tf, sum(tf.values()) or 1))
            df.update(tf.keys())
        _KB.update(sig=sig, chunks=chunks, docs=docs, df=df,
                   avg=(sum(d[1] for d in docs) / len(docs)) if docs else 1.0)
    return _KB


def kb_search(q, k=5):
    L = _kb_load()
    N = len(L["docs"])
    qt = list(dict.fromkeys(_tok(q)))
    if not N or not qt:
        return []
    scored = []
    for idx, (tf, ln) in enumerate(L["docs"]):
        sc, hit = 0.0, 0
        for t in qt:
            f = tf.get(t, 0)
            if f:
                hit += 1
                d = L["df"].get(t, 0)
                sc += math.log(1 + (N - d + 0.5) / (d + 0.5)) * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * ln / L["avg"]))
        if sc > 0:
            scored.append((sc, hit / len(qt), idx))
    scored.sort(reverse=True)
    return [(sc, cov, L["chunks"][i]) for sc, cov, i in scored[:k]]


def _domain_for(f, root_hint=None):
    base = root_hint or KNOWLEDGE_DIR
    try:
        rel = os.path.relpath(f, base)
    except ValueError:
        return "general"
    parts = rel.split(os.sep)
    return parts[0] if len(parts) > 1 and not parts[0].startswith("..") else "general"


def kb_learn(path, force=False, domain=None):
    p = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(p):
        return "Not found: " + p
    files = []
    if os.path.isdir(p):
        for root, dirs, fs in os.walk(p):
            dirs[:] = sorted(d for d in dirs if d not in KB_SKIP_DIRS and not d.startswith("."))
            for f in sorted(fs):
                if os.path.splitext(f)[1].lower() in KB_KINDS_EXT and not f.startswith("."):
                    files.append(os.path.join(root, f))
        files = files[:500]
    else:
        files = [p]
    srcs, entries, skipped, failed = _kb_sources(), [], 0, []
    for f in files:
        try:
            stt = os.stat(f)
            sig = f"{stt.st_size}:{int(stt.st_mtime)}"
            if not force and srcs.get(f, {}).get("sig") == sig:
                skipped += 1
                continue
            if stt.st_size > 80 * 1024 * 1024:
                failed.append(f"{os.path.basename(f)}: too big")
                continue
            dom = domain or _domain_for(f, p if os.path.isdir(p) else None)
            entries.append((f, os.path.basename(f), os.path.splitext(f)[1].lower().lstrip("."), sig, _extract(f), dom))
        except Exception as e:
            failed.append(f"{os.path.basename(f)}: {e}")
    if entries:
        kb_add_many(entries)
    words = sum(len(e[4].split()) for e in entries)
    r = f"Learned {len(entries)} file(s), {words} words. Skipped {skipped} unchanged."
    if failed:
        r += f"\n{len(failed)} failed: " + "; ".join(failed[:5])
    return r + "\nUse recall {query} to look things up."


KNOWLEDGE_DIR = os.path.join(HOME_DIR, "knowledge")
KNOWLEDGE_DOMAINS = ["security", "allopathy", "ayurveda", "homeopathy", "dictionary", "general"]

TERMUX_KALI_CHEATSHEET = """Termux & Kali reference (general command syntax, for authorized labs/CTFs/your own systems only)

TERMUX BASICS
- Update packages: pkg update && pkg upgrade -y
- Install/search/remove: pkg install <name> | pkg search <name> | pkg uninstall <name>
- Termux home is sandboxed: ~ = /data/data/com.termux/files/home. Shared phone storage needs: termux-setup-storage (creates ~/storage/...)
- Root (if the device is rooted and a root manager grants Termux access): su -c "<cmd>", or install tsu (pkg install tsu) then plain "sudo <cmd>"
- Background services / keeping Termux alive: termux-wake-lock ... termux-wake-unlock, or the Termux:Boot / Termux:API companion apps
- Useful companion packages: termux-api (sensors, clipboard, TTS/STT, notifications), openssh, tmux, proot-distro, git, python, nodejs, golang

RUNNING KALI INSIDE TERMUX (via proot-distro - no root required)
1. pkg install proot-distro
2. proot-distro install kali
3. proot-distro login kali
4. Inside the chroot: apt update && apt install -y kali-tools-top10
   Metapackages: kali-tools-top10, kali-tools-information-gathering, kali-tools-web, kali-tools-passwords,
   kali-tools-wireless (wireless tools usually need a USB adapter in monitor mode; most phone Wi-Fi chips cannot do this)
5. Exit the chroot with "exit"; re-enter any time with proot-distro login kali
Notes: proot-distro is NOT real virtualization - no raw sockets/packet injection in many cases, systemd/services generally
don't run, and GUI tools need a VNC server + viewer app since there's no X display by default.

COMMON TOOL CATEGORIES & BASIC SYNTAX (standard public documentation level; always get authorization before scanning
or testing anything you don't own - use a deliberately vulnerable target like a CTF box, DVWA, Metasploitable, or
HackTheBox/TryHackMe lab)
- Recon/scanning: nmap -sV -sC -p- <target>
                  nmap -A <target>
- Web content discovery: gobuster dir -u <url> -w <wordlist>   |   nikto -h <url>   |   whatweb <url>
- Password auditing (on hashes/services you're authorized to test): john <hashfile> | hashcat -m <mode> <hashfile> <wordlist>
  hydra -l <user> -P <wordlist> <target> <service>
- Web app testing: sqlmap -u "<url>" --batch   |   OWASP ZAP / Burp Suite for intercepting proxy work
- Exploitation framework: msfconsole -> search <term> -> use <module> -> show options -> set RHOSTS <target> -> run
- Binary/reverse engineering: gdb <binary> | radare2 <binary> | binwalk <firmware_image>
- Network capture: tcpdump -i <iface> | wireshark/tshark for analysis
- Wordlists: SecLists (apt install seclists, or git clone the SecLists repo) is the standard reference set

PRACTICE TARGETS (legal, built for this)
- TryHackMe, HackTheBox, PentesterLab, DVWA, OWASP Juice Shop, Metasploitable2/3 - all designed to be attacked for learning.

This file is reference material, not a walkthrough for any specific target. The agent should cite this file and the
tool's own --help/man page, check what's actually installed with envinfo before assuming a command exists, and
always confirm the user has authorization before running anything against a target that isn't their own or a
recognized practice lab.
"""


def ensure_knowledge_tree():
    for d in KNOWLEDGE_DOMAINS:
        os.makedirs(os.path.join(KNOWLEDGE_DIR, d), exist_ok=True)
    cheatsheet = os.path.join(KNOWLEDGE_DIR, "security", "termux_kali_cheatsheet.txt")
    if not os.path.exists(cheatsheet):
        open(cheatsheet, "w").write(TERMUX_KALI_CHEATSHEET)
    readme = os.path.join(KNOWLEDGE_DIR, "README.txt")
    if not os.path.exists(readme):
        open(readme, "w").write(
            "Drop .txt/.pdf/.docx/etc files in the matching subfolder (or make new subfolders of your own -\n"
            "the folder name becomes the 'domain' tag). On every run the agent scans this tree, ingests\n"
            "anything new or changed into its knowledge base, and uses it automatically on relevant tasks.\n"
            "Folders: " + ", ".join(KNOWLEDGE_DOMAINS) + " (or add your own).\n"
            "dictionary/ is special: plain lines 'english = bangla' or 'english\\tbangla' build a fast\n"
            "word-for-word lookup used by the 'translate' tool, in addition to\n"
            "being chunked into the knowledge base like everything else.\n")


def auto_study_knowledge(quiet=False):
    ensure_knowledge_tree()
    r = kb_learn(KNOWLEDGE_DIR)
    _dict_rebuild_if_needed()
    if not quiet:
        print("[knowledge] " + r.splitlines()[0])
    return r


def kb_context(task):
    try:
        if task.startswith("/"):
            return ""
        hits = [(s, c, ch) for s, c, ch in kb_search(task, 3) if c >= 0.5 and s >= 2.0]
        if not hits:
            return ""
        srcs = _kb_sources()
        lines = [f"- [{srcs.get(ch['s'], {}).get('domain', 'general')}/{srcs.get(ch['s'], {}).get('title', ch['s'])}] {ch['t'][:450]}"
                 for _, _, ch in hits]
        return ("\n\n[From your knowledge base, relevant to this task. Use it if helpful and mention the source. "
                "Call recall for more.]\n" + "\n".join(lines))
    except Exception:
        return ""


def t_learn(a):
    return kb_learn(resolve(a["path"]), bool(a.get("force")), a.get("domain"))


def t_recall(a):
    q = a.get("query", "")
    hits = kb_search(q, int(a.get("k", 4)))
    if not hits:
        return "Nothing in the knowledge base matches. Try other keywords, or learn the relevant files first."
    srcs = _kb_sources()
    out = []
    for n, (sc, cov, ch) in enumerate(hits, 1):
        s = srcs.get(ch["s"], {})
        out.append(f"[{n}] {s.get('domain', 'general')}/{s.get('title', ch['s'])} ({s.get('kind', '?')}, "
                   f"words {ch['w']+1}-{ch['w']+len(ch['t'].split())}, match {int(cov*100)}%)\n{ch['t']}")
    out.append("(For more context around a hit: read_doc {path, start_word}. Source path is the file listed by kb list.)")
    return clip("\n\n".join(out), 5500)


def t_kb(a, auto):
    act = a.get("action", "list")
    srcs = _kb_sources()
    if act == "stats":
        return f"{len(srcs)} sources, {sum(s['chunks'] for s in srcs.values())} chunks, {sum(s['words'] for s in srcs.values())} words."
    if act == "list":
        if not srcs:
            return "Knowledge base is empty. Use learn {path} on a book, document or folder."
        rows = [f"{s.get('domain', 'general')}/{s['title']} [{s['kind']}] {s['words']} words, added {s['added']}"
                for s in srcs.values()]
        return clip(f"{len(srcs)} sources:\n" + "\n".join(rows[-60:]), 4000)
    if act == "domains":
        by = Counter(s.get("domain", "general") for s in srcs.values())
        return "\n".join(f"{d}: {n} source(s)" for d, n in sorted(by.items())) or "Knowledge base is empty."
    if act == "forget":
        key = a.get("source", "").lower()
        gone = [k for k, s in srcs.items() if key and (key in k.lower() or key in s["title"].lower())]
        if not gone:
            return "No matching source."
        if not approve(f"remove from knowledge base: {', '.join(srcs[k]['title'] for k in gone[:5])}", auto):
            return "User denied."
        chunks = [c for c in _kb_read() if c["s"] not in gone]
        with open(KB_CHUNKS, "w") as f:
            for c in chunks:
                f.write(json.dumps(c) + "\n")
        for k in gone:
            srcs.pop(k)
        json.dump(srcs, open(KB_SOURCES, "w"))
        return f"Removed {len(gone)} source(s)."
    return "Unknown kb action. Use: list, stats, forget{source}."


DICT_CACHE_PATH = os.path.join(KB_DIR, "dictionary.json")
_DICT = {"sig": None, "en_bn": {}, "bn_en": {}}


def _dict_rebuild_if_needed():
    ddir = os.path.join(KNOWLEDGE_DIR, "dictionary")
    try:
        files = sorted(glob.glob(os.path.join(ddir, "*")))
    except Exception:
        files = []
    sig = tuple((f, os.path.getmtime(f)) for f in files if os.path.isfile(f))
    if sig == _DICT["sig"] and _DICT["en_bn"]:
        return
    en_bn, bn_en = {}, {}
    for f in files:
        if not os.path.isfile(f) or os.path.splitext(f)[1].lower() not in TEXT_EXT:
            continue
        try:
            for line in open(f, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = re.split(r"\t|=|:|-{1,2}(?!\w)", line, maxsplit=1) if "\t" in line else re.split(r"\t|=| - ", line, maxsplit=1)
                if len(parts) != 2:
                    continue
                en, bn = parts[0].strip().lower(), parts[1].strip()
                if en and bn:
                    en_bn.setdefault(en, bn)
                    bn_en.setdefault(bn, en)
        except Exception:
            pass
    _DICT.update(sig=sig, en_bn=en_bn, bn_en=bn_en)
    if en_bn:
        json.dump({"en_bn": en_bn, "bn_en": bn_en}, open(DICT_CACHE_PATH, "w"), ensure_ascii=False)


def dict_lookup(word):
    _dict_rebuild_if_needed()
    w = word.strip()
    wl = w.lower()
    if not _DICT["en_bn"] and not _DICT["bn_en"]:
        return None
    if wl in _DICT["en_bn"]:
        return f"{w} -> {_DICT['en_bn'][wl]}"
    if w in _DICT["bn_en"]:
        return f"{w} -> {_DICT['bn_en'][w]}"
    pool = list(_DICT["en_bn"].keys()) + list(_DICT["bn_en"].keys())
    close = difflib.get_close_matches(wl if re.match(r"^[a-zA-Z' -]+$", w) else w, pool, n=1, cutoff=0.78)
    if close:
        m = close[0]
        tgt = _DICT["en_bn"].get(m) or _DICT["bn_en"].get(m)
        return f"{w} (closest match: {m}) -> {tgt}"
    return None


def t_translate(a):
    word = a.get("word", "") or a.get("text", "") or a.get("query", "")
    if not word:
        return "Usage: translate {word}"
    hit = dict_lookup(word)
    if hit:
        return hit
    hits = kb_search(word, 2)
    srcs = _kb_sources()
    for _, _, ch in hits:
        if srcs.get(ch["s"], {}).get("domain") == "dictionary":
            return f"Not in the word list, but found in dictionary notes:\n{ch['t'][:400]}"
    return f"'{word}' isn't in the dictionary yet. Add it to a file in knowledge/dictionary/ as 'english = bangla'."


def knowledge_cli(cmd, arg):
    auto = {"on": False}
    if cmd == "/learn":
        print(kb_learn(arg) if arg else "Usage: /learn <file or folder>")
    elif cmd == "/recall":
        print(t_recall({"query": arg}) if arg else "Usage: /recall <question>")
    else:
        print(t_kb({"action": arg.split()[0] if arg else "list", "source": " ".join(arg.split()[1:])}, auto))


import glob


import textwrap
_ANSI = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def _c(code): return f"\x1b[{code}m" if _ANSI else ""
RST, BOLD, DIM = _c("0"), _c("1"), _c("2")
CY, GR, MG, YL, RD, BL = _c("36"), _c("32"), _c("35"), _c("33"), _c("31"), _c("34")
BCY, BGR, BMG, BYL, BRD, BBL = _c("96"), _c("92"), _c("95"), _c("93"), _c("91"), _c("94")
CONSOLE_NAME = os.environ.get("AGENT_NAME", "OMNIX-AI")
PRINT_LOCK = threading.RLock()
BUSY = threading.Event()
STOP = threading.Event()
WAITING = threading.Event()
CONSOLE = {"on": False, "t0": time.time(), "tasks": 0}


def _strip_ansi(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _W():
    try:
        w = shutil.get_terminal_size((80, 24)).columns
    except Exception:
        w = 80
    return max(38, min(w, 100))


def panel(title, body="", color=BCY, width=None, text_color="", icon="◈"):
    w = width or _W()
    inner = w - 4
    rows = []
    for para in str(body).expandtabs(4).split("\n"):
        rows += textwrap.wrap(para, inner, replace_whitespace=False, drop_whitespace=False,
                              break_long_words=True) or [""]
    head = f" {icon} {title} " if title else ""
    top = color + "╭─" + RST + (BOLD + color + head + RST if head else "") + color + "─" * max(w - 3 - len(head), 0) + "╮" + RST
    out = [top]
    for r in rows:
        r = r.rstrip()
        out.append(color + "│ " + RST + text_color + r + RST + " " * max(inner - len(r), 0) + color + " │" + RST)
    out.append(color + "╰" + "─" * (w - 2) + "╯" + RST)
    return "\n".join(out)


def show(title, body="", color=BCY, **kw):
    with PRINT_LOCK:
        print(panel(title, body, color, **kw))


def log(msg, color=""):
    with PRINT_LOCK:
        print(f"{color}{msg}{RST}" if color else msg)


_LOGO = {
    "A": ["▄▀█", "█▀█"], "G": ["█▀▀", "█▄█"], "E": ["█▀▀", "██▄"], "N": ["█▄ █", "█ ▀█"],
    "T": ["▀█▀", " █ "], "D": ["█▀▄", "█▄▀"], " ": ["  ", "  "],
}


def _logo(name):
    name = name.upper()
    if not all(ch in _LOGO for ch in name):
        return [BOLD + BGR + name + RST]
    top = " ".join(_LOGO[ch][0] for ch in name)
    bot = " ".join(_LOGO[ch][1] for ch in name)
    return [BOLD + BGR + top + RST, BOLD + BCY + bot + RST]


def banner():
    lines = _logo(CONSOLE_NAME) + [
        f"{DIM}neural interface online{RST}  {BGR}●{RST}",
        "",
        f"{DIM}TOOLS {RST}{CY}{len(PLUGINS)} custom{RST}   {DIM}PID {RST}{CY}{os.getpid()}{RST}",
        "",
        f"{BYL}⌨{RST}  just type to chat  ·  {BYL}!task{RST}{DIM} uses tools  ·  {RST}{BYL}/help{RST}",
    ]
    w = _W()
    with PRINT_LOCK:
        print()
        print(BCY + "╔" + "═" * (w - 2) + "╗" + RST)
        for ln in lines:
            pad = w - 4 - len(_strip_ansi(ln))
            print(BCY + "║ " + RST + ln + " " * max(pad, 0) + BCY + " ║" + RST)
        print(BCY + "╚" + "═" * (w - 2) + "╝" + RST)


def _uptime():
    s = int(time.time() - CONSOLE["t0"])
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def status_panel(hist_n, auto=None):
    state = f"{BYL}● WORKING{RST}" if BUSY.is_set() else f"{BGR}● READY{RST}"
    aut = f"{BYL}AUTO●{RST}" if (auto and auto.get("on")) else f"{DIM}AUTO○{RST}"
    d = f"{DIM}┊{RST}"
    mode = f"{BCY}CHAT{RST}" if MODE["chat"] else f"{BMG}AGENT{RST}"
    return f"{d} {state} {d} {mode} {d} {aut} {d} turns:{hist_n} {d} up {_uptime()} {d} {time.strftime('%H:%M:%S')}"


def _prompt_line():
    return f"{BGR}┌─[{RST}{BOLD}{CONSOLE_NAME}{RST}{BGR}]{RST}\n{BGR}└─λ{RST} "


def ui_note(msg):
    log(f"  {DIM}◌ {msg}{RST}")


def ui_thought(n, text):
    show(f"STEP {n} · THINK", text, MG, icon="◇", text_color=DIM)


def ui_tool(tool, args):
    a = clip(json.dumps(args, ensure_ascii=False), 1200)
    log(f"  {BYL}▸ {BOLD}{tool}{RST} {DIM}{a}{RST}")


def ui_result(res, bad=False):
    _log_raw("RESULT (FAILED)" if bad else "RESULT", res)
    show("RESULT" if not bad else "RESULT · FAILED", clip(res), RD if bad else GR, icon="◆" if not bad else "✖")


def ui_answer(ans):
    show("AGENT", ans, BGR, icon="◀", text_color=BOLD)


def ui_error(msg):
    show("ERROR", msg, RD, icon="✖")


def ui_ask(desc):
    show("PERMISSION REQUIRED", desc, BYL, icon="⚠")


HELP_TEXT = (
    "/auto        toggle auto-approve\n/reset       clear conversation memory\n/tools       list custom tools\n"
    "/status      show system panel\n/doctor      check the AI engine\n/rollback    undo last self-edit\n"
    "/audit       code audit tools\n/study /learn /recall /kb   knowledge base\n"
    "/chat        instant answers, no tools (default)\n/agent       tool-using agent for every message\n"
    "/clear       clear screen\nexit         shut down\n\n"
    "Type normally to chat. Start a message with ! to run it as an agent task\n(files, commands, apps), e.g.  !list my files"
)


def _ollama_base():
    m = re.match(r"(https?://[^/]+)", OLLAMA)
    return m.group(1) if m else "http://127.0.0.1:11434"


def ollama_models():
    try:
        with urllib.request.urlopen(_ollama_base() + "/api/tags", timeout=3) as r:
            return [m.get("name", "") for m in json.load(r).get("models", [])]
    except Exception:
        return None


def ensure_ollama(verbose=True):
    if ollama_models() is not None:
        return True
    if not shutil.which("ollama"):
        if verbose:
            ui_error("Ollama is not installed or not on PATH.\nInstall it (pkg install ollama), then run: ollama pull " + MODEL)
        return False
    if verbose:
        log(f"  {DIM}◌ Ollama is offline - starting 'ollama serve' in the background...{RST}")
    try:
        lf = open(os.path.join(HOME_DIR, "ollama.log"), "a")
        subprocess.Popen(["ollama", "serve"], stdout=lf, stderr=lf, stdin=subprocess.DEVNULL, start_new_session=True)
    except Exception as e:
        if verbose:
            ui_error("Could not start ollama: " + str(e)[:150])
        return False
    for _ in range(40):
        time.sleep(0.5)
        if ollama_models() is not None:
            if verbose:
                log(f"  {BGR}● Ollama online{RST}")
            return True
    if verbose:
        ui_error("Ollama did not come up. See ~/.omnix_ai/ollama.log")
    return False


def _think_retry(system, hist):
    try:
        return think(system, hist)
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, ConnectionError, OSError):
        if not ensure_ollama():
            raise
        return think(system, hist)


def think_safe(system, hist):
    box = {}

    def work():
        try:
            box["r"] = _think_retry(system, hist)
        except BaseException as e:
            box["e"] = e
    t = threading.Thread(target=work, daemon=True)
    t.start()
    t0, i, frames = time.time(), 0, "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    while t.is_alive():
        if _ANSI:
            secs = int(time.time() - t0)
            note = "  (first run loads the model - can take a minute)" if secs > 8 else ""
            with PRINT_LOCK:
                sys.stdout.write(f"\r  {BCY}{frames[i % 10]}{RST} {DIM}model is working... {secs}s{note}{RST}\x1b[K")
                sys.stdout.flush()
            i += 1
        t.join(0.12)
    if _ANSI:
        with PRINT_LOCK:
            sys.stdout.write("\r\x1b[K")
            sys.stdout.flush()
    if "e" in box:
        raise box["e"]
    return box["r"]


def doctor():
    rows = []
    models = ollama_models()
    rows.append(("✔" if models is not None else "✖") + " Ollama server" +
                ("" if models is not None else "\n    → run: ollama serve   (or just retry - the agent will try to start it)"))
    if models is not None:
        have = MODEL in models or MODEL + ":latest" in models
        rows.append(("✔" if have else "✖") + f" Model {MODEL}" + ("" if have else f"\n    → run: ollama pull {MODEL}"))
    show("DOCTOR", "\n".join(rows), BBL, icon="✚")


MODE = {"chat": True}
CHAT_HIST = []
CHAT_SYSTEM = ("You are a fast, helpful assistant running on an Android phone. Answer directly and briefly in plain text. "
               "No JSON, no tool calls, no step-by-step planning unless asked.")


def chat_stream(text):
    CHAT_HIST.append({"role": "user", "content": text})
    body = {"model": MODEL, "stream": True, "keep_alive": "30m",
            "messages": [{"role": "system", "content": CHAT_SYSTEM}] + CHAT_HIST[-12:],
            "options": {"temperature": 0.3, "num_ctx": 2048}}
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        try:
            r = urllib.request.urlopen(req, timeout=900)
        except (urllib.error.URLError, ConnectionError):
            if not ensure_ollama():
                CHAT_HIST.pop()
                return
            r = urllib.request.urlopen(req, timeout=900)
    except Exception as e:
        CHAT_HIST.pop()
        ui_error(f"Ollama error: {e}")
        return
    out = []
    with PRINT_LOCK:
        print(f"\n{BGR}{BOLD}◀ AGENT{RST}\n  ", end="", flush=True)
    try:
        with r:
            for line in r:
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                piece = d.get("message", {}).get("content", "")
                if piece:
                    out.append(piece)
                    with PRINT_LOCK:
                        print(piece.replace("\n", "\n  "), end="", flush=True)
                if d.get("done"):
                    break
    finally:
        with PRINT_LOCK:
            print()
        if out:
            CHAT_HIST.append({"role": "assistant", "content": "".join(out)})
        else:
            CHAT_HIST.pop()


CMDQ = queue.Queue()
ANSQ = queue.Queue()
ASK = {"pending": False}


def ask_line(prompt):
    if not CONSOLE["on"]:
        return input(prompt)
    with PRINT_LOCK:
        print(f"{BYL}  ▸ {RST}{prompt}", end="", flush=True)
    ASK["pending"] = True
    try:
        while not STOP.is_set():
            try:
                return ANSQ.get(timeout=0.3)
            except queue.Empty:
                continue
        return "n"
    finally:
        ASK["pending"] = False


def text_worker():
    while not STOP.is_set():
        if BUSY.is_set() and not ASK["pending"]:
            time.sleep(0.15)
            continue
        if not ASK["pending"]:
            with PRINT_LOCK:
                print("\n" + _prompt_line(), end="", flush=True)
        WAITING.set()
        try:
            line = input("")
        except (EOFError, KeyboardInterrupt):
            CMDQ.put(("exit", None))
            return
        finally:
            WAITING.clear()
        line = line.strip()
        if ASK["pending"]:
            ANSQ.put(line)
            continue
        if not line:
            continue
        if line in ("exit", "quit"):
            CMDQ.put(("exit", None))
            return
        BUSY.set()
        CMDQ.put(("text", line))


def _dispatch_line(task, hist, auto):
    if task == "/auto":
        auto["on"] = not auto["on"]
        log(f"  auto-approve: {'ON' if auto['on'] else 'OFF'}", BYL)
    elif task == "/help":
        show("COMMANDS", HELP_TEXT, BCY, icon="?")
    elif task == "/status":
        show("SYSTEM", status_panel(len(hist) + len(CHAT_HIST), auto).replace("┊", "|") + f"\ncustom tools: {len(PLUGINS)}", BBL, icon="◎")
    elif task == "/doctor":
        doctor()
    elif task.startswith("/raw"):
        arg = task[4:].strip()
        RAW["full"] = (arg == "on") if arg in ("on", "off") else not RAW["full"]
        log(f"  raw mode: {'ON - nothing is cut, but replies get slower and longer' if RAW['full'] else 'OFF - long output is capped on screen (full copy always kept in the session log)'}", BYL)
    elif task == "/log":
        show("SESSION LOG", f"Every tool result, in full, is being written to:\n{SESSION_LOG}\nOpen it any time with: cat {SESSION_LOG}", BBL, icon="📄")
    elif task == "/clear":
        os.system("clear")
        banner()
    elif task == "/reset":
        hist.clear()
        CHAT_HIST.clear()
        log("  memory cleared", BYL)
    elif task == "/tools":
        show("TOOLS", "\n".join(f"{n}: {d}" for n, (d, _) in PLUGINS.items()) or "no custom tools yet", BMG, icon="⚙")
    elif task == "/rollback":
        rollback()
    elif task.startswith("/audit"):
        audit_cli(task[6:].strip())
    elif task.startswith("/study"):
        study_cli(task[6:].strip())
    elif task.split()[0] in ("/learn", "/recall", "/kb"):
        knowledge_cli(task.split()[0], task[len(task.split()[0]):].strip())
    elif task == "/agent":
        MODE["chat"] = False
        log("  mode: AGENT (uses tools, works in steps)", BYL)
    elif task == "/chat":
        MODE["chat"] = True
        log("  mode: CHAT (instant answers, no tools)", BYL)
    elif task.startswith("/"):
        show("UNKNOWN COMMAND", f"{task.split()[0]} is not a command. Type /help to see them.", BYL, icon="?")
    elif task.startswith("!"):
        run_task(task[1:].strip(), hist, auto)
    elif MODE["chat"]:
        chat_stream(task)
    else:
        run_task(task, hist, auto)


def interactive_console(hist, auto):
    CONSOLE["on"] = True
    banner()
    ensure_ollama()
    threading.Thread(target=text_worker, daemon=True).start()
    try:
        while not STOP.is_set():
            try:
                src, payload = CMDQ.get(timeout=0.5)
            except queue.Empty:
                continue
            if src == "exit":
                STOP.set()
                break
            BUSY.set()
            CONSOLE["tasks"] += 1
            try:
                with PRINT_LOCK:
                    print(f"\n{status_panel(len(hist) + len(CHAT_HIST), auto)}")
                    print(f"{BCY}⌨ TASK{RST} {BOLD}{payload}{RST}")
                _dispatch_line(payload, hist, auto)
            except KeyboardInterrupt:
                log("\n  ✖ task interrupted", RD)
            except Exception as e:
                ui_error(f"{type(e).__name__}: {e}")
            finally:
                if CMDQ.empty():
                    BUSY.clear()
                    if WAITING.is_set() and not ASK["pending"]:
                        with PRINT_LOCK:
                            print("\n" + _prompt_line(), end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        STOP.set()
        CONSOLE["on"] = False
    log(f"\n{BGR}◈ shutting down · session {_uptime()} · {CONSOLE['tasks']} commands{RST}")


def t_remember(a):
    note = a["note"].strip()
    open(MEM, "a").write(note + "\n")
    try:
        kb_add_many([("mem:" + hex(abs(hash(note)))[2:], note[:60], "memory", "", note, "general")])
    except Exception:
        pass
    return "Saved."


def t_create_tool(a):
    name = re.sub(r"[^a-z0-9_]", "", a["name"].lower())
    if not name:
        return "Bad tool name."
    src = f'NAME = {name!r}\nDESC = {a.get("description","custom tool")!r}\n\n{a["code"]}\n'
    compile(src, name, "exec")
    if "def run" not in src:
        return "Code must define run(args)."
    open(os.path.join(TOOLS_DIR, name + ".py"), "w").write(src)
    load_plugins()
    return f"Tool '{name}' created and loaded." if name in PLUGINS else "Saved but failed to load."


def t_self_edit(a):
    src = open(SELF).read()
    if a["old"] not in src:
        return "self_edit failed: old text not found in my source."
    new_src = src.replace(a["old"], a["new"], 1)
    compile(new_src, SELF, "exec")
    bk = os.path.join(BACKUPS, f"omnix_{int(time.time())}.py")
    shutil.copy(SELF, bk)
    open(SELF, "w").write(new_src)
    return f"Source edited (backup: {bk}). Call restart to load it. /rollback undoes it."


def rollback():
    files = sorted(os.listdir(BACKUPS))
    if not files:
        print("No backups.")
        return
    shutil.copy(os.path.join(BACKUPS, files[-1]), SELF)
    os.remove(os.path.join(BACKUPS, files[-1]))
    print("Restored", files[-1], "- restart me.")


CDP_HOST = os.environ.get("BROWSER_CDP", "127.0.0.1:9222")
_B = {"ws": None, "proc": None, "net": [], "netmap": {}, "con": [], "id": 0,
      "pending": {}, "loaded": threading.Event(), "lock": threading.Lock()}


class WS:
    def __init__(self, url):
        u = urllib.parse.urlparse(url)
        self.lock = threading.Lock()
        self.buf = b""
        self.s = socket.create_connection((u.hostname, u.port or 80), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        path = (u.path or "/") + ("?" + u.query if u.query else "")
        self.s.sendall((f"GET {path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                        f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
        raw = b""
        while b"\r\n\r\n" not in raw:
            c = self.s.recv(4096)
            if not c:
                raise ConnectionError("websocket handshake failed")
            raw += c
        head, self.buf = raw.split(b"\r\n\r\n", 1)
        if b" 101" not in head.split(b"\r\n")[0]:
            raise ConnectionError("websocket refused: " + head.split(b"\r\n")[0].decode(errors="ignore"))
        self.s.settimeout(None)

    def _read(self, n):
        while len(self.buf) < n:
            c = self.s.recv(65536)
            if not c:
                raise ConnectionError("socket closed")
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _frame(self, op, payload):
        n = len(payload)
        h = bytes([0x80 | op])
        if n < 126:
            h += bytes([0x80 | n])
        elif n < 65536:
            h += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            h += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        with self.lock:
            self.s.sendall(h + mask + body)

    def send(self, text):
        self._frame(1, text.encode())

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            fin, op, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 8:
                raise ConnectionError("closed")
            if op == 9:
                self._frame(10, data)
                continue
            if op == 10:
                continue
            msg += data
            if fin:
                return msg.decode("utf-8", "ignore")

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


def _event(m):
    p, meth = m.get("params", {}), m.get("method", "")
    if meth == "Network.requestWillBeSent":
        e = {"rid": p["requestId"], "method": p["request"]["method"], "url": p["request"]["url"],
             "type": p.get("type", "?"), "status": None}
        _B["net"].append(e)
        _B["netmap"][p["requestId"]] = e
        del _B["net"][:-500]
    elif meth == "Network.responseReceived":
        e = _B["netmap"].get(p["requestId"])
        if e:
            e["status"] = p["response"].get("status")
    elif meth == "Runtime.consoleAPICalled":
        txt = " ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", []))
        _B["con"].append(f"[{p.get('type')}] {txt}")
    elif meth == "Runtime.exceptionThrown":
        d = p.get("exceptionDetails", {})
        _B["con"].append("[exception] " + str(d.get("exception", {}).get("description", d.get("text", ""))))
    elif meth == "Log.entryAdded":
        en = p.get("entry", {})
        _B["con"].append(f"[{en.get('level')}] {en.get('text')} {en.get('url','')}")
    elif meth == "Page.loadEventFired":
        _B["loaded"].set()
    del _B["con"][:-300]


def _reader(ws):
    try:
        while True:
            m = json.loads(ws.recv())
            if "id" in m:
                ev = _B["pending"].get(m["id"])
                if ev:
                    ev[1] = m
                    ev[0].set()
            else:
                _event(m)
    except Exception:
        _B["ws"] = None


def _cmd(method, params=None, timeout=30):
    ws = _B["ws"]
    if ws is None:
        raise ConnectionError("browser disconnected")
    with _B["lock"]:
        _B["id"] += 1
        i = _B["id"]
    ev = [threading.Event(), None]
    _B["pending"][i] = ev
    ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
    ok = ev[0].wait(timeout)
    _B["pending"].pop(i, None)
    if not ok:
        raise TimeoutError(method + " timed out")
    if "error" in ev[1]:
        raise RuntimeError(ev[1]["error"].get("message", "cdp error"))
    return ev[1].get("result", {})


def _targets():
    return json.load(urllib.request.urlopen(f"http://{CDP_HOST}/json", timeout=3))


def _launch():
    exe = next((shutil.which(x) for x in ("chromium", "chromium-browser", "google-chrome", "chrome")
                if shutil.which(x)), None)
    if not exe:
        raise RuntimeError(
            "No browser available. Option A (headless): pkg install x11-repo tur-repo && pkg install chromium. "
            "Option B (your real Chrome, rooted): open Chrome, then run: "
            "su -c 'socat TCP-LISTEN:9222,bind=127.0.0.1,fork,reuseaddr ABSTRACT-CONNECT:chrome_devtools_remote &' "
            "(needs: pkg install socat)")
    port = CDP_HOST.split(":")[1]
    _B["proc"] = subprocess.Popen(
        [exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--remote-debugging-port={port}",
         "--user-data-dir=" + os.path.join(HOME_DIR, "chrome"), "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        try:
            _targets()
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Browser started but DevTools port did not open.")


def _connect():
    if _B["ws"]:
        return
    try:
        ts = _targets()
    except Exception:
        _launch()
        ts = _targets()
    pages = [t for t in ts if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not pages:
        req = urllib.request.Request(f"http://{CDP_HOST}/json/new?about:blank", method="PUT")
        pages = [json.load(urllib.request.urlopen(req, timeout=5))]
    path = urllib.parse.urlparse(pages[0]["webSocketDebuggerUrl"]).path
    ws = WS(f"ws://{CDP_HOST}{path}")
    _B["ws"] = ws
    threading.Thread(target=_reader, args=(ws,), daemon=True).start()
    for d in ("Page", "Runtime", "Network", "Log"):
        _cmd(d + ".enable")


def _js(expr, timeout=30):
    r = _cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, timeout)
    if "exceptionDetails" in r:
        d = r["exceptionDetails"]
        return "JS error: " + str(d.get("exception", {}).get("description", d.get("text", "")))
    v = r.get("result", {})
    return v.get("value", v.get("description"))


def _summary(n):
    r = _js("JSON.stringify({t:document.title,u:location.href,x:document.body?document.body.innerText.slice(0,%d):''})" % n)
    try:
        d = json.loads(r)
        return f"Title: {d['t']}\nURL: {d['u']}\n\n{d['x']}"
    except Exception:
        return str(r)


_INTERACTIVE = ("a[href],button,input:not([type=hidden]),select,textarea,[role=button],[role=link],[role=tab],"
                "[role=menuitem],[role=checkbox],[role=option],[onclick],[contenteditable=true],[contenteditable=''],summary")

_ELEMENTS_JS = r"""(()=>{
const sel=__SEL__, lim=__LIM__;
document.querySelectorAll('[data-aid]').forEach(e=>e.removeAttribute('data-aid'));
const all=[];
for(const e of document.querySelectorAll(sel)){
  const r=e.getBoundingClientRect(), cs=getComputedStyle(e);
  if(r.width<2||r.height<2||cs.visibility==='hidden'||cs.display==='none'||e.disabled)continue;
  all.push([e,(r.bottom>=0&&r.top<=innerHeight)?1:0]);
}
all.sort((a,b)=>b[1]-a[1]);
const out=[];
all.slice(0,lim).forEach(([e,v],i)=>{
  e.setAttribute('data-aid',String(i));
  const label=(e.innerText||(e.type==='password'?'':e.value)||e.placeholder||e.getAttribute('aria-label')||e.title||e.alt||e.name||'').trim().replace(/\s+/g,' ').slice(0,60);
  out.push([i,e.tagName.toLowerCase(),e.type||'',label,e.tagName==='A'?e.href:'',v?0:1]);
});
return JSON.stringify(out);
})()"""

_FIND_JS = r"""(()=>{
const t=__T__.toLowerCase().trim(), sel=__SEL__;
document.querySelectorAll('[data-aid="find"]').forEach(e=>e.removeAttribute('data-aid'));
let best=null,bs=1e12;
for(const e of document.querySelectorAll(sel+',label,li,h1,h2,h3,td,span,p,div')){
  const r=e.getBoundingClientRect(); if(r.width<2||r.height<2)continue;
  const l=(e.innerText||e.value||e.placeholder||e.getAttribute('aria-label')||e.title||'').trim().replace(/\s+/g,' ').toLowerCase();
  if(!l||l.length>200)continue;
  const m=l===t?0:l.startsWith(t)?1:l.includes(t)?2:-1; if(m<0)continue;
  const s=m*1000+(e.matches(sel)?0:500)+l.length;
  if(s<bs){bs=s;best=e;}
}
if(!best)return 'none';
best.scrollIntoView({block:'center'}); best.setAttribute('data-aid','find'); return 'ok';
})()"""

_KEYMAP = {"enter": (13, "Enter", "\r"), "tab": (9, "Tab", ""), "escape": (27, "Escape", ""), "backspace": (8, "Backspace", ""),
           "arrowdown": (40, "ArrowDown", ""), "arrowup": (38, "ArrowUp", ""), "arrowleft": (37, "ArrowLeft", ""),
           "arrowright": (39, "ArrowRight", ""), "pagedown": (34, "PageDown", ""), "space": (32, " ", " ")}


def _elements_text(limit=30):
    r = _js(_ELEMENTS_JS.replace("__SEL__", json.dumps(_INTERACTIVE)).replace("__LIM__", str(limit)))
    try:
        rows = json.loads(r)
    except Exception:
        return "(could not list elements)"
    out = []
    for i, tag, typ, label, href, off in rows:
        kind = f"input:{typ or 'text'}" if tag == "input" else tag
        s = f'#{i} {kind} "{label}"'
        if href:
            s += " -> " + href[:80]
        if off:
            s += " (off-screen)"
        out.append(s)
    return "\n".join(out) or "(no interactive elements found)"


def _sel_from(a):
    if a.get("index") is not None:
        return '[data-aid="%d"]' % int(a["index"])
    if a.get("text") and a.get("action") in ("click", "select"):
        r = _js(_FIND_JS.replace("__T__", json.dumps(str(a["text"]))).replace("__SEL__", json.dumps(_INTERACTIVE)))
        return '[data-aid="find"]' if r == "ok" else None
    return a.get("selector", "") or ""


def _settle():
    time.sleep(0.8)
    for _ in range(20):
        try:
            if _js("document.readyState") == "complete":
                return
        except Exception:
            pass
        time.sleep(0.5)


def _after(n=1200):
    _settle()
    return clip(_summary(n) + "\n\n[clickable elements, use their #number]\n" + _elements_text(25), 4500)


def _click_sel(sel):
    r = _js("(()=>{const e=document.querySelector(%s);if(!e)return '';e.scrollIntoView({block:'center',inline:'center'});"
            "const r=e.getBoundingClientRect();return JSON.stringify([r.left+r.width/2,r.top+r.height/2])})()" % json.dumps(sel))
    if not r:
        return False
    x, y = json.loads(r)
    _cmd("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
    _cmd("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
    _cmd("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
    return True


def _press(key):
    vk, code, text = _KEYMAP.get(key.lower(), (0, key, ""))
    if not vk:
        raise RuntimeError("Unknown key. Use: " + ", ".join(_KEYMAP))
    base = {"key": code if code != " " else " ", "code": code, "windowsVirtualKeyCode": vk}
    _cmd("Input.dispatchKeyEvent", {**base, "type": "keyDown" if text else "rawKeyDown", **({"text": text} if text else {})})
    _cmd("Input.dispatchKeyEvent", {**base, "type": "keyUp"})


STALE = "That element is gone or the page changed. Call browser elements again to get fresh numbers."


def t_browser(a):
    act = a.get("action", "")
    if act == "close":
        if _B["ws"]:
            _B["ws"].close()
            _B["ws"] = None
        if _B["proc"]:
            _B["proc"].terminate()
            _B["proc"] = None
        return "Browser closed."
    _connect()
    sel = json.dumps(a.get("selector", ""))
    if act == "open":
        url = a["url"] if "://" in a["url"] else "https://" + a["url"]
        _B["net"].clear(); _B["netmap"].clear(); _B["con"].clear(); _B["loaded"].clear()
        r = _cmd("Page.navigate", {"url": url})
        if r.get("errorText"):
            return "Navigation failed: " + r["errorText"]
        _B["loaded"].wait(25)
        return _after(2000)
    if act == "elements":
        return clip(_elements_text(int(a.get("limit", 40))), 4500)
    if act == "click":
        s = _sel_from(a)
        if s is None:
            return f"No visible element with text '{a.get('text')}'. Call elements to see what is on the page."
        if not s:
            return "click needs index, text or selector."
        if not _click_sel(s):
            return STALE if a.get("index") is not None else "selector not found"
        return "Clicked.\n" + _after()
    if act == "type":
        s = _sel_from(a)
        if not s:
            return "type needs index or selector (from browser elements)."
        r = _js("(()=>{const e=document.querySelector(%s);if(!e)return 'gone';e.scrollIntoView({block:'center'});e.focus();"
                "if(%s){if(e.setSelectionRange&&e.value!==undefined){e.setSelectionRange(e.value.length,e.value.length)}}"
                "else if(typeof e.select==='function'){e.select()}else{document.execCommand('selectAll')}return 'ok'})()"
                % (json.dumps(s), "true" if a.get("append") else "false"))
        if r != "ok":
            return STALE if a.get("index") is not None else "selector not found"
        txt = str(a.get("text", ""))
        if txt:
            _cmd("Input.insertText", {"text": txt})
        else:
            _press("Backspace")
        if a.get("submit"):
            _press("Enter")
            return "Typed and pressed Enter.\n" + _after()
        return "Typed."
    if act == "press":
        _press(str(a.get("key", "Enter")))
        return "Pressed.\n" + _after()
    if act == "select":
        s = _sel_from(a)
        v = json.dumps(str(a.get("value", "")).lower())
        r = _js("(()=>{const e=document.querySelector(%s);if(!e||!e.options)return 'not a select';"
                "for(const o of e.options){if(o.text.toLowerCase()===%s||o.value.toLowerCase()===%s){e.value=o.value;"
                "e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return 'ok'}}"
                "return 'option not found'})()" % (json.dumps(s), v, v))
        return str(r)
    if act == "scroll":
        d = a.get("direction", "down")
        js = {"down": "scrollBy(0,innerHeight*0.8)", "up": "scrollBy(0,-innerHeight*0.8)", "top": "scrollTo(0,0)",
              "bottom": "scrollTo(0,document.documentElement.scrollHeight)"}.get(d, "scrollBy(0,innerHeight*0.8)")
        pos = _js("(()=>{window.%s;return Math.round(scrollY)+'/'+document.documentElement.scrollHeight})()" % js)
        time.sleep(0.6)
        return f"Scrolled {d} (position {pos}).\n" + _elements_text(25)
    if act == "wait":
        secs = min(float(a.get("seconds", 10)), 60)
        end = time.time() + secs
        if not (a.get("text") or a.get("selector")):
            time.sleep(min(secs, 10))
            return "Waited.\n" + _after()
        while time.time() < end:
            ok = _js("document.body&&document.body.innerText.toLowerCase().includes(%s)" % json.dumps(a["text"].lower())) \
                if a.get("text") else _js("!!document.querySelector(%s)" % sel)
            if ok is True:
                return "Found.\n" + _after()
            time.sleep(0.7)
        return "Timed out waiting.\n" + _after(800)
    if act == "find":
        r = _js("(()=>{const t=%s.toLowerCase();const x=document.body.innerText;const lx=x.toLowerCase();const out=[];let i=-1;"
                "while(out.length<5&&(i=lx.indexOf(t,i+1))>=0){out.push(x.slice(Math.max(0,i-80),i+t.length+120).replace(/\\s+/g,' '))}"
                "return JSON.stringify(out)})()" % json.dumps(str(a.get("text", ""))))
        try:
            rows = json.loads(r)
        except Exception:
            return str(r)
        return clip("\n---\n".join(rows) or "Text not found on the page.", 3000)
    if act == "back":
        _js("history.back()")
        return "Went back.\n" + _after()
    if act == "text":
        return clip(str(_js(f"(document.querySelector({sel})||document.body).innerText")), 4500)
    if act == "html":
        return clip(str(_js(f"(document.querySelector({sel})||document.documentElement).outerHTML")), 5000)
    if act == "links":
        r = _js("JSON.stringify([...document.querySelectorAll('a[href]')].slice(0,60).map(a=>(a.innerText||'').trim().slice(0,50)+' -> '+a.href))")
        try:
            return clip("\n".join(json.loads(r)), 4000)
        except Exception:
            return str(r)
    if act == "js":
        v = _js(a["code"])
        return clip(v if isinstance(v, str) else json.dumps(v), 4000)
    if act == "network":
        rows = [(i, e) for i, e in enumerate(_B["net"])
                if a.get("all") or e["type"] in ("XHR", "Fetch", "Document")]
        return clip("\n".join(f"#{i} {e['method']} {e['status']} {e['type']} {e['url'][:150]}"
                              for i, e in rows[-60:]) or "No requests captured. Open a page first.", 4500)
    if act == "response":
        e = _B["net"][int(a["index"])]
        r = _cmd("Network.getResponseBody", {"requestId": e["rid"]})
        return clip(f"{e['method']} {e['url']}\nstatus={e['status']}\n\n{r.get('body','')}", 4500)
    if act == "console":
        return clip("\n".join(_B["con"][-40:]) or "Console empty.", 3500)
    if act == "storage":
        ck = _cmd("Network.getCookies").get("cookies", [])
        ls = _js("JSON.stringify({local:{...localStorage},session:{...sessionStorage}})")
        return clip("cookies: " + json.dumps([{"name": c["name"], "domain": c["domain"], "value": c["value"][:60]} for c in ck])
                    + "\nstorage: " + str(ls), 4500)
    if act == "screenshot":
        r = _cmd("Page.captureScreenshot", {"format": "png"}, 60)
        p = os.path.expanduser(a.get("path", "~/shot.png"))
        open(p, "wb").write(base64.b64decode(r["data"]))
        return "Saved screenshot to " + p
    return ("Unknown action. Use: open, elements, click{index|text|selector}, type{index|selector,text,submit?,append?}, press{key}, "
            "select{index,value}, scroll{direction}, wait{text|selector|seconds}, find{text}, back, text, html, links, js, "
            "network, response, console, storage, screenshot, close.")


def t_http(a):
    method = a.get("method", "GET").upper()
    headers = dict(a.get("headers") or {})
    body, data = a.get("body"), None
    if body is not None:
        if isinstance(body, str):
            data = body.encode()
        else:
            data = json.dumps(body).encode()
            headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(a["url"], data=data, method=method, headers={"User-Agent": UA, **headers})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        status, hd, text = r.status, dict(r.headers), r.read(200000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        status, hd, text = e.code, dict(e.headers), e.read(200000).decode("utf-8", "ignore")
    hl = "\n".join(f"{k}: {v}" for k, v in list(hd.items())[:15])
    return clip(f"status={status}\n{hl}\n\n{text}", 4500)


GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")


def _su(cmd, timeout=60):
    p = subprocess.run(["su", "-c", cmd], capture_output=True, text=True, timeout=timeout)
    return p.stdout + p.stderr


def _ui_nodes():
    last = ""
    for cmd in ("uiautomator dump /sdcard/ui.xml", "uiautomator dump --compressed /sdcard/ui.xml"):
        _su("rm -f /sdcard/ui.xml; " + cmd + " >/dev/null 2>&1")
        xml = _su("cat /sdcard/ui.xml")
        if "<hierarchy" in xml:
            break
        last = xml[:100]
    else:
        raise RuntimeError("Could not read the screen (screen off or locked, a video is playing, or root not granted to Termux). " + last)
    root = ET.fromstring(xml[xml.index("<hierarchy"):])
    out = []
    for n in root.iter("node"):
        b = re.findall(r"\d+", n.get("bounds", ""))
        if len(b) != 4:
            continue
        x1, y1, x2, y2 = map(int, b)
        cls = n.get("class", "")
        out.append({"text": n.get("text", ""), "desc": n.get("content-desc", ""),
                    "id": n.get("resource-id", "").split("/")[-1], "click": n.get("clickable") == "true",
                    "edit": "EditText" in cls, "focused": n.get("focused") == "true",
                    "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2, "pkg": n.get("package", "")})
    return out


def _ui_find(nodes, want):
    w = want.lower().strip()
    hits = []
    for i, n in enumerate(nodes):
        labels = [l for l in (n["text"].lower(), n["desc"].lower(), n["id"].lower()) if l]
        if w in labels:
            s = 0
        elif any(l.startswith(w) for l in labels):
            s = 1
        elif any(w in l for l in labels):
            s = 2
        else:
            continue
        hits.append(((s, not n["click"], len(n["text"] or n["desc"]), i), n))
    hits.sort(key=lambda h: h[0])
    return [n for _, n in hits]


def _peek(limit=14):
    try:
        nodes = _ui_nodes()
    except Exception as e:
        return "\n[could not read screen: " + str(e)[:80] + "]"
    rows = []
    for x in nodes:
        lab = x["text"] or x["desc"]
        if lab or x["edit"]:
            rows.append(f"{lab[:40]}{'*' if x['click'] else ''}{'[input]' if x['edit'] else ''}")
    app = nodes[0]["pkg"] if nodes else "?"
    return f"\n[screen now, app={app}; * = tappable]\n" + " | ".join(rows[:limit])


APP_HINTS = {"whatsapp": "com.whatsapp", "telegram": "org.telegram.messenger", "signal": "org.thoughtcrime.securesms",
             "chrome": "com.android.chrome", "firefox": "org.mozilla.firefox", "youtube": "com.google.android.youtube",
             "gmail": "com.google.android.gm", "maps": "com.google.android.apps.maps", "instagram": "com.instagram.android",
             "facebook": "com.facebook.katana", "messenger": "com.facebook.orca", "twitter": "com.twitter.android",
             "x": "com.twitter.android", "settings": "com.android.settings", "spotify": "com.spotify.music",
             "snapchat": "com.snapchat.android", "discord": "com.discord", "reddit": "com.reddit.frontpage",
             "linkedin": "com.linkedin.android", "messages": "com.google.android.apps.messaging"}


def _installed():
    return {l[8:].strip() for l in _su("pm list packages").splitlines() if l.startswith("package:")}


def _pkg_for(name):
    n = name.lower().strip()
    if "." in n and " " not in n:
        return n, []
    inst = _installed()
    h = APP_HINTS.get(n)
    if h and h in inst:
        return h, []
    key = n.replace(" ", "")
    exact = sorted(p for p in inst if key in p.lower().split("."))
    if exact:
        return exact[0], exact
    part = sorted(p for p in inst if key in p.lower())
    return (part[0] if len(part) == 1 else None), part


def _tap_xy(x, y):
    _su(f"input tap {x} {y}")


SAFE_TYPE = re.compile(r"^[A-Za-z0-9 .,@_:/+=\-]*$")


def _type_text(txt):
    if not txt:
        return
    if SAFE_TYPE.match(txt):
        for i in range(0, len(txt), 40):
            _su("input text " + shlex.quote(txt[i:i + 40].replace(" ", "%s")))
        return
    if shutil.which("termux-clipboard-set"):
        subprocess.run(["termux-clipboard-set"], input=txt, text=True, timeout=15)
        time.sleep(0.4)
        _su("input keyevent 279")
        return
    if txt.isascii():
        for i in range(0, len(txt), 30):
            _su("input text " + shlex.quote(txt[i:i + 30].replace(" ", "%s")))
        return
    raise RuntimeError("Text with emoji/accents needs the clipboard: pkg install termux-api (and the Termux:API app).")


def _clear_field(n):
    dels = " ".join(["67"] * min(n + 3, 120))
    _su(f"input keycombination 113 29 >/dev/null 2>&1 && input keyevent 67 || (input keyevent 123; input keyevent {dels})")


def _screen_size():
    m = re.search(r"(\d+)x(\d+)", _su("wm size"))
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)


KEYS = {"back": 4, "home": 3, "enter": 66, "recent": 187, "delete": 67, "tab": 61, "search": 84,
        "copy": 278, "cut": 277, "paste": 279, "power": 26, "volup": 24, "voldown": 25, "menu": 82}


def t_ui(a):
    act = a.get("action", "")
    if act == "dump":
        nodes = _ui_nodes()
        rows = [f"#{i} {n['text'] or n['desc'] or n['id']} | id={n['id']} @{n['cx']},{n['cy']}"
                f"{' [tap]' if n['click'] else ''}{' [input]' if n['edit'] else ''}"
                for i, n in enumerate(nodes) if n["text"] or n["desc"] or n["click"] or n["edit"]]
        return clip((f"app: {nodes[0]['pkg']}\n" if nodes else "") + "\n".join(rows), 4500)
    if act == "read":
        seen, out = set(), []
        for n in _ui_nodes():
            for t in (n["text"], n["desc"]):
                if t and t not in seen:
                    seen.add(t)
                    out.append(t)
        return clip("\n".join(out) or "(no text on screen)", 4500)
    if act == "current":
        return clip(_su("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'") or "unknown", 400)
    if act == "apps":
        q = a.get("query", "").lower()
        inst = sorted(_installed())
        res = [p for p in inst if q in p.lower()] if q else [p for p in inst if not p.startswith(("com.android.", "android."))]
        return clip("\n".join(res[:80]) or f"No installed package contains '{q}'.", 3000)
    if act == "wait_for":
        end = time.time() + min(float(a.get("seconds", 10)), 40)
        while True:
            if _ui_find(_ui_nodes(), a["text"]):
                return f"'{a['text']}' is on screen." + _peek()
            if time.time() >= end:
                return f"Timed out: '{a['text']}' never appeared." + _peek(20)
            time.sleep(1)
    if act == "scroll_to":
        w, h = _screen_size()
        prev = None
        for _ in range(int(a.get("max", 8))):
            nodes = _ui_nodes()
            if _ui_find(nodes, a["text"]):
                return f"'{a['text']}' is on screen. Use tap_text to press it."
            labels = [n["text"] + n["desc"] for n in nodes]
            if labels == prev:
                return f"Reached the end; '{a['text']}' not found." + _peek(20)
            prev = labels
            y1, y2 = (0.75, 0.25) if a.get("direction", "down") == "down" else (0.25, 0.75)
            _su(f"input swipe {w//2} {int(h*y1)} {w//2} {int(h*y2)} 300")
            time.sleep(0.7)
        return f"'{a['text']}' not found after scrolling." + _peek(20)
    if act in ("tap_text", "tap_index", "long_press") and ("text" in a or "index" in a):
        deadline = time.time() + min(float(a.get("wait", 0)), 20)
        while True:
            nodes = _ui_nodes()
            if "index" in a and act != "tap_text":
                if int(a["index"]) >= len(nodes):
                    return "Index out of range. Use ui dump again."
                n = nodes[int(a["index"])]
                break
            hits = _ui_find(nodes, str(a["text"]))
            nth = int(a.get("nth", 0))
            if len(hits) > nth:
                n = hits[nth]
                break
            if time.time() >= deadline:
                return f"No element matching '{a['text']}'. Try scroll_to, wait_for, or a different label." + _peek(20)
            time.sleep(1)
        if act == "long_press":
            _su(f"input swipe {n['cx']} {n['cy']} {n['cx']} {n['cy']} 800")
        else:
            _tap_xy(n["cx"], n["cy"])
        time.sleep(1)
        return f"{'Long-pressed' if act == 'long_press' else 'Tapped'} '{n['text'] or n['desc'] or n['id']}'." + _peek()
    if act == "tap":
        _tap_xy(int(a["x"]), int(a["y"]))
        time.sleep(0.8)
        return "Tapped." + _peek()
    if act == "long_press":
        _su(f"input swipe {int(a['x'])} {int(a['y'])} {int(a['x'])} {int(a['y'])} 800")
        return "Long-pressed." + _peek()
    if act == "swipe":
        _su(f"input swipe {int(a['x1'])} {int(a['y1'])} {int(a['x2'])} {int(a['y2'])} {int(a.get('ms', 300))}")
        return "Swiped." + _peek()
    if act in ("scroll_down", "scroll_up"):
        w, h = _screen_size()
        y1, y2 = (0.75, 0.25) if act == "scroll_down" else (0.25, 0.75)
        _su(f"input swipe {w//2} {int(h*y1)} {w//2} {int(h*y2)} 300")
        time.sleep(0.6)
        return "Scrolled." + _peek()
    if act == "type":
        txt = str(a.get("text", ""))
        if a.get("into") or a.get("text_field") or a.get("clear"):
            nodes = _ui_nodes()
            edits = [n for n in nodes if n["edit"]]
            tgt = None
            if a.get("into"):
                c = _ui_find(edits, str(a["into"])) or _ui_find(nodes, str(a["into"]))
                tgt = c[0] if c else None
            if tgt is None:
                tgt = next(iter([n for n in edits if n["focused"]] or edits), None)
            if tgt is None and (a.get("into") or a.get("text_field")):
                return "No input field on screen. Use ui dump."
            if tgt:
                _tap_xy(tgt["cx"], tgt["cy"])
                time.sleep(0.4)
                if a.get("clear"):
                    _clear_field(len(tgt["text"]))
        _type_text(txt)
        if a.get("submit"):
            _su("input keyevent 66")
        time.sleep(0.6)
        return "Typed." + _peek()
    if act == "key":
        k = str(a.get("name", "")).lower()
        _su(f"input keyevent {KEYS.get(k, k)}")
        time.sleep(0.6)
        return f"Pressed {k}." + _peek()
    if act == "open_app":
        pkg, cands = _pkg_for(a.get("package") or a.get("name") or "")
        if not pkg:
            return ("No single installed app matches. Candidates: " + ", ".join(cands[:8])) if cands else \
                   "No installed app matches that name. Use ui apps {query} to search packages."
        out = _su(f"monkey -p {shlex.quote(pkg)} -c android.intent.category.LAUNCHER 1")
        if "No activities found" in out:
            return f"{pkg} has no launcher activity."
        time.sleep(2)
        return f"Launched {pkg}." + _peek()
    if act == "wait":
        time.sleep(min(float(a.get("seconds", 2)), 30))
        return "Waited." + _peek()
    if act == "screenshot":
        p = a.get("path", "/sdcard/screen.png")
        _su(f"screencap -p {shlex.quote(p)}")
        return "Saved screenshot to " + p
    return ("Unknown ui action. Use: dump, read, current, apps{query}, open_app{package|name}, tap_text{text,nth?,wait?}, "
            "tap_index{index}, tap{x,y}, long_press, swipe, scroll_down, scroll_up, scroll_to{text}, wait_for{text}, "
            "type{text,into?,clear?,submit?}, key{name}, wait, screenshot.")


EMERGENCY = {"911", "112", "999", "000", "110", "119", "100", "101", "102", "108", "15", "17", "18"}
_ROOT = {}


def _has_root():
    if "v" not in _ROOT:
        try:
            _ROOT["v"] = subprocess.run(["su", "-c", "id -u"], capture_output=True, text=True, timeout=8).stdout.strip() == "0"
        except Exception:
            _ROOT["v"] = False
    return _ROOT["v"]


def _api(args, timeout=40):
    if not shutil.which(args[0]):
        raise RuntimeError(f"{args[0]} not found. Run: pkg install termux-api, install the Termux:API app (F-Droid) "
                           "and grant it the Contacts, SMS, Phone and Notification permissions.")
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0 and not p.stdout.strip():
        raise RuntimeError((p.stderr or "command failed").strip()[:300])
    return p.stdout


def _json_api(args, timeout=40):
    out = _api(args, timeout).strip()
    return json.loads(out) if out else []


def _digits(n):
    n = str(n).strip()
    return ("+" if n.startswith("+") else "") + re.sub(r"\D", "", n)


def _lookup(q):
    q = q.lower().strip()
    seen, out = set(), []
    for c in _json_api(["termux-contact-list"]):
        nm, num = c.get("name") or "", _digits(c.get("number") or "")
        if q in nm.lower() and num and (nm, num) not in seen:
            seen.add((nm, num))
            out.append((nm, num))
    return out


def _name_for(num):
    try:
        tail = re.sub(r"\D", "", num)[-8:]
        for c in _json_api(["termux-contact-list"]):
            if tail and re.sub(r"\D", "", c.get("number") or "").endswith(tail):
                return c.get("name") or num
    except Exception:
        pass
    return num


def _resolve(to):
    to = str(to).strip()
    if re.fullmatch(r"[+\d][\d\s\-().]{4,}", to):
        return _digits(to), to
    m = _lookup(to)
    if not m:
        raise RuntimeError(f"No contact matches '{to}'. Ask the user for the number.")
    if len({d for _, d in m}) > 1:
        raise RuntimeError("Several contacts match. Ask the user which one:\n" + "\n".join(f"- {n} {d}" for n, d in m[:8]))
    return m[0][1], m[0][0]


def _ts(v):
    try:
        v = float(v)
        return time.strftime("%m-%d %H:%M", time.localtime(v / 1000 if v > 1e11 else v))
    except Exception:
        return str(v)[:16]


def t_contacts(a):
    q = a.get("query", "").strip()
    rows = _lookup(q) if q else [(c.get("name", ""), _digits(c.get("number", ""))) for c in _json_api(["termux-contact-list"])]
    return clip("\n".join(f"{n}: {d}" for n, d in rows[:30]) or f"No contact matches '{q}'.", 2500)


def t_inbox(a):
    src = str(a.get("source", "sms")).lower()
    limit = min(int(a.get("limit", 10)), 30)
    frm = str(a.get("from") or "").lower()
    if src.startswith("call"):
        rows = _json_api(["termux-call-log", "-l", str(limit)])
        return clip("\n".join(f"{_ts(r.get('date'))} | {r.get('type')} | {r.get('name') or r.get('phone_number')} "
                              f"| {r.get('duration', '')}s" for r in rows) or "Call log empty.", 3000)
    if src.startswith("notif"):
        app = str(a.get("app") or "").lower()
        rows = []
        for n in _json_api(["termux-notification-list"]):
            pkg = n.get("packageName") or ""
            text = f"{n.get('title', '')}: {n.get('content', '')}"
            if (app and app not in pkg.lower()) or (frm and frm not in text.lower()):
                continue
            rows.append(f"{pkg.split('.')[-1]} | {text[:220]}")
        return clip("\n".join(rows[-limit:]) or "No matching notifications (Termux:API needs notification access).", 3500)
    fetch = 100 if (frm or a.get("unread")) else limit
    out = []
    for m in _json_api(["termux-sms-list", "-d", "-n", "-t", a.get("box", "inbox"), "-l", str(fetch)]):
        who = f"{m.get('sender') or ''} {m.get('number') or ''}".strip()
        if frm and frm not in who.lower():
            continue
        if a.get("unread") and m.get("read") is not False:
            continue
        out.append(f"{_ts(m.get('received'))} | {who} | {'UNREAD ' if m.get('read') is False else ''}{(m.get('body') or '')[:220]}")
    return clip("\n".join(out[:limit]) or "No matching messages.", 3500)


def msg_plan(a):
    app = str(a.get("app") or "sms").lower().replace(" ", "")
    text = str(a.get("text", "")).strip()
    if not text or not a.get("to"):
        raise RuntimeError("message needs both 'to' and 'text'.")
    if app not in ("sms", "whatsapp"):
        raise RuntimeError("message supports app=sms or whatsapp. For other apps use ui: open_app, tap_text on the chat, "
                           "type the text, and ask the user before tapping Send.")
    num, disp = _resolve(a["to"])
    return {"app": app, "num": num, "disp": disp, "text": text,
            "desc": f"{app} to {disp} ({num}):\n{text}"}


def _am_view(url, pkg=None):
    cmd = ["am", "start", "-a", "android.intent.action.VIEW", "-d", url] + (["-p", pkg] if pkg else [])
    if shutil.which("am"):
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and "Error" not in r.stdout + r.stderr:
            return True
    if _has_root():
        _su(" ".join(shlex.quote(x) for x in cmd))
        return True
    return False


def msg_send(p):
    if p["app"] == "sms":
        _api(["termux-sms-send", "-n", p["num"], p["text"]])
        time.sleep(2)
        try:
            ok = any(p["text"][:30] in (m.get("body") or "") for m in _json_api(["termux-sms-list", "-t", "sent", "-l", "3"]))
        except Exception:
            ok = False
        return f"SMS sent to {p['disp']}." + (" Confirmed in the Sent folder." if ok else " Could not confirm in Sent; check inbox sent box later.")
    digits = re.sub(r"\D", "", p["num"])
    url = "https://wa.me/" + digits + "?text=" + urllib.parse.quote(p["text"])
    if not _am_view(url, "com.whatsapp"):
        return "Could not open WhatsApp from Termux. Open it yourself; the message is: " + p["text"]
    if not _has_root():
        return "WhatsApp chat opened with the message ready. Without root I cannot tap Send: ask the user to press Send."
    time.sleep(4)
    for _ in range(6):
        nodes = _ui_nodes()
        screen = " ".join(n["text"] + " " + n["desc"] for n in nodes).lower()
        if "isn't on whatsapp" in screen or "not on whatsapp" in screen or "invalid" in screen:
            return "WhatsApp says that number is not on WhatsApp. Nothing was sent." + _peek()
        send = [n for n in nodes if n["click"] and (n["id"] == "send" or n["desc"].lower().startswith("send"))]
        if send:
            _tap_xy(send[0]["cx"], send[0]["cy"])
            time.sleep(2)
            after = " ".join(n["text"] for n in _ui_nodes())
            ok = p["text"][:25] in after
            return f"WhatsApp message to {p['disp']} sent." + (" Message visible in the chat." if ok else " Could not confirm it in the chat; check.")
        time.sleep(1.5)
    return "WhatsApp opened but the Send button was not found." + _peek(20)


def _call_state():
    try:
        return str(_json_api(["termux-telephony-deviceinfo"]).get("call_state", "unknown"))
    except Exception:
        if _has_root():
            m = re.search(r"mCallState=(\d)", _su("dumpsys telephony.registry"))
            return {"0": "idle", "1": "ringing", "2": "offhook"}.get(m.group(1), "unknown") if m else "unknown"
        return "unknown"


def t_call(a, auto):
    act = a.get("action", "")
    if act == "dial":
        if re.sub(r"\D", "", str(a.get("to", ""))) in EMERGENCY:
            return "Refusing to place emergency calls automatically. Tell the user to dial that number themselves."
        num, disp = _resolve(a.get("to", ""))
        if re.sub(r"\D", "", num) in EMERGENCY:
            return "Refusing to place emergency calls automatically. Tell the user to dial that number themselves."
        if not approve(f"PLACE A PHONE CALL to {disp} ({num})", {"on": False}):
            return "User denied."
        try:
            _api(["termux-telephony-call", num])
            how = "placed"
        except Exception as e:
            uri = shlex.quote("tel:" + urllib.parse.quote(num))
            if _has_root():
                _su(f"am start -a android.intent.action.CALL -d {uri}")
                how = "placed (root intent)"
            elif _am_view("tel:" + urllib.parse.quote(num)):
                return f"Opened the dialer with {disp} filled in. The user must press the call button. ({e})"
            else:
                return f"Could not place the call: {e}"
        time.sleep(3)
        return f"Call to {disp} {how}. Call state: {_call_state()}."
    if act == "status":
        return "Call state: " + _call_state()
    if act in ("hangup", "answer"):
        if act == "answer" and not approve("ANSWER the incoming call", auto):
            return "User denied."
        if not _has_root():
            return "Needs root to press the call keys. Ask the user to do it."
        _su("input keyevent " + ("6" if act == "hangup" else "5"))
        time.sleep(1)
        return f"{act} done. Call state: {_call_state()}."
    return "Unknown call action. Use: dial{to}, hangup, answer, status."


def t_clipboard(a):
    if a.get("action") == "set":
        subprocess.run(["termux-clipboard-set"], input=a.get("text", ""), text=True, timeout=15)
        return "Clipboard set."
    p = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, timeout=15)
    return clip(p.stdout or "(clipboard empty)")


def t_download(a):
    p = os.path.expanduser(a["path"])
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    req = urllib.request.Request(a["url"], headers={"User-Agent": UA})
    total = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(p, "wb") as f:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            f.write(c)
            total += len(c)
    return f"Downloaded {total} bytes to {p}"


def _gh(path, raw=False):
    h = {"User-Agent": UA, "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(GITHUB_API + path, headers=h), timeout=25) as r:
        body = r.read().decode("utf-8", "ignore")
    return body if raw else json.loads(body)


def t_github(a):
    act = a.get("action", "")
    if act == "search":
        d = _gh("/search/repositories?per_page=8&sort=stars&q=" + urllib.parse.quote(a["query"]))
        return clip("\n".join(f"{i['full_name']} *{i['stargazers_count']} - {(i.get('description') or '')[:90]}"
                              for i in d.get("items", [])) or "No repos found.")
    if act == "readme":
        return clip(_gh(f"/repos/{a['repo']}/readme", raw=True), 4500)
    if act == "tree":
        d = _gh(f"/repos/{a['repo']}/contents/{a.get('path', '')}")
        d = d if isinstance(d, list) else [d]
        return clip("\n".join(f"{i['type']} {i['path']}" for i in d))
    if act == "file":
        return clip(_gh(f"/repos/{a['repo']}/contents/{a['path']}", raw=True), 5000)
    if act == "clone":
        dest = os.path.expanduser(a.get("dest", "~/" + a["repo"].split("/")[-1]))
        return clip(t_shell({"cmd": f"git clone --depth 1 https://github.com/{shlex.quote(a['repo'])} {shlex.quote(dest)}"}))
    return "Unknown github action. Use: search{query}, readme{repo}, tree{repo,path?}, file{repo,path}, clone{repo,dest?}."


def t_install(a):
    mgr, name = a.get("manager", "auto"), a.get("name", "")
    if not re.fullmatch(r"[\w.+\-@/=\[\], ]+", name):
        return "Invalid package name."
    if mgr == "auto":
        mgr = "apt" if (os.environ.get("PREFIX", "").find("com.termux") == -1 and shutil.which("apt")) else "pkg"
    cmd = {"pkg": "pkg install -y ", "apt": "apt-get install -y ", "pip": "pip install --break-system-packages ",
           "npm": "npm install -g "}.get(mgr)
    if not cmd:
        return "manager must be pkg, apt, pip, or npm."
    p = subprocess.run(cmd + name, shell=True, capture_output=True, text=True, timeout=900)
    return clip(f"exit={p.returncode}\n{p.stdout[-1200:]}{p.stderr[-1200:]}")


SEC_TOOLS = ["nmap", "hydra", "john", "hashcat", "aircrack-ng", "sqlmap", "gobuster", "nikto", "wireshark",
             "tshark", "msfconsole", "burpsuite", "zaproxy", "wpscan", "netcat", "nc", "tcpdump", "proxychains4",
             "searchsploit", "dirb", "wfuzz", "binwalk", "radare2", "r2", "gdb", "openssl", "git", "python3",
             "ruby", "go", "proot-distro"]


def _in_termux():
    return "com.termux" in os.environ.get("PREFIX", "") or os.path.isdir("/data/data/com.termux/files/usr")


def envinfo(_a=None):
    lines = []
    termux = _in_termux()
    lines.append(f"Base OS: {'Termux (Android)' if termux else 'Linux (not Termux - likely inside a proot-distro chroot or a real Linux box)'}")
    if termux:
        lines.append("Package manager here: pkg (= apt wrapper for the Termux repo). Use 'pkg install <name>'.")
        chroots = []
        pd = shutil.which("proot-distro")
        if pd:
            r = subprocess.run(["proot-distro", "list"], capture_output=True, text=True, timeout=20)
            chroots = [l.strip() for l in r.stdout.splitlines() if "installed" in l.lower() or "*" in l]
        lines.append("proot-distro: " + ("installed, distros: " + "; ".join(chroots[:10]) if pd else
                     "not installed. To get a full Kali toolset: pkg install proot-distro && proot-distro install kali"))
        lines.append("To work inside Kali once installed: proot-distro login kali   (then use apt, not pkg, "
                      "and install tool sets with e.g. apt install kali-tools-top10, or a single tool like apt install nmap)")
    else:
        lines.append("Package manager here: apt/apt-get (Debian/Kali-style). Use 'apt-get install -y <name>' or manager:apt.")
    root = bool(shutil.which("su") or shutil.which("tsu"))
    lines.append(f"Root: {'su/tsu available, try root {cmd} for things Termux alone cannot do' if root else 'no su/tsu found - root tool will fail'}")
    found = [t for t in SEC_TOOLS if shutil.which(t)]
    missing = [t for t in SEC_TOOLS if t not in found]
    lines.append("Security tools found on PATH: " + (", ".join(found) if found else "none of the common ones"))
    if missing:
        lines.append("Not found (install with pkg/apt, or inside the Kali chroot): " + ", ".join(missing[:15]))
    lines.append("Storage: " + ("termux-setup-storage has been run (~/storage exists)" if os.path.isdir(os.path.expanduser("~/storage"))
                 else "run termux-setup-storage once to access the phone's shared storage" if termux else "n/a"))
    return "\n".join(lines)


def t_research(a):
    q = a["query"]
    res = t_search({"query": q})
    out = ["SEARCH RESULTS:\n" + res]
    for line in res.splitlines()[:2]:
        if " - http" not in line:
            continue
        url = line.split(" - ", 1)[1].strip()
        try:
            out.append(f"\nPAGE {url}:\n" + t_fetch({"url": url})[:1500])
        except Exception as e:
            out.append(f"\nPAGE {url}: failed ({e})")
    return clip("\n".join(out), 5000)


def approve(desc, auto):
    if auto["on"]:
        return True
    ui_ask(desc)
    r = ask_line("[y]es / [n]o / [a]lways this session: ").strip().lower()
    if r == "a":
        auto["on"] = True
    return r in ("y", "a")


def _tool_names():
    import inspect
    names = set(re.findall(r'name == "(\w+)"', inspect.getsource(run_tool))) | set(PLUGINS) | {"finish"}
    return names


def run_tool(name, a, auto):
    try:
        if name == "read_doc":
            return t_read_doc(a)
        if name == "learn":
            return t_learn(a)
        if name == "recall":
            return t_recall(a)
        if name == "kb":
            return t_kb(a, auto)
        if name == "translate":
            return t_translate(a)
        if name == "envinfo":
            return envinfo(a)
        if name == "study":
            return t_study(a, auto)
        if name == "audit":
            return t_audit(a, auto)
        if name == "verify":
            return t_verify(a, auto)
        if name == "undo":
            return t_undo(a)
        if name == "nano":
            return t_nano(a) if approve(f"open nano for YOU to review/edit {a.get('path')}", auto) else "User denied."
        if name == "check":
            return t_check(a)
        if name == "view":
            return t_view(a)
        if name == "patch_lines":
            return t_patch_lines(a) if approve(_desc("patch_lines", a, f"patch {a.get('path')} lines {a.get('start')}-{a.get('end', a.get('start'))}"), auto) else "User denied."
        if name == "debug":
            return t_debug(a) if approve("run for debugging: " + str(a.get("path")), auto) else "User denied."
        if name == "cve_check":
            return t_cve_check(a)
        if name == "ui":
            act = a.get("action")
            risky = act in ("tap_text", "long_press") and re.match(
                r"(?i)\s*(send|call|dial|pay|buy|purchase|confirm|delete|post|tweet|publish|place order|transfer|submit)\b",
                str(a.get("text", "")))
            if risky:
                if not approve("IRREVERSIBLE-LOOKING TAP: " + clip(json.dumps(a), 300), {"on": False}):
                    return "User denied."
            elif act not in ("dump", "read", "current", "apps", "wait_for", "wait", "screenshot", "scroll_down",
                             "scroll_up", "scroll_to") and not approve("ui " + clip(json.dumps(a), 300), auto):
                return "User denied."
            return t_ui(a)
        if name == "contacts":
            return t_contacts(a)
        if name == "inbox":
            return t_inbox(a)
        if name == "message":
            plan = msg_plan(a)
            if not approve("SEND MESSAGE\n" + plan["desc"], {"on": False}):
                return "User denied."
            return msg_send(plan)
        if name == "call":
            return t_call(a, auto)
        if name == "clipboard":
            if a.get("action") == "set" and not approve("set clipboard", auto):
                return "User denied."
            return t_clipboard(a)
        if name == "download":
            return t_download(a) if approve(f"download {a.get('url')} -> {a.get('path')}", auto) else "User denied."
        if name == "github":
            if a.get("action") == "clone" and not approve("git clone " + str(a.get("repo")), auto):
                return "User denied."
            return t_github(a)
        if name == "install":
            return t_install(a) if approve(f"install {a.get('manager','pkg')}: {a.get('name')}", auto) else "User denied."
        if name == "research":
            return t_research(a)
        if name == "browser":
            if a.get("action") in ("js", "click", "type", "storage", "press", "select") and not approve(
                    "browser " + clip(json.dumps(a), 300), auto):
                return "User denied."
            return t_browser(a)
        if name == "http":
            if a.get("method", "GET").upper() not in ("GET", "HEAD") and not approve(
                    "HTTP " + clip(json.dumps(a), 300), auto):
                return "User denied."
            return t_http(a)
        if name == "root":
            cmd = a.get("cmd", "")
            if any(re.search(b, cmd) for b in BLOCK):
                return "Blocked: dangerous command."
            if not approve("ROOT: " + cmd, {"on": False}):
                return "User denied."
            return t_root(a)
        if name == "shell":
            cmd = a.get("cmd", "")
            if any(re.search(b, cmd) for b in BLOCK):
                return "Blocked: dangerous command."
            if re.search(r"(^|[;&|]\s*)(su|tsu|sudo)(\s|$)", cmd):
                if not approve("ROOT via shell: " + cmd, {"on": False}):
                    return "User denied."
                return t_shell(a)
            if not cmd.strip().startswith(SAFE) and not approve("shell: " + cmd, auto):
                return "User denied. Try another way or ask the user."
            return t_shell(a)
        if name == "python":
            return t_python(a) if approve("run python:\n" + clip(a.get("code", ""), 500), auto) else "User denied."
        if name == "write_file":
            return t_write(a) if approve(_desc("write_file", a, f"write {a.get('path')}"), auto) else "User denied."
        if name == "edit_file":
            return t_edit(a) if approve(_desc("edit_file", a, f"edit {a.get('path')}"), auto) else "User denied."
        if name == "read_file":
            rp = resolve(a["path"])
            if already_loaded("read", rp):
                return LOADED_MSG
            return clip(open(rp, errors="ignore").read(), 4000)
        if name == "search":
            return t_search(a)
        if name == "fetch":
            return t_fetch(a)
        if name == "remember":
            return t_remember(a)
        if name == "create_tool":
            ok = approve(f"CREATE NEW TOOL '{a.get('name')}':\n{clip(a.get('code',''), 800)}", {"on": False})
            return t_create_tool(a) if ok else "User denied."
        if name == "self_edit":
            ok = approve(f"EDIT MY OWN SOURCE:\n--- old\n{clip(a.get('old',''),400)}\n+++ new\n{clip(a.get('new',''),600)}", {"on": False})
            return t_self_edit(a) if ok else "User denied."
        if name == "restart":
            if approve("restart agent", {"on": False}):
                print("Restarting...")
                os.execv(sys.executable, [sys.executable, SELF] + sys.argv[1:])
            return "User denied."
        if name in PLUGINS:
            return clip(str(PLUGINS[name][1](a))) if approve(f"run custom tool {name} {clip(json.dumps(a), 200)}", auto) else "User denied."
        low = str(name).lower()
        if low in ("am", "open", "open_app", "openapp", "launch", "launch_app", "start", "start_app", "monkey"):
            target = a.get("package") or a.get("name") or a.get("app")
            if target:
                return run_tool("ui", {"action": "open_app", "package": target, "name": target}, auto)
        if low in ("pm", "input", "svc", "settings", "dumpsys", "getprop", "cmd") and a.get("cmd"):
            return run_tool("root", {"cmd": f"{low} {a['cmd']}"}, auto)
        return f"Unknown tool '{name}'. It is not a tool. Valid tools: {', '.join(sorted(_tool_names()))}. Shell commands must go through shell or root."
    except Exception as e:
        return f"Tool error: {type(e).__name__}: {e}"


def run_task(task, hist, auto):
    ctx = kb_context(task)
    hist.append({"role": "user", "content": task + ctx})
    if ctx:
        ui_note("recalled relevant knowledge")
    fails = 0
    nf = 0
    last_sig, repeats = None, 0
    for step in range(MAX_STEPS):
        try:
            raw = think_safe(build_system(), hist)
        except Exception as e:
            ui_error(f"Ollama error: {e}\nIs 'ollama serve' running?")
            hist.pop()
            return
        hist.append({"role": "assistant", "content": raw})
        try:
            i = raw.find("{")
            d, _ = json.JSONDecoder().raw_decode(raw[i:])
            tool, args = d["tool"], d.get("args", {})
            args = args if isinstance(args, dict) else {}
        except Exception:
            hist.append({"role": "user", "content": 'Invalid. Reply with ONE JSON object: {"thought": "...", "tool": "...", "args": {...}}'})
            continue
        if tool == "finish":
            ans = str(args.get("answer", "Done."))
            ui_answer(ans)
            return
        sig = (tool, json.dumps(args, sort_keys=True, default=str))
        repeats = repeats + 1 if sig == last_sig else 0
        last_sig = sig
        if repeats >= 2:
            ui_error(f"Stopped: the model kept repeating the same step ({tool}). Rephrase the task or use a bigger model.")
            return
        ui_tool(tool, args)
        _STEP[0] += 1
        res = run_tool(tool, args, auto)
        bad = res.startswith(("Tool error", "Edit failed", "Blocked", "User denied", "Unknown tool")) or re.match(r"exit=[1-9]", res)
        ui_result(res, bool(bad))
        fails = fails + 1 if bad else 0
        nf = nf + 1 if "File not found" in res else 0
        if nf >= 3:
            ui_error("Stopped: the model keeps guessing file paths that do not exist. Give it the exact path.")
            return
        note = "\nRepeated failures. STOP, re-read the error, and change your approach (or build a tool)." if fails >= 2 else ""
        hist.append({"role": "user", "content": "Tool result:\n" + res + note})
    log("\n  ⚠ step limit reached - send a follow-up to continue", BYL)


def main():
    load_plugins()
    auto = {"on": False}
    hist = []
    try:
        auto_study_knowledge(quiet=len(sys.argv) > 1)
    except Exception as e:
        print("[knowledge] skipped auto-study: " + str(e)[:150])
    if len(sys.argv) > 1:
        run_task(" ".join(sys.argv[1:]), hist, auto)
        return
    interactive_console(hist, auto)


if __name__ == "__main__":
    main()
