#!/usr/bin/env python3
"""SL Log Cleaner - merge, de-duplicate and sort Second Life chat logs.

Second Life viewers keep one plain-text transcript per conversation
(``chat.txt`` for nearby chat, ``some_resident.txt`` for an IM, ``Group
Name.txt`` for a group, ...).  After a few reinstalls, new computers and
backups you end up with several partially overlapping copies of every
transcript.  This tool walks one or more folders, groups the copies of each
conversation, and writes a single transcript per conversation that contains
every message exactly as often as it really occurred, in chronological order.

See README.md for usage and for a description of the merge rules.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

__version__ = "1.0.0"

LOG_EXTENSION = ".txt"

# A dated line as written by the viewer: "[2024/01/15 13:45]  Name: text".
# The official viewer writes 24-hour or 12-hour ("1:45 PM") stamps without
# seconds; the optional seconds field is accepted for third-party viewers.
_TIMESTAMP = re.compile(
    r"\[(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s([AaPp])[Mm])?\]"
)

# Suffix added when the viewer's "add datestamp to log file name" option is
# on: "-YYYY-MM-DD" for chat.txt and "-YYYY-MM" for everything else.
_DATE_SUFFIX = re.compile(r"-\d{4}-\d{2}(?:-\d{2})?$")

# (year, month, day, hour, minute, second); second is -1 when not logged.
Timestamp = Tuple[int, int, int, int, int, int]


def parse_timestamp(line: str) -> Optional[Timestamp]:
    """Return the sortable timestamp a log line starts with, or ``None``.

    ``None`` means the line is not the start of a dated message: it is a
    continuation of a multi-line message, a line stamped with a time but no
    date, or something that is not chat at all.
    """
    match = _TIMESTAMP.match(line)
    if match is None:
        return None
    year, month, day, hour, minute, second, meridiem = match.groups()
    hour = int(hour)
    if meridiem:
        hour = hour % 12 + (12 if meridiem in "Pp" else 0)
    return (int(year), int(month), int(day), hour, int(minute),
            int(second) if second else -1)


@dataclass
class Transcript:
    """The messages of one conversation, bucketed by timestamp.

    ``messages`` maps a timestamp to the messages carrying it, in the order
    they were logged.  A message is the full text of a log entry, including
    the continuation lines of a multi-line message.  ``preamble`` holds any
    lines that precede the first dated message of a file.
    """

    preamble: List[str] = field(default_factory=list)
    messages: Dict[Timestamp, List[str]] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.preamble) + sum(map(len, self.messages.values()))

    def merge(self, other: "Transcript") -> None:
        """Fold ``other`` into this transcript without duplicating messages."""
        self.preamble = merge_sequences(self.preamble, other.preamble)
        for stamp, incoming in other.messages.items():
            existing = self.messages.get(stamp)
            self.messages[stamp] = (
                incoming if existing is None else merge_sequences(existing, incoming)
            )

    def lines(self) -> Iterable[str]:
        """Yield every message in chronological order."""
        yield from self.preamble
        for stamp in sorted(self.messages):
            yield from self.messages[stamp]


def merge_sequences(first: List[str], second: List[str]) -> List[str]:
    """Order-preserving union of two message sequences.

    Messages the two sequences have in common (their longest common
    subsequence) appear once; everything else is kept.  This removes the
    overlap between two copies of a log while keeping genuine repeats - a
    resident who said "lol" twice in the same minute still says it twice.
    """
    if not second or first == second:
        return first
    if not first:
        return second
    merged: List[str] = []
    matcher = SequenceMatcher(None, first, second, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        merged.extend(first[i1:i2])
        if tag != "equal":
            merged.extend(second[j1:j2])
    return merged


def read_transcript(path: Path) -> Transcript:
    """Parse one log file.

    Logs are decoded as UTF-8; bytes that are not valid UTF-8 are carried
    through unchanged (``surrogateescape``) rather than dropped.  Empty lines
    are discarded - the viewer never writes them.
    """
    transcript = Transcript()
    current: Optional[List[str]] = None  # lines of the message being read
    bucket: List[str] = transcript.preamble

    def flush() -> None:
        if current is not None:
            bucket.append("\n".join(current))

    with open(path, "r", encoding="utf-8", errors="surrogateescape") as handle:
        for number, raw in enumerate(handle):
            line = raw.rstrip("\n")
            if number == 0:
                line = line.lstrip("﻿")  # byte-order mark
            if not line:
                continue
            stamp = parse_timestamp(line)
            if stamp is not None:
                flush()
                current = [line]
                bucket = transcript.messages.setdefault(stamp, [])
            elif current is not None:
                current.append(line)
            else:
                transcript.preamble.append(line)
    flush()
    return transcript


@dataclass
class Conversation:
    """All the files on disk that belong to one output transcript."""

    folder: str  # output sub-folder ("" unless grouping by account)
    names: Counter = field(default_factory=Counter)  # spellings of the name
    files: List[Path] = field(default_factory=list)

    @property
    def output_name(self) -> str:
        """The most common spelling of the name, original capitalisation kept."""
        return self.names.most_common(1)[0][0] + LOG_EXTENSION


def find_conversations(
    roots: Sequence[Path],
    exclude: Optional[Path] = None,
    by_account: bool = False,
    keep_date_suffix: bool = False,
) -> List[Conversation]:
    """Walk ``roots`` and group the log files found by conversation.

    Files are grouped by name, ignoring upper/lower case and (unless
    ``keep_date_suffix``) the viewer's date suffix.  The original
    capitalisation is remembered for the output file, which matters on
    case-sensitive file systems.  With ``by_account`` files are additionally
    kept apart by the name of the folder they sit in.  Anything under
    ``exclude`` (the output folder) is ignored.
    """
    excluded = exclude.resolve() if exclude is not None else None
    conversations: Dict[Tuple[str, str], Conversation] = {}
    for root in roots:
        for folder, subfolders, filenames in os.walk(root):
            subfolders.sort()
            folder_path = Path(folder)
            if excluded is not None and (
                excluded == folder_path.resolve()
                or excluded in folder_path.resolve().parents
            ):
                subfolders.clear()
                continue
            for filename in sorted(filenames):
                stem, extension = os.path.splitext(filename)
                if extension.lower() != LOG_EXTENSION:
                    continue
                if not keep_date_suffix:
                    stem = _DATE_SUFFIX.sub("", stem)
                account = folder_path.name if by_account else ""
                key = (account.casefold(), stem.casefold())
                conversation = conversations.setdefault(key, Conversation(account))
                conversation.names[stem] += 1
                conversation.files.append(folder_path / filename)
    return list(conversations.values())


@dataclass
class Result:
    """What happened to one conversation."""

    output: Path
    sources: int  # files that contained dated chat
    read: int  # messages read across all sources
    written: int  # messages left after merging
    skipped: List[Path]  # files without any dated chat line


def merge_conversation(
    conversation: Conversation, output_dir: Path, dry_run: bool = False
) -> Result:
    """Merge the files of one conversation and write the result."""
    merged = Transcript()
    skipped: List[Path] = []
    sources = read = 0
    for path in conversation.files:
        transcript = read_transcript(path)
        if not transcript.messages:
            skipped.append(path)  # not a dated chat log; leave it alone
            continue
        sources += 1
        read += len(transcript)
        merged.merge(transcript)

    output = output_dir / conversation.folder / conversation.output_name
    if sources and not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8", errors="surrogateescape") as handle:
            handle.writelines(message + "\n" for message in merged.lines())
    return Result(output, sources, read, len(merged), skipped)


def _application_dir() -> Path:
    """Folder the default ``logs``/``output`` folders live in.

    A packaged executable uses the folder it sits in, so double-clicking it
    works no matter what the working directory is; the script uses the
    current directory.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sllogcleaner",
        description="Merge, de-duplicate and chronologically sort Second Life chat logs.",
    )
    parser.add_argument(
        "inputs", nargs="*", type=Path, metavar="FOLDER",
        help="folder(s) to search for .txt logs, including sub-folders "
             "(default: the 'logs' folder next to the program)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, metavar="FOLDER",
        help="folder to write merged logs to (default: 'output' next to the program)",
    )
    parser.add_argument(
        "--by-account", action="store_true",
        help="only merge files whose containing folders share a name, and write "
             "them to a sub-folder of that name (keeps different residents apart)",
    )
    parser.add_argument(
        "--keep-date-suffix", action="store_true",
        help="keep dated files such as 'chat-2024-01-15.txt' separate instead "
             "of folding them into 'chat.txt'",
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="report what would be done without writing anything",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="only print errors",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    base = _application_dir()
    inputs: List[Path] = args.inputs or [base / "logs"]
    output_dir: Path = args.output or base / "output"
    say = (lambda *_: None) if args.quiet else print

    if not args.inputs and not inputs[0].is_dir():
        inputs[0].mkdir(parents=True, exist_ok=True)
        say(f"Created {inputs[0]}\nCopy your Second Life log folders into it and run again.")
        return 0
    missing = [str(path) for path in inputs if not path.is_dir()]
    if missing:
        print(f"error: not a folder: {', '.join(missing)}", file=sys.stderr)
        return 2

    conversations = find_conversations(
        inputs, exclude=output_dir,
        by_account=args.by_account, keep_date_suffix=args.keep_date_suffix,
    )
    written = files = total_read = total_written = 0
    skipped: List[Path] = []
    for conversation in conversations:
        result = merge_conversation(conversation, output_dir, args.dry_run)
        skipped.extend(result.skipped)
        if not result.sources:
            continue
        written += 1
        files += result.sources
        total_read += result.read
        total_written += result.written
        say(f"{result.output}: {result.sources} file(s), {result.written} messages"
            f" ({result.read - result.written} duplicates removed)")

    for path in skipped:
        say(f"skipped (no dated chat lines): {path}")
    verb = "Would merge" if args.dry_run else "Merged"
    say(f"\n{verb} {files} file(s) into {written} log(s) in {output_dir}: "
        f"{total_written} messages kept, {total_read - total_written} duplicates removed.")
    if not files:
        say(f"No chat logs found in {', '.join(map(str, inputs))}.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = sys.argv[1:] if argv is None else list(argv)
    try:
        status = run(build_parser().parse_args(arguments))
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        status = 1
    # Double-clicked executable: keep the console window open to be read.
    if getattr(sys, "frozen", False) and not arguments and sys.stdin and sys.stdin.isatty():
        input("\nPress Enter to close...")
    return status


if __name__ == "__main__":
    sys.exit(main())
