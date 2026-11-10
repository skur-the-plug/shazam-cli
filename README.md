<div align="center">

# ⚡ shazam-cli

### Name that song without leaving your terminal.

[![Linux](https://img.shields.io/badge/Linux-PipeWire-FCC624?logo=linux&logoColor=black)](https://pipewire.org/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/skur-the-plug/shazam-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/skur-the-plug/shazam-cli/actions/workflows/ci.yml)
[![MIT License](https://img.shields.io/badge/license-MIT-22c55e.svg)](LICENSE)

One command. Twelve seconds. Artist and title—right in your shell.

</div>

```console
$ shazam
Listening for 12 seconds...
Identifying...
Daft Punk — Instant Crush

$ shazam history
  1. 2026-11-10 20:25  Daft Punk — Instant Crush
  2. 2026-11-09 23:41  Tame Impala — Borderline
```

## Why this exists

Sometimes the fastest interface is the one already open. `shazam-cli` gives
PipeWire-based Linux desktops a small, focused song recognizer with no GUI, no
account, and no background daemon.

- 🎙️ **Microphone recognition** with a plain `shazam`
- 🔇 **Instant mute detection**—no waiting 12 seconds for a silent recording
- 🔊 **System-audio capture** with `shazam --monitor`
- 🗂️ **Private local history** with `shazam history`
- 📁 **Audio-file recognition** for WAV, MP3, FLAC, and more
- 🧼 **No daemon and no leftover recordings**
- 🐧 **PipeWire-first** and tested on Arch Linux

## Quick start

### Install from GitHub with `uv`

```bash
uv tool install git+https://github.com/skur-the-plug/shazam-cli.git
```

Or clone it and use the installer:

```bash
git clone https://github.com/skur-the-plug/shazam-cli.git
cd shazam-cli
./install.sh
```

Then put some music on and run:

```bash
shazam
```

> [!IMPORTANT]
> `~/.local/bin` must be on your `PATH`. `uv` prints a hint if it is not.

## Requirements

- Linux with PipeWire
- Python 3.11 or newer
- `pw-record` for audio capture
- `pactl` for mute and monitor-source detection
- An internet connection for recognition

Install the system pieces first if they are missing:

<details>
<summary><strong>Arch Linux</strong></summary>

```bash
sudo pacman -S pipewire-audio libpulse python
```

</details>

<details>
<summary><strong>Ubuntu / Debian</strong></summary>

```bash
sudo apt install pipewire-bin pulseaudio-utils python3 python3-venv
```

</details>

<details>
<summary><strong>Fedora</strong></summary>

```bash
sudo dnf install pipewire-utils pulseaudio-utils python3
```

</details>

## Usage

| Command | What it does |
|---|---|
| `shazam` | Listen through the default microphone for 12 seconds |
| `shazam --monitor` | Identify audio playing through the default speakers |
| `shazam song.mp3` | Identify an existing audio file |
| `shazam history` | Show successful matches, newest first |
| `shazam -s 8` | Use an 8-second microphone sample |
| `shazam -d NODE` | Capture from a specific PipeWire node |
| `shazam --help` | Show every option |

If the microphone is muted, the command exits immediately:

```console
$ shazam
shazam: microphone is muted — unmute it and try again.
```

To find PipeWire node IDs for `--device`:

```bash
wpctl status
```

## History

Only successful matches are stored. History lives at:

```text
${XDG_STATE_HOME:-~/.local/state}/shazam/history.jsonl
```

It is newline-delimited JSON, so it is both resilient and script-friendly. The
file is created with user-only permissions (`0600`). Failed matches and muted
attempts never enter the history.

## How it works

```text
microphone / speaker monitor / file
                 │
                 ▼
        temporary WAV sample
                 │
                 ▼
       local acoustic fingerprint
                 │
                 ▼
         Shazam match request
                 │
                 ▼
       Artist — Title + history
```

Audio capture is handled by PipeWire's `pw-record`. Recognition is powered by
[ShazamIO](https://github.com/shazamio/ShazamIO), which creates the acoustic
signature locally. Microphone samples are held in a temporary directory and
deleted as soon as recognition finishes.

## Privacy

- The microphone is active only while `shazam` is visibly listening.
- The temporary WAV recording is deleted after each attempt.
- History stays on your machine unless you choose to share it.
- Recognition uses Shazam's network service through an unofficial,
  reverse-engineered client; it can change or stop working without notice.

## Troubleshooting

<details>
<summary><strong>No song recognized</strong></summary>

Move closer to the music, reduce background noise, and keep the default
12-second sample. Recorded releases work much better than humming or live
performances.

</details>

<details>
<summary><strong>Could not record from the default microphone</strong></summary>

Confirm PipeWire can see an input:

```bash
wpctl status
pw-record --rate 48000 --channels 2 --sample-count 96000 test.wav
```

Also check that your terminal session can access the user's PipeWire socket.

</details>

<details>
<summary><strong>System audio does not work</strong></summary>

`--monitor` targets the monitor of the current default sink. Check it with:

```bash
pactl get-default-sink
pactl list short sources
```

</details>

<details>
<summary><strong><code>shazam: command not found</code></strong></summary>

Add the user binary directory to your shell configuration:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

</details>

## Development

```bash
git clone https://github.com/skur-the-plug/shazam-cli.git
cd shazam-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
```

## Uninstall

If installed with `uv`:

```bash
uv tool uninstall shazam-pipewire-cli
```

The history is intentionally left in place. Remove it separately only if you
want to erase it:

```bash
rm -r ~/.local/state/shazam
```

## Disclaimer

This is an independent project and is not affiliated with or endorsed by
Apple Inc. or Shazam. “Shazam” is a trademark of Apple Inc.

## License

[MIT](LICENSE) © 2026 Anas Houhou
