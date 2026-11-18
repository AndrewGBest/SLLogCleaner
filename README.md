# SL Log Cleaner

Merge, de-duplicate and chronologically sort [Second Life](https://secondlife.com) chat logs.

After a few reinstalls, new computers and backups you end up with several
partially overlapping copies of every chat transcript. SL Log Cleaner reads
all of them and writes **one transcript per conversation**, containing every
message once, in order.

Your original files are only ever read, never changed.

## Quick start

### Using the download (no Python needed)

1. Download the archive for your system from the
   [Releases](../../releases) page and unpack it anywhere.
2. Start **SLLogCleaner**. A small window opens.
3. Next to *Log folders*, press *Browse...* and choose the folder that holds
   your Second Life logs. Sub-folders are searched too, so you can collect
   whole backups side by side in one folder and choose that:

   ```
   my-sl-logs/
     old-laptop/jane_resident/chat.txt
     old-laptop/jane_resident/My Cool Group.txt
     desktop/jane_resident/chat.txt
     ...
   ```
4. Next to *Save merged logs to*, choose an empty folder for the result.
5. Press *Merge*. The window lists every merged log and how many duplicates
   were removed.

The two checkboxes match the `--by-account` and `--keep-date-suffix`
[options](#options) below.

The downloads are not code-signed, so Windows SmartScreen and macOS Gatekeeper
will warn the first time; see
[docs/RELEASING.md](docs/RELEASING.md#known-limitations) for how to get past
that.

### Using Python

Requires Python 3.9 or newer; there are no other dependencies.

```bash
python sllogcleaner.py
```

Without arguments this merges everything in a `logs` folder in the current
directory into an `output` folder (creating `logs` if it is missing). Add
`--gui` for the window. To install it as a command:

```bash
pip install .
```

```bash
sllogcleaner ~/sl-backups -o ~/sl-merged
```

## Where Second Life keeps its logs

The log folder can be changed in the viewer's preferences, so check there
first. By default the viewer keeps its data in the folder below, with chat
transcripts usually in a sub-folder named after the account:

| System  | Folder                                      |
|---------|---------------------------------------------|
| Windows | `%APPDATA%\SecondLife\`                     |
| macOS   | `~/Library/Application Support/SecondLife/` |
| Linux   | `~/.secondlife/`                            |

Third-party viewers such as Firestorm use their own folder.

## Options

```
sllogcleaner [FOLDER ...] [-o FOLDER] [--by-account] [--keep-date-suffix] [-n] [-q] [--gui]
```

| Option               | Effect |
|----------------------|--------|
| `FOLDER ...`         | Folders to search (with sub-folders). Default: `logs` next to the program. |
| `-o`, `--output`     | Where merged logs are written. Default: `output` next to the program. Existing files of the same name are overwritten. |
| `--by-account`       | Keep residents apart: only merge files whose containing folders have the same name (e.g. `jane_resident`), and write to `output/<that name>/`. **Use this if `logs` holds more than one account** - otherwise both accounts' `chat.txt` are merged into one. |
| `--keep-date-suffix` | Keep `chat-2024-01-15.txt` / `friend-2024-01.txt` as separate files instead of folding them into `chat.txt` / `friend.txt`. Use this if your viewer has "add datestamp to log file name" switched on and you want to put the result back. |
| `-n`, `--dry-run`    | Show what would happen without writing anything. |
| `-q`, `--quiet`      | Only print errors. |
| `--gui`              | Open the window instead. |
| `--version`, `-h`    | Version / help. |

The downloaded program accepts the same arguments. On Windows it is built
without a console, so it works but prints nothing there; use the Python
version if you want the report in a terminal.

## How it works

1. **Find.** Every `.txt` file under the input folders is collected. The
   output folder is skipped if it lies inside an input folder.
2. **Group.** Files with the same name belong to the same conversation.
   Upper/lower case is ignored when comparing, and the viewer's date suffix
   (`-YYYY-MM` or `-YYYY-MM-DD`) is stripped unless `--keep-date-suffix` is
   given. The output file keeps the original capitalisation
   (`My Cool Group.txt`, not `my cool group.txt`), so the result works on
   case-sensitive file systems such as Linux.
3. **Parse.** A message starts at a line beginning with a dated timestamp,
   `[2024/01/15 13:45]` or `[2024/01/15 1:45 PM]` (seconds are accepted too).
   Following lines without one are continuation lines of a multi-line message
   and stay attached to it.
4. **Merge.** Messages are bucketed by timestamp. Within a bucket, the copies
   are combined so that the messages they have in common appear once and the
   rest are kept in order. Two copies of the same log collapse into one, but
   someone saying "lol" twice in the same minute still says it twice.
5. **Write.** Buckets are written in chronological order.

Files without a single dated chat line (`teleport_history.txt`,
`typed_locations.txt`, ...) are reported as skipped and not copied.

### Limitations

- Logs written with the date switched off (`[13:45]` only) or with no
  timestamps cannot be ordered across days and are skipped.
- Timestamps are compared as written. Copies of the same conversation recorded
  with different clock settings (time zone, 12/24-hour) are not recognised as
  duplicates of each other.
- `conversation.log` and other non-`.txt` files are ignored.

## Development

```bash
python -m pip install pytest
```

```bash
python -m pytest
```

The whole program is [`sllogcleaner.py`](sllogcleaner.py); tests are in
[`tests/`](tests). Building executables and publishing a release is described
in [docs/RELEASING.md](docs/RELEASING.md).

## License

SL Log Cleaner is free software, released under the
[GNU General Public License, version 3](LICENSE). It comes with no warranty.
