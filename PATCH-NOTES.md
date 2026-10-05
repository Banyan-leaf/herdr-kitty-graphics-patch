# herdr「pane 图像闪一下消失」补丁 · 技术说明
# herdr "pane images flash and disappear" patch · Technical notes

---

## 这是什么
## What this is

这是给 [herdrdev/herdr](https://github.com/herdrdev/herdr) 做的**本地补丁**，不是上游提交。herdr 只接受 maintainer 和 `.github/APPROVED_CONTRIBUTORS` 名单内的人提 PR，其他人按他们的 `CONTRIBUTING.md` 只能报 bug，所以这份补丁只留在本地／你自己的仓库里。

补丁修的是**一类**问题：pane 的图形能力回答与实际能否显示不一致。受害的是**任何在 pane 里画图的程序**，与具体程序无关；鲸娘（dsh-TUI）只是最直观的复现案例。

- 基线：`b064806`（写这份说明时的 `master`）
- 分支：`fix/kitty-graphics-capability`
- 提交：`450698e`，18 个文件，+651/−11
- 补丁文件：`0001-fix-stop-advertising-kitty-graphics-herdr-cannot-del.patch`
- 范围：**只改 herdr**。dsh-TUI 不需要任何改动——它的能力探测和降级渲染都是对的，问题出在 herdr 给出的答案。

This is a **local patch** for [herdrdev/herdr](https://github.com/herdrdev/herdr), not an upstream submission. Herdr only accepts implementation pull requests from maintainers and the names in `.github/APPROVED_CONTRIBUTORS`; everyone else is asked to file a bug report, so this patch stays local or in your own fork.

The patch fixes a **class** of problem: a pane's graphics answer disagreeing with what can actually be displayed. Every program that draws images inside a pane is affected; the dsh-TUI whale-girl mascot is just the easiest reproduction to see.

- base: `b064806` (`master` when this was written)
- branch: `fix/kitty-graphics-capability`
- commit: `450698e`, 18 files, +651/−11
- patch file: `0001-fix-stop-advertising-kitty-graphics-herdr-cannot-del.patch`
- scope: **herdr only.** dsh-TUI needs no change; its capability probe and its fallback rendering are both correct. The bug is herdr's answer, not its reader.

---

## Bug 是什么
## The bug in one line

pane 终端只会根据**自己解析器的状态**回答 Kitty 图形能力查询（`a=q`），从不检查当前挂着的客户端、外层终端到底能不能显示图像。于是**任何会探测能力、且优先 Kitty 的图片程序**（图片预览、编辑器/文件管理器图片插件、绘图与图表输出、带立绘的 TUI……）都会选错协议，画出一张看不见的图——而它原本能显示的字符画/占位保底已经被顶掉了。最终症状统一是"闪一下、然后一片空白"，且没有任何报错。

常见受害者终端：**Windows Terminal**（有 Sixel、没有 Kitty，本来能显示图）、GNOME Terminal / VTE、Alacritty、macOS Terminal.app、默认 xterm、未开透传的 tmux / screen。真正实现 Kitty 的终端（kitty、Ghostty、WezTerm）不受影响。

补丁前还有第二个问题：`terminal.kitty_graphics = false` 只是"不主动开启"协议，pane 终端仍保留 libghostty 的默认图片配额，因此依然会回 `OK`。

这两处修复都与具体程序无关：不会为任何程序做特判，也不需要程序改一行代码。

A pane terminal answers the Kitty graphics capability query (`a=q`) from its own parser state, without checking whether the attached client's outer terminal can display placements. **Any image-drawing program that probes and prefers Kitty** (image previews, editor/file-manager image plugins, plotting output, TUIs with artwork) then picks Kitty over Sixel or over its text fallback, paints a raster, and nothing appears — while the fallback it had been showing is already replaced. The symptom is always a brief flash followed by a blank area, and there is no error anywhere.

Terminals that hit this: **Windows Terminal** (Sixel but no Kitty, so images were displayable before), GNOME Terminal / VTE, Alacritty, macOS Terminal.app, default xterm, tmux / screen without passthrough. Terminals that really implement Kitty (kitty, Ghostty, WezTerm) are unaffected.

Second gap before the patch: `terminal.kitty_graphics = false` only skipped *enabling* the protocol, so the pane terminal kept libghostty's default image quota and still answered `a=q` with OK.

Both changes are application-agnostic: nothing is special-cased per program, and no program needs a code change.

---

## 补丁做了什么
## What the patch does

1. `terminal.kitty_graphics = false` 现在会**真正关闭** pane 终端的协议：libghostty 把"图片配额为 0"视为"不支持图像"，命令被忽略、`a=q` 不再应答。
2. 客户端在握手前**探测外层终端**（发 `a=q` 加一个 DA1 哨兵，也就是所有图片类 TUI 用的那套查询），把答案作为握手字段 `kitty_graphics` 上报（JSON、可选、`#[serde(default = "default_true")]`，所以不带该字段的旧客户端仍能解码并保持原行为）。
3. 服务端把 pane 图形能力改为"设置开启 **且** 有一个能渲染的已连接客户端"；这个答案变化时，会**重新应用到活着的 pane 终端**。没有客户端连接、或客户端从不上报时，保持原来的乐观答案。

1. `terminal.kitty_graphics = false` now disables the protocol in the pane terminal. libghostty treats a zero image-storage quota as "images unsupported": commands are ignored and `a=q` goes unanswered.
2. The client probes the outer terminal before the handshake (`a=q` plus a DA1 sentinel — the query image-capable TUIs send) and reports the answer as the optional endpoint hello field `kitty_graphics` (`#[serde(default = "default_true")]`, so a hello without it still decodes and keeps today's behaviour).
3. The server gates pane graphics on the setting **and** on an attached client that can render; live pane terminals are re-applied when that answer changes. A client that never reports, and a session with no client attached, keep the previous optimistic answer.

---

## 怎么应用和构建
## How to apply and build

```sh
git checkout -b fix/kitty-graphics-capability <base-commit>
git am 0001-*.patch            # 或者：git cherry-pick 450698e
```

构建需要 Rust 1.96.1（见 `rust-toolchain.toml`）和 **Zig 0.16.0**（见 `crates/ghostty-vt/build.rs`）；Zig 不在 PATH 上时用 `ZIG=` 指过去。

```sh
ZIG=/path/to/zig cargo build --release
```

Building needs Rust 1.96.1 (`rust-toolchain.toml`) and Zig **0.16.0** (`crates/ghostty-vt/build.rs`); point `ZIG` at the binary if it is not on PATH.

---

## 怎么验证
## How to verify

```sh
python3 verify-probe.py        # 在任意 herdr pane 里跑
```

| 外层终端 / Outer terminal | 期望的 `repr:` / Expected `repr:` |
| --- | --- |
| Windows Terminal、GNOME Terminal、Alacritty、没开透传的 tmux | `b'\x1b[?62;22c'` —— 只有 DA1，**没有 OK** / DA1 only, **no OK** |
| kitty、Ghostty、WezTerm | `b'\x1b_Gi=31;OK\x1b\\\x1b[?62;22c'` —— 先回 OK / OK first |

视觉检查：dsh-tui 设 `companion.skin: whaleGirl`，吉祥物应当稳定显示并持续动画，而不是闪一下后留个空槽。

Visual check: dsh-TUI with `companion.skin: whaleGirl` draws its block-art mascot and keeps animating, instead of flashing once and leaving a blank slot.

---

## 上游自己修好了怎么判断
## If upstream fixes it themselves

**先做这一步，再考虑 rebase：**

1. 在官方版本上，用一个不支持 Kitty 图形的终端，在 pane 里跑 `python3 verify-probe.py`；
2. 如果回复里**已经没有 `OK`**，说明上游修好了——删掉本地分支和补丁，直接用官方版本。

Check this **before** rebasing anything:

1. run `python3 verify-probe.py` inside a pane of the official build on a non-Kitty terminal;
2. if the reply already has no `OK`, upstream fixed it — delete this branch and the patch, and use the official build.

---

## 补丁打不上了怎么办
## If the patch stops applying

重新把同样的逻辑挂到新代码上即可；改动是刻意做得很局部的：

| 区域 / Area | 文件 / Files |
| --- | --- |
| 关闭协议 + 能力决策 / disable + capability decision | `src/kitty_graphics.rs`、`crates/ghostty-vt/src/lib.rs`（`disable_kitty_graphics`） |
| 建 pane 时的调用点 / pane spawn call sites | `src/pane.rs`（两处 spawn 都改为调 `kitty_graphics::apply_to_terminal`） |
| 活终端重新应用 / live re-application | `src/pane.rs`（`PaneRuntime::apply_kitty_graphics`）、`src/terminal/runtime.rs` |
| 宿主探测 / host probe | `src/client/terminal_setup.rs`（`probe_host_kitty_graphics`） |
| 探测接线 + 握手字段 / probe plumbing + hello field | `src/client/mod.rs`、`src/client/handshake.rs`、`src/client/state.rs`、`src/client/loop_config.rs`、`src/client/endpoint/supervisor.rs`、`src/protocol/endpoint.rs` |
| 服务端门控 / server gate | `src/server/clients.rs`、`src/server/headless.rs`（`refresh_kitty_graphics_delivery`，在接入与断开时调用） |

如果上游把端点协议升到新一代，把能力字段迁到新 codec，并**保持可选 + 默认 `true`**，否则老客户端会被误当成"不能画图"。

Re-hang the same logic on the new code; the additions are deliberately local:

If the endpoint protocol moves to a new generation, carry the capability into the new codec and keep the field optional with a `true` default, so older clients keep the optimistic answer.

---

## 升级注意：别混用二进制
## Upgrade hygiene — do not mix builds

- 补丁版二进制建议放独立路径（本机是 `~/.local/bin/herdr-patched`），这样 `herdr update` 只会覆盖官方那个。
- **客户端和服务端必须来自同一个二进制**：图形能力的判断在服务端，宿主探测在客户端；混用会重新触发这个 bug（或被版本检查拒绝）。
- 每次升级后：`herdr --version`，然后重新跑一次 `verify-probe.py`。

- Keep the patched binary at a separate path (on this machine: `~/.local/bin/herdr-patched`) so `herdr update` only replaces the official one.
- Run client and server from the **same** binary: the graphics decision lives in the server, the host probe in the client. A mismatch reintroduces the bug (or gets rejected by the version check).
- After any upgrade: `herdr --version`, then `verify-probe.py` again.

---

## 已知局限
## Known limits

- **Windows 原生客户端**（`herdr.exe` + Windows Terminal）：宿主探测只做了 Unix 侧，那边保留乐观答案，所以**问题依旧**——对所有画图的程序一视同仁。
- 已经启动着的程序不会自动改（协议在启动时一次性选定），需要**重启那个程序**。
- 盲目试 Kitty、不探测的程序照旧会画看不见的图；这不是 herdr 行为改变，但症状一样。
- 同时挂着多个客户端时，只要有**一个**能渲染就会回 `OK`，所以同时挂着的"不能渲染"的客户端仍然看不到图。

- **Windows-native clients** (`herdr.exe` + Windows Terminal): no host probe yet (the optimistic answer is kept), so the issue **persists** there — for every image-drawing program.
- A child that already probed before the capability was known keeps its choice; **restart that child**.
- Apps that try Kitty without probing still paint invisible images (not a herdr behaviour change, but the same symptom).
- With several attached clients the answer is optimistic if **any** of them can render, so a simultaneously attached non-capable client still shows nothing.

---

## 本机验证记录
## What was verified

- 新增 10 个测试；`cargo fmt --check`、`cargo clippy --all-targets` 干净。
- 全量 `cargo nextest run --no-fail-fast`：3947 跑 / 3946 过。唯一失败项 `sigwinch_refreshes_host_palette_without_resizing` 在**未改动的 baseline 上也失败**——它断言必须查询宿主调色板，而 WSL 下 Linux 平台故意跳过该查询。
- 维护脚本测试 150 个全过。
- **真实 Windows Terminal（WSL）端到端**（补丁版）：pane 里的子进程只收到 DA1，没有 `OK`；作为复现案例，dsh-TUI 鲸娘吉祥物出现在单元格网格里（151 个半块字符），30 秒后仍在动画。对照：官方 0.9.3 的探针回 `OK`，且它的 dsh-TUI pane 吉祥物槽位是空白。
- 模拟外层终端矩阵：0.9.3 + WT 型 ⇒ `OK`（复现 bug）；补丁版 + WT 型 ⇒ 无 `OK`（修好）；补丁版 + Kitty 型 ⇒ `OK`（能画的终端无回归）。
- 补丁版成品二进制（`~/.local/bin/herdr-patched`，release 31MB，md5 `29485147575dcbdb310d6f214a031f44`）复测以上前两项，结果一致。
- **没跑**：`just windows-lint`（本机没有 Windows SDK），所以 Windows 专用的那段 stub 只经过代码审阅、没有编译验证。

- 10 new tests; `cargo fmt --check` and `cargo clippy --all-targets` clean.
- Full `cargo nextest run --no-fail-fast`: 3947 run, 3946 pass. The single failure (`sigwinch_refreshes_host_palette_without_resizing`) also fails on the untouched baseline, because it asserts a host palette query that Linux deliberately skips under WSL.
- Maintenance script tests: 150 pass.
- **End-to-end on a real Windows Terminal from WSL** (patched build): a pane child receives DA1 only, no `OK`; as the reproduction case, the dsh-TUI whale-girl mascot is present in the cell grid (151 half-block cells) and still animating after 30 s. Control on the official 0.9.3: the probe answers `OK`, and its dsh-TUI pane has a blank mascot slot.
- Emulated outer terminals: 0.9.3 + WT-like host ⇒ `OK` (bug reproduced); patched + WT-like host ⇒ no `OK` (fixed); patched + Kitty-like ⇒ `OK` (no regression on capable terminals).
- The shipped release binary (`~/.local/bin/herdr-patched`, 31 MB, md5 `29485147575dcbdb310d6f214a031f44`) re-tested the first two rows with the same results.
- **Not run**: `just windows-lint` (no Windows SDK on this machine), so the Windows-only stub is compile-reviewed, not compiled.
