"""Billie the Platypus judges your terminal. Silently. With disdain."""

import argparse
import contextlib
import getpass
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import traceback
import unicodedata
from importlib.resources import files
from pathlib import Path

from billie import sayings

ROOT = files("billie").joinpath("static")
DEFAULT_BILLIE = "billie.txt"


class Billie:
    """Summon a judgmental platypus with random corporate wisdom."""

    MAX_PERCENT = 100
    MIN_PS_LEN = 2

    def __init__(self, tty, ns):
        self.tty = tty
        self.ns = ns
        self.lines = []
        self.billie_path = ROOT.joinpath(DEFAULT_BILLIE)
        self.words = sayings.BillieDeque(*sayings.WORD_LIST)

    def setup(self):
        """Load Billie, gather words, decorate terminal."""
        if self.tty.pretty:
            billie = self.load_billie()
            max_billie = max(map(clean_len, billie)) + 15
        else:
            billie = []
            max_billie = 15

        if self.ns.density > self.MAX_PERCENT:
            sys.stderr.write("billie disapproves of density over 100%\n")
            sys.exit(1)

        if self.ns.density < 0:
            sys.stderr.write("billie disapproves of negative density\n")
            sys.exit(1)

        if self.tty.width < max_billie:
            sys.stderr.write("terminal too small for billie's ego\n")
            sys.stderr.write(f"need at least {max_billie} columns\n")
            return False

        prompt = os.getenv("PS1", "").split("\n")
        line_count = len(prompt) + 1

        fill = range(self.tty.height - len(billie) - line_count)
        self.lines = ["\n" for _ in fill]
        self.lines += billie

        had_stdin = self.get_stdin_data()
        if not had_stdin:
            self.get_real_data()

        self.apply_text()
        return True

    def apply_text(self):
        """Scatter Billie's wisdom across the terminal."""
        line_len = len(self.lines)

        if self.ns.density == 0:
            return

        affected = sorted(
            random.sample(range(line_len), int(line_len * (self.ns.density / 100)))
        )

        for i, target in enumerate(affected, start=1):
            line = self.lines[target]
            line = re.sub("\n", " ", line)

            word = self.words.get()

            if i == 1 or i == len(affected) or random.choice(range(20)) == 0:
                word = "*judges silently*"

            self.lines[target] = BillieMessage(self, line, word).generate()

    def load_billie(self):
        """Load the platypus ASCII art."""
        if self.ns.no_billie:
            return [""]
        return self.billie_path.read_text(encoding="utf-8").splitlines(keepends=True)

    def get_real_data(self):
        """Grab system data for Billie to judge."""
        ret = []
        with contextlib.suppress(OSError):
            if username := getpass.getuser():
                ret.append(username)

        if words := os.getenv("EDITOR", "").split():
            editor = words[0].split("/")[-1]
            ret.append(editor)

        uname = (platform.system(), platform.node(), platform.machine())
        ret.extend(x for x in uname if x)

        with contextlib.suppress(OSError):
            if (
                hasattr(platform, "freedesktop_os_release")
                and (os_release := platform.freedesktop_os_release())
                and (os_id := os_release.get("ID"))
            ):
                ret.append(os_id)

        filenames = [x.name for x in Path.home().iterdir()]
        if filenames:
            ret.append(random.choice(filenames))

        ret += self.get_processes()[:2]

        self.words.extend(map(str.lower, ret))

    def get_stdin_data(self):
        """Get words from stdin for Billie to judge."""
        if not self.tty.in_is_pipe:
            return False

        stdin_lines = (line for line in sys.stdin.readlines())
        rx_word = re.compile(r"\w+", re.UNICODE)

        self.words.clear()
        word_list = [
            match.group(0)
            for line in stdin_lines
            for match in rx_word.finditer(line.lower())
        ]
        self.words.extend(word_list)
        return True

    def get_processes(self):
        """Grab running process names for Billie to be unimpressed by."""
        processes = set()
        try:
            result = subprocess.run(  # noqa: S603
                ["ps", "-A", "-o", "comm="],  # noqa: S607
                capture_output=True,
                text=True,
                check=True,
            )

            for comm in result.stdout.splitlines():
                name = comm.split("/")[-1]
                if name and len(name) >= self.MIN_PS_LEN and ":" not in name:
                    processes.add(name)

        except (OSError, subprocess.CalledProcessError):
            pass

        proc_list = list(processes)
        random.shuffle(proc_list)
        return proc_list

    def print_billie(self):
        """Unleash Billie upon the terminal."""
        for line in self.lines:
            sys.stdout.write(line)
        sys.stdout.flush()


class BillieMessage:
    """A randomly placed, randomly colored piece of platypus wisdom."""

    def __init__(self, billie, occupied, word):
        self.billie = billie
        self.tty = billie.tty
        self.occupied = occupied
        self.word = word

    def generate(self):
        """Format a word with color and random spacing."""
        if self.word == "*judges silently*":
            msg = self.word
        else:
            msg = f"{sayings.PREFIXES.get()} {self.word}"
            if random.choice(range(15)) == 0:
                msg += f" {sayings.SUFFIXES.get()}"

        interval = self.tty.width - onscreen_len(msg)
        interval -= clean_len(self.occupied)

        if interval < 1:
            return self.occupied + "\n"

        spacer = " " * random.choice(range(interval))
        msg = f"{spacer}{msg}"

        if self.tty.pretty:
            msg = f"\x1b[1m\x1b[38;5;{sayings.COLORS.get()}m{msg}\x1b[39m\x1b[0m"

        return f"{self.occupied}{msg}\n"


class TTYHandler:
    """Get terminal properties."""

    def __init__(self):
        self.height = 25
        self.width = 80
        self.in_is_pipe = False
        self.out_is_tty = True
        self.pretty = True

    def setup(self):
        """Calculate terminal properties."""
        self.width, self.height = shutil.get_terminal_size()
        self.in_is_pipe = (not sys.stdin.isatty()) if sys.stdin else False
        self.out_is_tty = sys.stdout.isatty()

        self.pretty = self.out_is_tty
        if sys.platform == "win32":
            colorterm = os.getenv("COLORTERM", "").lower()
            self.pretty = (
                "WT_SESSION" in os.environ
                or colorterm in {"truecolor", "24bit"}
                or os.getenv("TERM") == "xterm"
            )


def clean_len(s):
    """Calculate string length without ANSI color codes."""
    s = re.sub(r"\x1b\[[0-9;]*m", "", s)
    return len(s)


def onscreen_len(s):
    """Calculate on-screen length accounting for wide characters."""
    length = 0
    for ch in s:
        length += 2 if unicodedata.east_asian_width(ch) == "W" else 1
    return length


def setup_arguments():
    """Build the argument parser."""
    parser = argparse.ArgumentParser("billie", description=__doc__)

    parser.add_argument(
        "--no-billie", action="store_true", help="hide billie (but why)"
    )

    parser.add_argument(
        "-mh",
        "--max-height",
        help="max terminal height",
        type=int,
    )

    parser.add_argument(
        "-mw",
        "--max-width",
        help="max terminal width",
        type=int,
    )

    parser.add_argument(
        "-d",
        "--density",
        help="word density percent (0-100, default 30)",
        type=float,
        default=30,
    )
    return parser


def main():
    """Summon Billie."""
    tty = TTYHandler()
    tty.setup()

    parser = setup_arguments()
    ns = parser.parse_args()
    if ns.max_height:
        tty.height = ns.max_height
    if ns.max_width:
        tty.width = ns.max_width

    try:
        billie = Billie(tty, ns)
        if not billie.setup():
            return 1
        billie.print_billie()

    except (UnicodeEncodeError, UnicodeDecodeError):
        traceback.print_exc()
        print()

        lang = os.getenv("LC_ALL") or os.getenv("LC_CTYPE") or os.getenv("LANG") or ""
        if not lang:
            print("billie can't render without proper $LANG")
            return 3

        if not lang.lower().endswith(("utf-8", "utf8")):
            print(
                f"locale '{lang}' is not UTF-8. "
                "billie needs UTF-8 to look properly judgmental."
            )
            return 2

        print("unknown unicode error. billie is displeased.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
