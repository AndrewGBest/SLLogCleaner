# Releasing

Releases ship a stand-alone executable per platform, so users do not need
Python. The executables are built with [PyInstaller](https://pyinstaller.org)
by the [`release` workflow](../.github/workflows/release.yml).

## Targets

| Download                          | Contains           | Built on (GitHub runner) |
|-----------------------------------|--------------------|--------------------------|
| `SLLogCleaner-windows-x64.zip`    | `SLLogCleaner.exe` | `windows-latest`         |
| `SLLogCleaner-linux-x64.tar.gz`   | `SLLogCleaner`     | `ubuntu-22.04`           |
| `SLLogCleaner-macos-arm64.tar.gz` | `SLLogCleaner.app` | `macos-latest` (Apple silicon) |
| `SLLogCleaner-macos-x64.tar.gz`   | `SLLogCleaner.app` | `macos-15-intel` (Intel) |

PyInstaller is not a cross-compiler - each program has to be built on the
system it is for - which is why there is one job per target. Linux is built on
an older image so the binary also runs on distributions with an older glibc.
`macos-15-intel` is GitHub's last Intel image; drop that target when it is
retired. macOS is included because Second Life has an official macOS viewer.

All builds are "windowed": started without arguments they open the window,
with arguments they act as the command line. Windows and Linux get a single
file; macOS gets an `.app` bundle.

## Cutting a release

1. Update `__version__` in `sllogcleaner.py` and merge to `main`.
2. Tag that commit and push the tag:

   ```bash
   git tag v1.0.0
   ```

   ```bash
   git push origin v1.0.0
   ```

3. The workflow runs the tests on every platform, checks that the tag matches
   `__version__`, builds each program and smoke-tests it by merging a real log, and creates a
   **draft** GitHub release with the four archives attached.
4. Download at least one archive, try it on real logs, edit the generated
   release notes, then press *Publish*.

To test the build without releasing, start the workflow manually from the
*Actions* tab ("Run workflow"). The archives are then available as workflow
artifacts and nothing is published.

## Building locally

```bash
python -m pip install pyinstaller
```

```bash
pyinstaller --onefile --windowed --name SLLogCleaner sllogcleaner.py
```

On macOS leave out `--onefile`. The result is written to `dist/`. The Python
used for the build needs `tkinter` (on Debian/Ubuntu: the `python3-tk`
package).

## Known limitations

- **Unsigned binaries.** Windows SmartScreen shows "Windows protected your
  PC" (choose *More info → Run anyway*), and macOS Gatekeeper refuses to open
  the file on double-click (right-click → *Open*, or
  `xattr -dr com.apple.quarantine SLLogCleaner.app`). Removing these warnings
  requires paid code-signing certificates (Windows) and an Apple Developer
  account with notarisation (macOS).
- **Antivirus false positives.** One-file PyInstaller executables are
  occasionally flagged by antivirus heuristics. If this becomes a problem,
  switch the Windows build to `--onedir`.
- **Start-up time.** A one-file executable unpacks itself to a temporary
  folder on each start, which adds a moment before it begins.

## Possible follow-ups

- Publishing to PyPI so `pipx install sllogcleaner` works.
- Linux `aarch64` build, if anyone asks for it.
