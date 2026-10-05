# Install the patched Herdr build

This is an **unofficial** build: Herdr 0.9.3 plus the pane graphics capability
fix described in `PATCH-NOTES.md`. It is not affiliated with or endorsed by the
Herdr project.

## 1. Pick the binary for your system

| File | Needs | Use when |
| --- | --- | --- |
| `herdr-patched` (gnu) | glibc ≥ 2.39 | Ubuntu 24.04+, Fedora 40+, Debian trixie+, Arch, openSUSE Tumbleweed |
| `herdr-patched` (musl, separate archive) | nothing (static) | any x86_64 Linux, including older releases |

## 2. Install to a separate path

```sh
install -m 755 herdr-patched ~/.local/bin/herdr-patched
herdr-patched --version      # expect: herdr 0.9.3
```

Do **not** overwrite your daily `herdr` unless you intend to (see below).

## 3. Run it

```sh
herdr-patched --session patched
```

- It shares your config (`~/.config/herdr/config.toml`) but uses its own session
  and socket, so a running official server and its panes are untouched.
- **Never run it without `--session`**: it would connect to your running official
  server, and the graphics decision lives on the server, so the fix would have no
  effect.
- Windows-native Herdr (`herdr.exe`) is **not** covered by this patch.

To replace your daily binary instead:

```sh
cp ~/.local/bin/herdr ~/.local/bin/herdr-official-0.9.3   # back up first
install -m 755 herdr-patched ~/.local/bin/herdr
herdr server stop        # WARNING: this ends processes running in panes
```

Roll back by copying the backup back. `herdr update` overwrites
`~/.local/bin/herdr`, so keep the patched copy under its own name.

## 4. Verify it took effect

Run this inside any pane of the patched session:

```sh
python3 verify-probe.py
```

- Terminal without Kitty graphics (Windows Terminal, GNOME Terminal, Alacritty,
  macOS Terminal.app, tmux without passthrough): the reply should contain
  **only** `\x1b[?62;22c` and **no** `OK`.
- Terminal with Kitty graphics (kitty, Ghostty, WezTerm): the reply should still
  start with `\x1b_Gi=31;OK\x1b\\` — images keep working there.

Visual check: any image-drawing program should now either display its images or
show its own text/block-art fallback. Before the patch both were missing.

## 5. Updating

```sh
herdr update     # official binary only; the patched copy is separate
```

After any upgrade, re-run `verify-probe.py`. If the official build already answers
without `OK`, upstream fixed the issue and you can drop this patch entirely.
Details, including how to rebase the patch after upstream changes, are in
`PATCH-NOTES.md`.
