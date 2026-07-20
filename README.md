# Launcher

A lightweight, Spotlight-style command bar for Linux with web search, an
embedded browser, and multi-provider AI chat.

- **Web search** — DuckDuckGo (default), Google, or Bing
- **Embedded browser** — results open in a built-in viewer
- **AI chat** — OpenAI, Claude (Anthropic), Kimi (Moonshot), OpenRouter, or any
  OpenAI-compatible endpoint, with saved conversation history
- Frameless, always-on-top, keyboard-driven

*By Lehman · <3ma.reds@gmail.com> · ☕ [Buy me a coffee](https://buymeacoffee.com/lehman)*

---

## Usage

- Type and press **Enter** to search (or chat, in AI mode)
- `/mode` — switch between **web** and **ai** mode
- `/config` — open settings (provider, API key, model, search engine)
- **Esc** — back out / close · **Ctrl+C** — quit

Config and history live in `~/.config/launcher/`.

---

## Run from source

Requires `python3`, PyGObject, GTK 3, and WebKit2GTK 4.1.

```sh
# Debian/Ubuntu/Pop!_OS deps
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1

python3 launcher.py
```

---

## Keyboard shortcut (summon the bar)

The app is a **single-instance daemon**: the first run stays resident, and
running the command again just toggles the window (show/hide) via `SIGUSR1`.
So bind **one global shortcut to the launch command** — the first press starts
it, every press after that toggles it, exactly like Spotlight.

Recommended shortcut: **Ctrl + Space**.

The command to bind (pick one):

```sh
# If installed (Flatpak, .deb, or `make install`):
io.github.emanuele_r.Launcher

# Running from source:
python3 /home/emanuelerossi/launcher/launcher.py
```

### COSMIC (Pop!_OS)

Settings → **Keyboard** → **Custom Shortcuts** → **Add shortcut** →
set the command above, then press **Ctrl + Space** as the key combination.

### GNOME

Settings → **Keyboard** → **View and Customize Shortcuts** → **Custom Shortcuts**
→ **+**. Name it `Launcher`, set the command above, and assign **Ctrl + Space**.

### KDE Plasma

System Settings → **Shortcuts** → **Custom Shortcuts** → **Edit → New → Global
Shortcut → Command/URL**. Put the command under the *Action* tab and **Ctrl +
Space** under the *Trigger* tab.

### Any desktop (fallback)

Bind the shortcut to toggle an already-running instance directly:

```sh
pkill -USR1 -f launcher.py
```

> **Note:** GNOME and some IMEs use **Ctrl + Space** to switch input sources.
> If the shortcut doesn't register, free it in *Keyboard → Input Sources*
> first, or pick another combo (e.g. **Super + Space**).

---

## Build a Flatpak (and the COSMIC Store)

The COSMIC Store installs Flatpaks, so the same manifest covers both.

```sh
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
flatpak-builder --user --install --force-clean build-dir io.github.emanuele_r.Launcher.yml
flatpak run io.github.emanuele_r.Launcher
```

To publish a single-file bundle you can hand to the COSMIC Store / other machines:

```sh
flatpak-builder --repo=repo --force-clean build-dir io.github.emanuele_r.Launcher.yml
flatpak build-bundle repo launcher.flatpak io.github.emanuele_r.Launcher
```

> If your installed `org.gnome.Platform` version differs, change
> `runtime-version` in `io.github.emanuele_r.Launcher.yml` to match.

---

## Build a Debian package

```sh
sudo apt install devscripts debhelper
dpkg-buildpackage -us -uc -b
sudo apt install ../lehman-launcher_1.0.0_all.deb
```

Or install straight from the tree with the Makefile:

```sh
sudo make install PREFIX=/usr
```

---

## License

MIT © 2026 Lehman
