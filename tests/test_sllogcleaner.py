from pathlib import Path

import pytest

import sllogcleaner as slc


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(tmp_path: Path, *extra: str) -> Path:
    out = tmp_path / "out"
    assert slc.main([str(tmp_path / "logs"), "-o", str(out), "-q", *extra]) == 0
    return out


@pytest.mark.parametrize("line, expected", [
    ("[2024/01/15 13:45]  A: hi", (2024, 1, 15, 13, 45, -1)),
    ("[2024/1/5 1:45 PM]  A: hi", (2024, 1, 5, 13, 45, -1)),
    ("[2024/01/15 12:05 AM]  A: hi", (2024, 1, 15, 0, 5, -1)),
    ("[2024/01/15 12:05 PM]  A: hi", (2024, 1, 15, 12, 5, -1)),
    ("[2024/01/15 13:45:09]  A: hi", (2024, 1, 15, 13, 45, 9)),
    ("[13:45]  A: hi", None),
    (" continuation [2024/01/15 13:45]", None),
    ("typed location", None),
])
def test_parse_timestamp(line, expected):
    assert slc.parse_timestamp(line) == expected


def test_merge_sequences_keeps_repeats_and_order():
    assert slc.merge_sequences(["x", "y", "z"], ["y", "z", "w"]) == ["x", "y", "z", "w"]
    assert slc.merge_sequences(["y", "z"], ["x", "y", "z"]) == ["x", "y", "z"]
    assert slc.merge_sequences(["lol", "lol"], ["lol", "lol"]) == ["lol", "lol"]
    assert slc.merge_sequences(["lol"], ["lol", "lol"]) == ["lol", "lol"]


def test_overlapping_copies_are_merged_and_sorted(tmp_path):
    write(tmp_path / "logs/pc1/jane_doe/chat.txt",
          "[2024/01/02 10:00]  A: second\n[2024/01/01 09:00]  A: first\n")
    write(tmp_path / "logs/pc2/jane_doe/chat.txt",
          "[2024/01/02 10:00]  A: second\n[2024/01/03 11:00]  A: third\n")
    out = run(tmp_path)
    assert (out / "chat.txt").read_text(encoding="utf-8") == (
        "[2024/01/01 09:00]  A: first\n"
        "[2024/01/02 10:00]  A: second\n"
        "[2024/01/03 11:00]  A: third\n")


def test_multiline_messages_and_repeats_survive(tmp_path):
    text = ("[2024/01/01 09:00]  A: line one\n line two\n"
            "[2024/01/01 09:00]  A: lol\n[2024/01/01 09:00]  A: lol\n")
    write(tmp_path / "logs/a/chat.txt", text)
    write(tmp_path / "logs/b/chat.txt", text)
    assert (run(tmp_path) / "chat.txt").read_text(encoding="utf-8") == text


def test_capitalisation_is_preserved(tmp_path):
    line = "[2024/01/01 09:00]  A: hi\n"
    write(tmp_path / "logs/a/My Cool Group.txt", line)
    write(tmp_path / "logs/b/My Cool Group.TXT", line)
    out = run(tmp_path)
    assert [p.name for p in out.iterdir()] == ["My Cool Group.txt"]


def test_date_suffixes(tmp_path):
    write(tmp_path / "logs/chat-2024-01-15.txt", "[2024/01/15 09:00]  A: a\n")
    write(tmp_path / "logs/chat-2024-01-16.txt", "[2024/01/16 09:00]  A: b\n")
    write(tmp_path / "logs/jane_doe-2024-01.txt", "[2024/01/16 09:00]  J: c\n")
    assert sorted(p.name for p in run(tmp_path).iterdir()) == ["chat.txt", "jane_doe.txt"]
    kept = run(tmp_path, "--keep-date-suffix")
    assert "chat-2024-01-15.txt" in [p.name for p in kept.iterdir()]


def test_by_account_keeps_residents_apart(tmp_path):
    write(tmp_path / "logs/pc1/jane_doe/chat.txt", "[2024/01/01 09:00]  A: jane\n")
    write(tmp_path / "logs/pc2/jane_doe/chat.txt", "[2024/01/01 09:00]  A: jane\n")
    write(tmp_path / "logs/pc1/john_doe/chat.txt", "[2024/01/01 09:00]  A: john\n")
    out = run(tmp_path, "--by-account")
    assert (out / "jane_doe/chat.txt").read_text(encoding="utf-8").count("\n") == 1
    assert "john" in (out / "john_doe/chat.txt").read_text(encoding="utf-8")


def test_non_chat_files_and_output_folder_are_ignored(tmp_path):
    write(tmp_path / "logs/teleport_history.txt", "Some Region (1, 2, 3)\n")
    write(tmp_path / "logs/chat.txt", "[2024/01/01 09:00]  A: hi\n")
    out = tmp_path / "logs/output"
    write(out / "chat.txt", "[2020/01/01 09:00]  A: stale\n")
    assert slc.main([str(tmp_path / "logs"), "-o", str(out), "-q"]) == 0
    assert [p.name for p in out.iterdir()] == ["chat.txt"]
    assert "stale" not in (out / "chat.txt").read_text(encoding="utf-8")


def test_invalid_bytes_round_trip(tmp_path):
    path = tmp_path / "logs/chat.txt"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xef\xbb\xbf[2024/01/01 09:00]  A: caf\xe9\n")
    data = (run(tmp_path) / "chat.txt").read_bytes()
    assert data.replace(b"\r\n", b"\n") == b"[2024/01/01 09:00]  A: caf\xe9\n"


def test_dry_run_writes_nothing(tmp_path):
    write(tmp_path / "logs/chat.txt", "[2024/01/01 09:00]  A: hi\n")
    assert not run(tmp_path, "--dry-run").exists()


def test_gui_merges_chosen_folders(tmp_path):
    """Drive the window the way a user would: fill both folders, press Merge."""
    import os
    import time

    required = os.environ.get("SLLOGCLEANER_REQUIRE_GUI")
    try:
        import tkinter
        root = tkinter.Tk()
    except Exception as error:  # no tkinter or no display on this machine
        if required:
            raise
        pytest.skip(f"no GUI available: {error}")

    try:
        write(tmp_path / "logs/a/chat.txt", "[2024/01/02 10:00]  A: second\n")
        write(tmp_path / "logs/b/chat.txt",
              "[2024/01/02 10:00]  A: second\n[2024/01/01 09:00]  A: first\n")
        app = slc.GuiApp(root)
        app.input_dir.set(str(tmp_path / "logs"))
        app.output_dir.set(str(tmp_path / "out"))
        app.merge_button.invoke()
        assert app.busy
        deadline = time.time() + 30
        while app.busy and time.time() < deadline:
            root.update()
            time.sleep(0.01)
        assert not app.busy
        assert (tmp_path / "out/chat.txt").read_text(encoding="utf-8") == (
            "[2024/01/01 09:00]  A: first\n[2024/01/02 10:00]  A: second\n")
        assert "1 duplicates removed" in app.report.get("1.0", "end")
        assert str(app.merge_button.cget("text")) == "Merge"
    finally:
        root.destroy()
