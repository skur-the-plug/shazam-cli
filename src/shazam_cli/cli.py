"""Command-line song recognition for PipeWire Linux desktops."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Sequence

from shazamio import Shazam

from . import __version__


def clean(value: object) -> str:
    """Keep remote metadata to one safe terminal line."""
    return " ".join(str(value or "").split())


def history_path() -> Path:
    """Return the XDG-compatible private history path."""
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home).expanduser() if state_home else Path.home() / ".local" / "state"
    return base / "shazam" / "history.jsonl"


def save_history(track: dict[str, Any]) -> None:
    """Append one successful identification to the private local history."""
    entry = {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "artist": clean(track.get("subtitle")),
        "title": clean(track.get("title")),
        "url": clean(track.get("url")),
    }
    destination = history_path()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(
        destination,
        os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        0o600,
    )
    with os.fdopen(descriptor, "a", encoding="utf-8") as history_file:
        history_file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history() -> list[dict[str, Any]]:
    """Load valid history entries while tolerating a damaged line."""
    source = history_path()
    if not source.exists():
        return []

    entries: list[dict[str, Any]] = []
    with source.open(encoding="utf-8") as history_file:
        for line in history_file:
            try:
                entry = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(entry, dict) and entry.get("title"):
                entries.append(entry)
    return entries


def show_history() -> int:
    """Print successful identifications, newest first."""
    try:
        entries = load_history()
    except OSError as exc:
        print(f"shazam: could not read history: {clean(exc)}", file=sys.stderr)
        return 1

    if not entries:
        print("No Shazam history yet.")
        return 0

    for number, entry in enumerate(reversed(entries), start=1):
        try:
            when = datetime.fromisoformat(entry["time"]).astimezone().strftime("%Y-%m-%d %H:%M")
        except (KeyError, TypeError, ValueError):
            when = "unknown time"
        artist = clean(entry.get("artist"))
        title = clean(entry.get("title"))
        song = f"{artist} — {title}" if artist else title
        print(f"{number:>3}. {when}  {song}")
    return 0


def record(seconds: float, target: str | None, audio_path: Path) -> None:
    """Capture a fixed-length WAV sample through PipeWire."""
    command = [
        "pw-record",
        "--rate",
        "48000",
        "--channels",
        "2",
        "--format",
        "s16",
        "--sample-count",
        str(round(seconds * 48_000)),
    ]
    if target:
        command.extend(("--target", target))
    command.append(str(audio_path))

    print(f"Listening for {seconds:g} seconds...", file=sys.stderr, flush=True)
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=seconds + 8,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pw-record is not installed") from exc

    error = clean(result.stdout)
    if result.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size < 8_000:
        detail = f": {error}" if error else ""
        source = target or "the default microphone"
        raise RuntimeError(f"could not record from {source}{detail}")


def default_monitor() -> str:
    """Return the PipeWire node for audio currently playing on the PC."""
    try:
        sink = subprocess.check_output(
            ("pactl", "get-default-sink"),
            text=True,
            stderr=subprocess.STDOUT,
            timeout=3,
        ).strip()
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise RuntimeError("could not find the default speaker monitor") from exc
    if not sink:
        raise RuntimeError("could not find the default speaker monitor")
    return f"{sink}.monitor"


def microphone_is_muted(target: str | None) -> bool:
    """Read the software mute state without blocking if it is unavailable."""
    source = target or "@DEFAULT_SOURCE@"
    try:
        result = subprocess.run(
            ("pactl", "get-source-mute", source),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    state = result.stdout.partition(":")[2].strip().casefold()
    return state in {"yes", "true", "1"}


async def identify(audio_path: Path) -> dict[str, Any]:
    """Fingerprint an audio file and ask Shazam for a match."""
    async with Shazam() as client:
        return await asyncio.wait_for(client.recognize(audio_path), timeout=45)


def recognize(audio_path: Path) -> int:
    """Recognize, persist, and print one audio sample."""
    print("Identifying...", file=sys.stderr, flush=True)
    try:
        result = asyncio.run(identify(audio_path))
    except KeyboardInterrupt:
        print("shazam: cancelled", file=sys.stderr)
        return 130
    except TimeoutError:
        print("shazam: recognition timed out; check your internet connection", file=sys.stderr)
        return 1
    except Exception as exc:  # The API client exposes several transport exceptions.
        print(f"shazam: recognition failed: {clean(exc)}", file=sys.stderr)
        return 1

    track = result.get("track") or {}
    title = clean(track.get("title"))
    artist = clean(track.get("subtitle"))
    if not title:
        print("No song recognized. Try again closer to the music.", file=sys.stderr)
        return 1

    try:
        save_history(track)
    except OSError as exc:
        print(f"shazam: warning: could not save history: {clean(exc)}", file=sys.stderr)
    print(f"{artist} — {title}" if artist else title)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="shazam",
        description="Identify music from your microphone, speakers, or an audio file.",
    )
    result.add_argument(
        "input",
        nargs="?",
        help="audio file to identify, or 'history' to show past matches",
    )
    result.add_argument(
        "-s",
        "--seconds",
        type=float,
        default=12,
        help="recording length from 1 to 14 seconds (default: 12)",
    )
    result.add_argument(
        "-d",
        "--device",
        help="PipeWire target node (default: the system's default microphone)",
    )
    result.add_argument(
        "--monitor",
        action="store_true",
        help="listen to audio playing on this PC instead of the microphone",
    )
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.input == "history":
        return show_history()

    if not 1 <= args.seconds <= 14:
        print("shazam: --seconds must be between 1 and 14", file=sys.stderr)
        return 2

    if args.input is not None:
        audio_path = Path(args.input).expanduser().resolve()
        if not audio_path.is_file():
            print(f"shazam: audio file not found: {audio_path}", file=sys.stderr)
            return 2
        return recognize(audio_path)

    try:
        target = default_monitor() if args.monitor else args.device
        if not args.monitor and microphone_is_muted(target):
            print("shazam: microphone is muted — unmute it and try again.", file=sys.stderr)
            return 1
        with tempfile.TemporaryDirectory(prefix="shazam-") as audio_dir:
            audio_path = Path(audio_dir) / "sample.wav"
            record(args.seconds, target, audio_path)
            return recognize(audio_path)
    except KeyboardInterrupt:
        print("shazam: cancelled", file=sys.stderr)
        return 130
    except (RuntimeError, subprocess.SubprocessError) as exc:
        print(f"shazam: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
