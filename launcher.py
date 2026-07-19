#!/usr/bin/env python3
#
# Launcher — a quick command bar with web search, an embedded browser, and
# multi-provider AI chat (OpenAI, Claude, Kimi, OpenRouter, …).
#
# Author:  Lehman <3ma.reds@gmail.com>
# Support: https://buymeacoffee.com/lehman
# License: MIT
#
import os, sys, signal as _signal
os.environ['GDK_BACKEND'] = 'x11'

import json, threading, urllib.request, urllib.error, urllib.parse
from pathlib import Path

APP_ID  = 'io.github.lehman.Launcher'
APP_URL = 'https://buymeacoffee.com/lehman'

def data_file(name):
    """Locate a bundled data file (home.html) across dev and installed layouts."""
    here = Path(__file__).resolve().parent
    for c in (here / name,
              here.parent / 'share' / APP_ID / name,   # <prefix>/bin + <prefix>/share/<id>
              Path('/app/share') / APP_ID / name,       # Flatpak
              Path('/usr/share') / APP_ID / name,
              Path('/usr/local/share') / APP_ID / name):
        if c.exists():
            return c
    return here / name

# ── Daemon / single-instance ─────────────────────────────────────────────────
PID_FILE = os.path.join(os.environ.get('XDG_RUNTIME_DIR') or '/tmp', 'launcher.pid')

def _signal_existing():
    try:
        pid = int(open(PID_FILE).read())
        os.kill(pid, _signal.SIGUSR1)
        return True
    except Exception:
        return False

if _signal_existing():
    sys.exit(0)

with open(PID_FILE, 'w') as f:
    f.write(str(os.getpid()))

import atexit
atexit.register(lambda: os.path.exists(PID_FILE) and os.unlink(PID_FILE))

# ── Config ───────────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / '.config' / 'launcher' / 'config.json'

# AI providers. `format` selects the wire protocol:
#   'openai'    → OpenAI-compatible /chat/completions (OpenAI, Moonshot/Kimi, custom)
#   'anthropic' → Anthropic /v1/messages (Claude)
PROVIDERS = {
    'openai':    {'label': 'OpenAI',                    'format': 'openai',
                  'url': 'https://api.openai.com/v1/chat/completions',   'default_model': 'gpt-4o-mini'},
    'anthropic': {'label': 'Claude (Anthropic)',        'format': 'anthropic',
                  'url': 'https://api.anthropic.com/v1/messages',        'default_model': 'claude-opus-4-8'},
    'moonshot':  {'label': 'Kimi (Moonshot)',           'format': 'openai',
                  'url': 'https://api.moonshot.ai/v1/chat/completions',  'default_model': 'kimi-latest'},
    'openrouter':{'label': 'OpenRouter',                'format': 'openai',
                  'url': 'https://openrouter.ai/api/v1/chat/completions', 'default_model': 'openai/gpt-4o-mini'},
    'custom':    {'label': 'Custom (OpenAI-compatible)', 'format': 'openai',
                  'url': '',                                             'default_model': ''},
}

SEARCH_ENGINES = {
    'google':     'https://www.google.com/search?q=',
    'duckduckgo': 'https://duckduckgo.com/?q=',
    'bing':       'https://www.bing.com/search?q=',
}

def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text())
    except Exception:
        data = {}
    # Migrate the old flat {api_key, model} shape → per-provider structure.
    if 'providers' not in data:
        providers = {}
        if data.get('api_key') or data.get('model'):
            providers['openai'] = {'api_key': data.get('api_key', ''),
                                   'model': data.get('model', 'gpt-4o-mini')}
        data = {'provider': 'openai', 'providers': providers}
    data.setdefault('provider', 'openai')
    data.setdefault('providers', {})
    data.setdefault('search_engine', 'duckduckgo')
    return data

def save_config(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))

cfg           = load_config()
PROVIDER      = cfg.get('provider', 'openai')
SEARCH_ENGINE = cfg.get('search_engine', 'duckduckgo')

# ── Conversation history (AI mode) ────────────────────────────────────────────
CONV_PATH = CONFIG_PATH.parent / 'conversations.json'

def load_conversations():
    try:
        data = json.loads(CONV_PATH.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_conversations():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONV_PATH.write_text(json.dumps(conversations, indent=2))

conversations = load_conversations()

# ── GTK / WebKit ─────────────────────────────────────────────────────────────
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, Gdk, GLib

content_manager = WebKit2.UserContentManager()
content_manager.register_script_message_handler('launcher')

win = Gtk.Window()
win.set_decorated(False)
win.set_type_hint(Gdk.WindowTypeHint.SPLASHSCREEN)
win.set_default_size(640, 84)
win.set_keep_above(True)
win.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
win.set_app_paintable(True)
screen = win.get_screen()
visual = screen.get_rgba_visual()
if visual:
    win.set_visual(visual)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
win.add(box)

# launcher_wv fills the whole window by default (expand=True).
# When the page viewer is open we lock it to 56px via set_child_packing().
launcher_wv = WebKit2.WebView.new_with_user_content_manager(content_manager)
launcher_wv.set_background_color(Gdk.RGBA(0, 0, 0, 0))
s = launcher_wv.get_settings()
s.set_enable_plugins(False)
s.set_enable_java(False)
s.set_enable_webgl(False)
s.set_enable_media_stream(False)
box.pack_start(launcher_wv, True, True, 0)   # expand=True → fills window
launcher_wv.load_uri(data_file('home.html').as_uri())

# Page viewer — shown only while browsing.
# Give it its own content manager so we can inject a stylesheet that hides
# Google's "One Tap" sign-in prompt (the floating box that nags on every visit).
page_cm = WebKit2.UserContentManager()
page_cm.add_style_sheet(WebKit2.UserStyleSheet.new(
    """
    #credential_picker_container,
    #credentials-picker-container,
    div[id^="credential_picker"],
    iframe[src*="accounts.google.com/gsi"],
    div[aria-label="Sign in to Google"] { display: none !important; }
    """,
    WebKit2.UserContentInjectedFrames.ALL_FRAMES,
    WebKit2.UserStyleLevel.USER,
    None, None))
page_wv = WebKit2.WebView.new_with_user_content_manager(page_cm)
page_wv.set_no_show_all(True)
# A modern desktop user-agent stops Google from flagging the embedded browser
# as insecure and cuts down on sign-in nagging.
page_wv.get_settings().set_user_agent(
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
# Persist cookies across runs. A fresh, cookie-less session every launch looks
# like bot traffic to Google and is a major "unusual traffic" captcha trigger.
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
try:
    page_wv.get_context().get_cookie_manager().set_persistent_storage(
        str(CONFIG_PATH.parent / 'cookies.sqlite'),
        WebKit2.CookiePersistentStorage.SQLITE)
except Exception:
    pass
box.pack_start(page_wv, True, True, 0)

# ── Layout helpers ────────────────────────────────────────────────────────────
def launcher_fill():
    """launcher_wv expands to fill the whole window."""
    launcher_wv.set_size_request(-1, -1)
    box.set_child_packing(launcher_wv, True, True, 0, Gtk.PackType.START)

def launcher_bar():
    """launcher_wv is fixed to 56px; page_wv fills the rest."""
    launcher_wv.set_size_request(-1, 56)
    box.set_child_packing(launcher_wv, False, False, 0, Gtk.PackType.START)

# ── Helpers ───────────────────────────────────────────────────────────────────
def run_js(code):
    launcher_wv.evaluate_javascript(code, len(code), None, None, None, None, None)
    return False

def close_page():
    launcher_fill()
    page_wv.hide()
    page_wv.load_uri('about:blank')
    win.resize(640, 84)
    GLib.idle_add(run_js, 'setBrowsing(false)')
    return False

page_wv.connect('key-press-event',
    lambda _, e: (GLib.idle_add(close_page), True)[1] if e.keyval == Gdk.KEY_Escape else False)

# Ctrl+C closes from anywhere
accel = Gtk.AccelGroup()
accel.connect(Gdk.KEY_c, Gdk.ModifierType.CONTROL_MASK, 0, lambda *_: Gtk.main_quit())
win.add_accel_group(accel)

# ── SIGUSR1 toggle (daemon mode) ──────────────────────────────────────────────
def _toggle(*_):
    if win.get_visible():
        close_page()
        win.hide()
    else:
        GLib.idle_add(run_js, 'resetState()')
        win.show_all()
        win.present()
    return True

GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, _signal.SIGUSR1, _toggle)

# ── AI streaming ──────────────────────────────────────────────────────────────
def _stream_openai(url, api_key, model, messages):
    body = json.dumps({"model": model, "messages": messages, "stream": True}).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith('data: '):
                continue
            chunk = line[6:]
            if chunk == '[DONE]':
                GLib.idle_add(run_js, 'streamDone()')
                break
            try:
                delta = json.loads(chunk)['choices'][0]['delta'].get('content', '')
                if delta:
                    GLib.idle_add(run_js, f'appendChunk({json.dumps(delta)})')
            except Exception:
                pass

def _stream_anthropic(url, api_key, model, messages):
    body = json.dumps({"model": model, "max_tokens": 4096,
                       "messages": messages, "stream": True}).encode()
    req = urllib.request.Request(url, data=body, headers={
        'x-api-key': api_key, 'anthropic-version': '2023-06-01',
        'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith('data:'):
                continue
            try:
                evt = json.loads(line[5:].strip())
            except Exception:
                continue
            if evt.get('type') == 'content_block_delta':
                delta = evt.get('delta', {})
                if delta.get('type') == 'text_delta' and delta.get('text'):
                    GLib.idle_add(run_js, f'appendChunk({json.dumps(delta["text"])})')
            elif evt.get('type') == 'message_stop':
                GLib.idle_add(run_js, 'streamDone()')

def call_ai(messages):
    spec    = PROVIDERS.get(PROVIDER, PROVIDERS['openai'])
    pc      = cfg.get('providers', {}).get(PROVIDER, {})
    api_key = pc.get('api_key', '')
    model   = pc.get('model') or spec['default_model']
    url     = pc.get('base_url') or spec['url']
    try:
        if not url:
            raise ValueError('No API endpoint configured for this provider.')
        if spec['format'] == 'anthropic':
            _stream_anthropic(url, api_key, model, messages)
        else:
            _stream_openai(url, api_key, model, messages)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode()[:500]
        except Exception:
            detail = str(e)
        GLib.idle_add(run_js, f'streamError({json.dumps(detail)})')
    except Exception as e:
        GLib.idle_add(run_js, f'streamError({json.dumps(str(e))})')

# ── Message handler ───────────────────────────────────────────────────────────
def on_message(_, result):
    global PROVIDER, SEARCH_ENGINE
    try:
        msg = json.loads(result.get_js_value().to_string())
    except Exception:
        return
    action = msg.get('action')

    if action == 'startMove':
        win.begin_move_drag(1, msg.get('x', 0), msg.get('y', 0), Gdk.CURRENT_TIME)
    elif action == 'browse':
        launcher_bar()          # lock launcher to 56px
        page_wv.show()
        win.resize(1100, 700)
        url = msg.get('url')
        if not url:
            base = SEARCH_ENGINES.get(SEARCH_ENGINE, SEARCH_ENGINES['google'])
            url = base + urllib.parse.quote(msg.get('query', ''))
        page_wv.load_uri(url)
    elif action == 'closeBrowse':
        GLib.idle_add(close_page)
    elif action == 'ai':
        threading.Thread(target=call_ai, args=(msg['messages'],), daemon=True).start()
    elif action == 'expand':
        launcher_fill()         # let launcher fill the window
        page_wv.hide()
        win.resize(int(msg.get('w', 640)), int(msg.get('h', 420)))
    elif action == 'collapse':
        launcher_fill()
        win.resize(640, 84)
    elif action == 'getConfig':
        def _mask(k):
            return ('*' * (len(k) - 4) + k[-4:]) if len(k) > 4 else '*' * len(k)
        stored = cfg.get('providers', {})
        providers = {
            name: {
                'api_key_masked': _mask(stored.get(name, {}).get('api_key', '')),
                'model':          stored.get(name, {}).get('model', ''),
                'base_url':       stored.get(name, {}).get('base_url', ''),
                'default_model':  spec['default_model'],
            }
            for name, spec in PROVIDERS.items()
        }
        GLib.idle_add(run_js, 'receiveConfig(%s)' % json.dumps({
            'provider': PROVIDER,
            'search_engine': SEARCH_ENGINE,
            'providers': providers,
        }))
    elif action == 'saveConfig':
        prov = msg.get('provider', PROVIDER)
        if prov not in PROVIDERS:
            prov = 'openai'
        PROVIDER = prov
        SEARCH_ENGINE = msg.get('search_engine', SEARCH_ENGINE)
        pc = cfg.setdefault('providers', {}).setdefault(prov, {})
        if msg.get('api_key'):            # blank = keep the stored key
            pc['api_key'] = msg['api_key']
        if msg.get('model') is not None:
            pc['model'] = msg.get('model', '').strip()
        if prov == 'custom':
            pc['base_url'] = (msg.get('base_url') or '').strip()
        cfg['provider'] = PROVIDER
        cfg['search_engine'] = SEARCH_ENGINE
        save_config(cfg)
        GLib.idle_add(run_js, 'configSaved()')
    elif action == 'getHistory':
        items = sorted(
            ({'id': c.get('id'), 'title': c.get('title', ''), 'ts': c.get('ts', 0)}
             for c in conversations),
            key=lambda x: x['ts'], reverse=True)
        GLib.idle_add(run_js, 'receiveHistory(%s)' % json.dumps(items))
    elif action == 'getConversation':
        conv = next((c for c in conversations if c.get('id') == msg.get('id')), None)
        GLib.idle_add(run_js, 'receiveConversation(%s)' % json.dumps(conv or {}))
    elif action == 'saveConversation':
        cid = msg.get('id')
        if cid:
            conv = next((c for c in conversations if c.get('id') == cid), None)
            if conv is None:
                conv = {'id': cid}
                conversations.append(conv)
            conv['title']    = msg.get('title', '')
            conv['messages'] = msg.get('messages', [])
            conv['ts']       = msg.get('ts', 0)
            save_conversations()
    elif action == 'deleteConversation':
        conversations[:] = [c for c in conversations if c.get('id') != msg.get('id')]
        save_conversations()
    elif action == 'openExternal':
        try:
            Gtk.show_uri_on_window(win, msg.get('url', ''), Gdk.CURRENT_TIME)
        except Exception:
            pass
    elif action == 'close':
        Gtk.main_quit()

content_manager.connect('script-message-received::launcher', on_message)
win.connect('destroy', Gtk.main_quit)

def on_load(_, event):
    if event == WebKit2.LoadEvent.FINISHED:
        win.show_all()
        win.present()

launcher_wv.connect('load-changed', on_load)
Gtk.main()
