# Releasing

Releases ship a stand-alone executable per platform, so users do not need
Python. The executables are built with [PyInstaller](https://pyinstaller.org)
by the [`release` workflow](../.github/workflows/release.yml).

## Targets

| Download                         | Built on (GitHub runner) | Notes |
|----------------------------------|--------------------------|-------|
| `sllogcleaner-windows-x64.zip`   | `windows-latest`         | |
| `sllogcleaner-linux-x64.tar.gz`  | `ubuntu-22.04`           | Older image, so the binary also runs on distributions with an older glibc. |
| `sllogcleaner-macos-arm64.tar.gz`| `macos-latest`           | Apple-silicon Macs. |
| `sllogcleaner-macos-x64.tar.gz`  | `macos-15-intel`         | Intel Macs. This is GitHub's last Intel image; drop the target when it is retired. |

PyInstaller is not a cross-compiler - each executable has to be built on the
system it is for - which is why there is one job per target. macOS is included
because Second Life has an official macOS viewer.

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
   `__version__`, builds and smoke-tests each executable, and creates a
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
pyinstaller --onefile --console --name sllogcleaner sllogcleaner.py
```

The executable is written to `dist/`.

## Known limitations

- **Unsigned binaries.** Windows SmartScreen shows "Windows protected your
  PC" (choose *More info → Run anyway*), and macOS Gatekeeper refuses to open
  the file on double-click (right-click → *Open*, or
  `xattr -d com.apple.quarantine sllogcleaner`). Removing these warnings
  requires paid code-signing certificates (Windows) and an Apple Developer
  account with notarisation (macOS).
- **Antivirus false positives.** One-file PyInstaller executables are
  occasionally flagged by antivirus heuristics. If this becomes a problem,
  switch the Windows build to `--onedir`.
- **Start-up time.** A one-file executable unpacks itself to a temporary
  folder on each start, which adds a moment before it begins.

## Possible follow-ups

- A small GUI (folder pickers and a "Merge" button) for users who are not
  comfortable with a terminal; `tkinter` ships with Python and bundles cleanly
  with PyInstaller.
- Publishing to PyPI so `pipx install sllogcleaner` works.
- Linux `aarch64` build, if anyone asks for it.
