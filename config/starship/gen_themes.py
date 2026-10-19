#!/usr/bin/env python3
"""Generate 10 p10k-style starship themes tuned to Ghostty's JetBrains Darcula."""
import json
import os
from collections import defaultdict

OUT = os.path.expanduser("~/.config/starship/themes")

# powerline / nerd font glyphs
PR, PL = "", ""          # solid arrows
TR, TL = "", ""          # thin arrows
CL, CR = "", ""          # round caps
RTR, RTL = "\ue0b5", "\ue0b7"        # thin round separators
SR, SL = "", ""          # slants
GIT = ""                       # git branch
CLOCK, HOURGLASS, CROSS, LOCK, GEAR = "", "", "", "", ""

OS_SYMBOLS = {
    "Macos": "", "Linux": "", "Ubuntu": "", "Debian": "",
    "Arch": "", "Fedora": "", "Alpine": "", "Redhat": "",
    "Windows": "", "Unknown": "",
}
LANGS = {  # module: (symbol, value variable)
    "python": (" ", "${version}( $virtualenv)"),
    "nodejs": (" ", "${version}"),
    "rust": (" ", "${version}"),
    # filled by project-prompt.zsh, which also looks in parent dirs (starship: cwd only)
    "env_var.STARSHIP_GO": ("\ue627 ", "$env_value"),
    "env_var.STARSHIP_JAVA": ("\ue738 ", "$env_value"),
    "env_var.STARSHIP_GRADLE": ("\ue660 ", "$env_value"),
    "env_var.STARSHIP_MAVEN": ("\ue674 ", "$env_value"),
    "docker_context": (" ", "$context"),
    "kubernetes": ("☸ ", "$context"),
}
LANG_VARS = "".join(f"${{{m}}}" for m in LANGS)
GIT_VARS = "$git_branch$git_commit$git_state$git_status"


def q(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(v, ensure_ascii=False)


def base_modules(dir_len=3):
    m = defaultdict(dict)
    m["os"].update(disabled=False)
    m["os.symbols"].update({k: v + " " for k, v in OS_SYMBOLS.items()})
    m["directory"].update(truncation_length=dir_len, truncate_to_repo=True,
                          truncation_symbol="…/", read_only=f" {LOCK}")
    m["git_branch"].update(symbol=f"{GIT} ")
    m["git_commit"].update(only_detached=True, tag_disabled=False, commit_hash_length=7)
    m["git_status"].update(
        ahead="⇡${count}", behind="⇣${count}", diverged="⇡${ahead_count}⇣${behind_count}",
        conflicted="~${count}", untracked="?${count}", stashed="*${count}",
        modified="!${count}", staged="+${count}", renamed="»${count}", deleted="✘${count}",
    )
    m["cmd_duration"].update(min_time=2000)
    m["status"].update(disabled=False, symbol=f"{CROSS} ", recognize_signal_code=True)
    m["time"].update(disabled=False, time_format="%H:%M:%S")
    m["jobs"].update(symbol=f"{GEAR} ", number_threshold=1)
    for name, (sym, _) in LANGS.items():
        m[name].update(symbol=sym)
    m["python"].update(version_format="${raw}")
    # kube-prompt.zsh exports STARSHIP_KUBE while a kube command is typed (or on prod)
    # (env-only on purpose: with detect_files also set, starship 1.27 ignores the env var)
    m["kubernetes"].update(disabled=False, detect_env_vars=["STARSHIP_KUBE"])
    m["character"].update(success_symbol="[❯](bold fg:ok)", error_symbol="[❯](bold fg:err)",
                          vimcmd_symbol="[❮](bold fg:ok)")
    return m


def lang_formats(m, fmt):
    """fmt(module, symbol_var_block, value_var) -> (format, style)"""
    for name, (_, var) in LANGS.items():
        m[name]["format"] = fmt(name, var)


def emit(path, title, desc, palette_name, palette, fmt, right, mods, add_newline=True, extra=None, tail=None):
    lines = [
        f"# {title} -- {desc}",
        "# generated for Ghostty 'JetBrains Darcula' (bg #202020) + FiraCode Nerd Font Mono",
        '"$schema" = "https://starship.rs/config-schema.json"',
        f"add_newline = {q(add_newline)}",
        "command_timeout = 500",
        "scan_timeout = 10",
        f"palette = {q(palette_name)}",
        f"format = {q(fmt)}",
    ]
    if right:
        lines.append(f"right_format = {q(right)}")
    for k, v in (extra or {}).items():
        lines.append(f"{k} = {q(v)}")
    lines += ["", f"[palettes.{palette_name}]"]
    lines += [f"{k} = {q(v)}" for k, v in palette.items()]
    for name, d in mods.items():
        if not d:
            continue
        lines += ["", f"[{name}]"] + [f"{k} = {q(v)}" for k, v in d.items()]
    if tail:
        lines += ["", tail.strip()]
    with open(os.path.join(OUT, path), "w") as f:
        f.write("\n".join(lines) + "\n")


def chain_left(m, sep, os_c, dir_c, git_c):
    """os -> dir -> git as one contiguous powerline. The directory module's
    repo_root_format (used only inside a repo) hands over into the git colour,
    its plain format closes onto the terminal background -- so no stray arrow
    shows outside a repo."""
    (ofg, obg), (dfg, dbg), (gfg, gbg) = os_c, dir_c, git_c
    m["os"].update(format=f"[ $symbol]({ofg_bg(ofg, obg)})[{sep}](fg:{obg} bg:{dbg})")
    seg = ofg_bg(dfg, dbg)
    m["directory"].update(
        style=seg, read_only_style=f"fg:err bg:{dbg}",
        format=f"[ $path ]($style)[$read_only ]($read_only_style)[{sep}](fg:{dbg})",
        repo_root_style=f"bold {seg}", before_repo_root_style=seg,
        repo_root_format=(f"[ $before_root_path]($before_repo_root_style)[$repo_root]($repo_root_style)"
                          f"[$path ]($style)[$read_only ]($read_only_style)[{sep}](fg:{dbg} bg:{gbg})"),
    )
    gseg = ofg_bg(gfg, gbg)
    m["git_branch"].update(style=gseg, format="[ $symbol$branch ]($style)")
    m["git_commit"].update(style=gseg, format="[  $hash$tag ]($style)")
    m["git_state"].update(style=gseg, format="[\\($state $progress_current/$progress_total\\) ]($style)")
    m["git_status"].update(style=f"bold {gseg}", format="([$all_status$ahead_behind ]($style))")
    return f"$os$directory({GIT_VARS}[{sep}](fg:{gbg}))"


def ofg_bg(fg, bg):
    return f"fg:{fg} bg:{bg}"


def right_segments(m, sep, colors, time_c, dur_c, status_c, jobs_c):
    """Self-contained segments: each draws its own leading arrow, so any
    combination of present/absent modules renders cleanly."""
    def seg(fg, bg, body):
        return f"[{sep}](fg:{bg})[{body}]({ofg_bg(fg, bg)})"
    m["status"]["format"] = seg(*status_c, " $symbol$status ")
    m["cmd_duration"]["format"] = seg(*dur_c, f" {HOURGLASS} $duration ")
    m["jobs"]["format"] = seg(*jobs_c, " $symbol$number ")
    m["time"]["format"] = seg(*time_c, f" $time {CLOCK} ")
    for name, (_, var) in LANGS.items():
        m[name]["format"] = seg(*colors[name], f" $symbol{var} ")
    return f"$status$cmd_duration$jobs{LANG_VARS}$time"


# ---------------------------------------------------------------- 01 classic
def t01():
    p = dict(seg="#303030", sep="#585858", frame="#4e4e4e", text="#adadad", os="#eeeeee",
             dir="#6d9df1", git="#67ff4f", dirty="#c2c300", lang="#60d3d1", dur="#c2c300",
             time="#949494", ok="#67ff4f", err="#fa5355")
    m = base_modules()
    thin = f"[{RTR}](fg:sep bg:seg)"
    m["os"].update(style="fg:os bg:seg", format="[ $symbol]($style)")
    # path comes from project-prompt.zsh (STARSHIP_PWD): full, shortened only when
    # the first line would overflow -- starship's own truncation is length-fixed
    m["directory"].update(disabled=True)
    m["env_var.STARSHIP_PWD"].update(style="bold fg:dir bg:seg", format=f"{thin}[ $env_value ]($style)")
    m["git_branch"].update(style="fg:git bg:seg", format=f"{thin}[ $symbol$branch ]($style)")
    m["git_commit"].update(style="fg:git bg:seg", format=f"{thin}[  $hash$tag ]($style)")
    m["git_state"].update(style="fg:dirty bg:seg", format="[\\($state\\) ]($style)")
    m["git_status"].update(style="fg:dirty bg:seg", format="([$all_status$ahead_behind ]($style))")
    rthin = f"[{RTL}](fg:sep bg:seg)"
    m["status"]["format"] = f"[ $symbol$status ](fg:err bg:seg){rthin}"
    m["cmd_duration"]["format"] = f"[ $duration {HOURGLASS} ](fg:dur bg:seg){rthin}"
    m["jobs"]["format"] = f"[ $symbol$number ](fg:lang bg:seg){rthin}"
    lang_formats(m, lambda n, v: f"[ {v} $symbol](fg:lang bg:seg){rthin}")
    m["time"]["format"] = f"[ $time {CLOCK} ](fg:time bg:seg)"
    m["kubernetes"].update(style="fg:lang bg:seg",
                           format=f"[ $context( \\($namespace\\)) $symbol]($style){rthin}")
    kube = f"""
[[kubernetes.contexts]]
context_pattern = ".*prod.*"
style = "bold fg:#ffffff bg:#d70000"
symbol = "\uf071 PROD "

[[kubernetes.contexts]]
context_pattern = "^dev$"
style = "fg:git bg:seg"

[[kubernetes.contexts]]
context_pattern = "^rancher-desktop$"
context_alias = "local"
style = "fg:lang bg:seg"
"""
    m["fill"].update(symbol="·", style="fg:frame")
    fmt = (f"[╭─](fg:frame)[{CL}](fg:seg)$os${{env_var.STARSHIP_PWD}}{GIT_VARS}[{CR}](fg:seg)"
           f"$fill[{CL}](fg:seg)$status$cmd_duration$jobs{LANG_VARS}$time[{CR}](fg:seg)[─╮](fg:frame)"
           f"$line_break[╰─](fg:frame)$character")
    emit("01-classic.toml", "01 Classic", "p10k classic, rounded: grey pills, thin round separators, frame, dotted fill",
         "classic", p, fmt, None, m, tail=kube)


# ---------------------------------------------------------------- 02 rainbow
def t02():
    p = dict(dark="#202020", light="#eeeeee", os="#adadad", dir="#4581eb", git="#5faf00",
             py="#c2c300", node="#126e00", rust="#d75f00", go="#33c2c1", java="#af5f00",
             docker="#6d9df1", kube="#4581eb", dur="#ffaf00", status="#fa5355", jobs="#33c2c1",
             time="#585858", ok="#67ff4f", err="#fa5355")
    m = base_modules()
    left = chain_left(m, PR, ("dark", "os"), ("light", "dir"), ("dark", "git"))
    colors = dict(python=("dark", "py"), nodejs=("light", "node"), rust=("dark", "rust"),
                  **{"env_var.STARSHIP_GO": ("dark", "go"), "env_var.STARSHIP_JAVA": ("light", "java"),
                     "env_var.STARSHIP_GRADLE": ("light", "java"), "env_var.STARSHIP_MAVEN": ("light", "java")}, docker_context=("dark", "docker"),
                  kubernetes=("light", "kube"))
    right = right_segments(m, PL, colors, ("light", "time"), ("dark", "dur"),
                           ("light", "status"), ("dark", "jobs"))
    m["fill"].update(symbol=" ")
    fmt = f"{left}$fill{right}$line_break$character"
    emit("02-rainbow.toml", "02 Rainbow", "p10k rainbow: every segment its own colour, two lines",
         "rainbow", p, fmt, None, m)


# ---------------------------------------------------------------- 03 lean
def t03():
    p = dict(os="#eeeeee", dir="#6d9df1", git="#67ff4f", dirty="#c2c300", lang="#60d3d1",
             dur="#c2c300", time="#808080", muted="#585858", ok="#67ff4f", err="#fa5355")
    m = base_modules()
    m["os"].update(style="fg:os", format="[$symbol]($style)")
    m["directory"].update(style="bold fg:dir", repo_root_style="bold fg:dir",
                          format="[$path]($style)[$read_only]($read_only_style) ")
    m["git_branch"].update(style="fg:git", format="[$symbol$branch]($style) ")
    m["git_commit"].update(style="fg:git", format="[ $hash$tag]($style) ")
    m["git_state"].update(style="fg:dirty", format="[\\($state\\)]($style) ")
    m["git_status"].update(style="fg:dirty", format="([$all_status$ahead_behind]($style) )")
    m["status"]["format"] = "[$symbol$status]($style) "
    m["status"]["style"] = "fg:err"
    m["cmd_duration"].update(style="fg:dur", format=f"[{HOURGLASS} $duration]($style) ")
    m["jobs"].update(style="fg:lang", format="[$symbol$number]($style) ")
    lang_formats(m, lambda n, v: f"[$symbol{v}](fg:lang) ")
    m["time"].update(style="fg:time", format=f"[{CLOCK} $time]($style)")
    m["fill"].update(symbol=" ")
    fmt = (f"$os$directory{GIT_VARS}$fill$status$cmd_duration$jobs{LANG_VARS}$time"
           f"$line_break$character")
    emit("03-lean.toml", "03 Lean", "p10k lean: no backgrounds, colour-only text, two lines",
         "lean", p, fmt, None, m)


# ---------------------------------------------------------------- 04 pure
def t04():
    p = dict(dir="#6d9df1", git="#808080", arrows="#60d3d1", dirty="#fb82ff", dur="#c2c300",
             muted="#585858", ok="#fb82ff", err="#fa5355")
    m = base_modules(dir_len=4)
    m["os"].update(style="fg:muted", format="[$symbol]($style)")
    m["directory"].update(style="fg:dir", format="[$path]($style)[$read_only]($read_only_style) ")
    m["git_branch"].update(style="fg:git", format="[$branch]($style)")
    m["git_commit"].update(style="fg:git", format="[$hash$tag]($style)")
    m["git_state"].update(style="fg:git", format=" [$state]($style)")
    m["git_status"].update(
        style="fg:arrows", format="([$conflicted$modified$staged$untracked$renamed$deleted](fg:dirty)[ $ahead_behind]($style)) ",
        modified="*", staged="+", untracked="?", renamed="", deleted="*", conflicted="=", stashed="",
        ahead="⇡", behind="⇣", diverged="⇡⇣")
    m["status"].update(style="fg:err", format="[$symbol$status]($style) ")
    m["cmd_duration"].update(style="fg:dur", format="[$duration]($style) ")
    m["jobs"].update(style="fg:muted", format="[$symbol$number]($style) ")
    lang_formats(m, lambda n, v: f"[$symbol{v}](fg:muted) ")
    m["time"].update(style="fg:muted", format="[$time]($style)")
    fmt = f"$directory{GIT_VARS}$cmd_duration{LANG_VARS}$line_break$os$character"
    right = "$status$jobs$time"
    emit("04-pure.toml", "04 Pure", "sindresorhus/pure: quiet two-liner, dim right prompt",
         "pure", p, fmt, right, m)


# ---------------------------------------------------------------- 05 pastel
def t05():
    p = dict(dark="#202020", os="#cba6f7", dir="#f5a9b8", git="#fab387", lang="#a6e3a1",
             dur="#f9e2af", status="#f38ba8", jobs="#89dceb", time="#b4befe",
             ok="#a6e3a1", err="#f38ba8")
    m = base_modules()
    left = chain_left(m, PR, ("dark", "os"), ("dark", "dir"), ("dark", "git"))
    colors = {n: ("dark", "lang") for n in LANGS}
    right = right_segments(m, PL, colors, ("dark", "time"), ("dark", "dur"),
                           ("dark", "status"), ("dark", "jobs"))
    m["time"]["time_format"] = "%H:%M"
    emit("05-pastel.toml", "05 Pastel", "soft pastel powerline, single line + right prompt",
         "pastel", p, f"{left} $character", right, m)


# ---------------------------------------------------------------- 06 neon
def t06():
    p = dict(black="#0a0a0a", panel="#1a1a2e", frame="#bc13fe", pink="#ff2bd6", cyan="#00f0ff",
             yellow="#f9f002", green="#39ff14", red="#ff073a", ok="#39ff14", err="#ff073a")
    m = base_modules()
    left = chain_left(m, SR, ("black", "pink"), ("black", "cyan"), ("black", "yellow"))
    sl = "[╱](fg:frame bg:panel)"
    m["status"]["format"] = f"[ $symbol$status ](bold fg:red bg:panel){sl}"
    m["cmd_duration"]["format"] = f"[ {HOURGLASS} $duration ](fg:yellow bg:panel){sl}"
    m["jobs"]["format"] = f"[ $symbol$number ](fg:cyan bg:panel){sl}"
    lang_formats(m, lambda n, v: f"[ $symbol{v} ](fg:green bg:panel){sl}")
    m["time"]["format"] = f"[ $time {CLOCK} ](fg:pink bg:panel)"
    m["fill"].update(symbol="─", style="fg:frame")
    fmt = (f"[╭─](fg:frame){left}$fill[{SL}](fg:panel)$status$cmd_duration$jobs{LANG_VARS}$time"
           f"[{SR}](fg:panel)$line_break[╰─](fg:frame)$character")
    m["character"].update(success_symbol="[❯❯](bold fg:pink)", error_symbol="[❯❯](bold fg:err)")
    emit("06-neon.toml", "06 Neon", "cyberpunk: neon blocks, slanted cuts, magenta frame",
         "neon", p, fmt, None, m)


# ---------------------------------------------------------------- 07 rounded
def t07():
    p = dict(dark="#202020", light="#eeeeee", os="#adadad", dir="#6d9df1", git="#67ff4f",
             dirty="#c2c300", lang="#60d3d1", dur="#ffd75f", status="#fb7172", time="#444444",
             ok="#67ff4f", err="#fa5355")
    m = base_modules()

    def pill(fg, bg, body):
        return f"[{CL}](fg:{bg})[{body}](fg:{fg} bg:{bg})[{CR}](fg:{bg})"
    m["os"]["format"] = pill("dark", "os", "$symbol") + " "
    m["directory"].update(read_only_style="fg:err bg:dir",
                          format=pill("dark", "dir", "$path[$read_only]($read_only_style)") + " ")
    m["git_branch"]["format"] = pill("dark", "git", "$symbol$branch") + " "
    m["git_commit"]["format"] = pill("dark", "git", " $hash$tag") + " "
    m["git_state"]["format"] = pill("dark", "dirty", "$state") + " "
    m["git_status"]["format"] = "(" + pill("dark", "dirty", "$all_status$ahead_behind") + " )"
    m["status"]["format"] = pill("dark", "status", "$symbol$status") + " "
    m["cmd_duration"]["format"] = pill("dark", "dur", f"{HOURGLASS} $duration") + " "
    m["jobs"]["format"] = pill("dark", "lang", "$symbol$number") + " "
    lang_formats(m, lambda n, v: pill("dark", "lang", f"$symbol{v}") + " ")
    m["time"].update(time_format="%H:%M", format=pill("light", "time", f"{CLOCK} $time"))
    emit("07-rounded.toml", "07 Rounded", "separate round pills, single line + right prompt",
         "rounded", p, f"$os$directory{GIT_VARS}$character",
         f"$status$cmd_duration$jobs{LANG_VARS}$time", m)


# ---------------------------------------------------------------- 08 two-line right
def t08():
    p = dict(dark="#202020", light="#eeeeee", os="#1a3272", dir="#4581eb", git="#126e00",
             lang="#33c2c1", gstat="#c2c300", dur="#555555", status="#fa5355", jobs="#60d3d1",
             time="#303030", ok="#67ff4f", err="#fa5355")
    m = base_modules()
    left = chain_left(m, PR, ("light", "os"), ("light", "dir"), ("light", "git"))
    # git status moves right, so the git segment only carries the branch
    m["git_status"]["format"] = f"([{PL}](fg:gstat)[ $all_status$ahead_behind ](fg:dark bg:gstat))"
    left = left.replace("$git_status", "")
    right = right_segments(m, PL, {n: ("dark", "lang") for n in LANGS}, ("light", "time"),
                           ("light", "dur"), ("light", "status"), ("dark", "jobs"))
    lang_formats(m, lambda n, v: f" [$symbol{v}](fg:lang)")
    right = right.replace(LANG_VARS, "")
    right = right.replace("$status", "$status$git_status")
    emit("08-twoline-right.toml", "08 Two-Line Right",
         "left: path + branch + tools; right on line 2: status, git status, duration, time",
         "twoline", p, f"{left}{LANG_VARS}$line_break$character", right, m)


# ---------------------------------------------------------------- 09 darcula
def t09():
    # JetBrains IDE Darcula editor colours (keyword orange, string green, number blue, ...)
    p = dict(editor="#2b2b2b", panel="#3c3f41", text="#a9b7c6", orange="#cc7832", yellow="#ffc66d",
             green="#6a8759", blue="#6897bb", purple="#9876aa", red="#bc3f3c", gray="#808080",
             ok="#6a8759", err="#bc3f3c")
    m = base_modules()
    left = chain_left(m, PR, ("text", "panel"), ("editor", "orange"), ("editor", "green"))
    colors = dict(python=("editor", "yellow"), nodejs=("editor", "green"), rust=("editor", "orange"),
                  **{"env_var.STARSHIP_GO": ("editor", "blue"), "env_var.STARSHIP_JAVA": ("editor", "orange"),
                     "env_var.STARSHIP_GRADLE": ("editor", "orange"), "env_var.STARSHIP_MAVEN": ("editor", "orange")}, docker_context=("editor", "blue"),
                  kubernetes=("editor", "purple"))
    right = right_segments(m, PL, colors, ("text", "panel"), ("editor", "yellow"),
                           ("text", "red"), ("editor", "purple"))
    emit("09-darcula.toml", "09 Darcula", "JetBrains Darcula IDE palette, single line + right prompt",
         "darcula", p, f"{left} $character", right, m)


# ---------------------------------------------------------------- 10 compact
def t10():
    p = dict(os="#adadad", dir="#6d9df1", git="#67ff4f", dirty="#c2c300", lang="#60d3d1",
             dur="#c2c300", time="#585858", ok="#67ff4f", err="#fa5355")
    m = base_modules(dir_len=2)
    m["directory"].update(style="bold fg:dir",
                          format="[$path]($style)[$read_only]($read_only_style) ")
    m["os"].update(style="fg:os", format="[$symbol]($style)")
    m["git_branch"].update(style="fg:git", symbol="", format=f"[{TR} $branch]($style)")
    m["git_commit"].update(style="fg:git", format=f"[{TR} $hash]($style)")
    m["git_state"].update(style="fg:dirty", format=" [$state]($style)")
    m["git_status"].update(style="fg:dirty", format="([$all_status$ahead_behind]($style))")
    m["status"].update(style="fg:err", symbol="✘", format=" [$symbol$status]($style)")
    m["cmd_duration"].update(style="fg:dur", format=" [$duration]($style)")
    m["jobs"].update(style="fg:lang", symbol="✦", format=" [$symbol$number]($style)")
    lang_formats(m, lambda n, v: " [$symbol](fg:lang)")  # icon only, no version call output
    m["time"].update(style="fg:time", time_format="%H:%M", format="[$time]($style) ")
    fmt = f"$time$os$directory{GIT_VARS}{LANG_VARS}$cmd_duration$jobs$status $character"
    emit("10-compact.toml", "10 Compact", "everything on one short line, icons only",
         "compact", p, fmt, None, m, add_newline=False)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for t in (t01, t02, t03, t04, t05, t06, t07, t08, t09, t10):
        t()
    print("\n".join(sorted(os.listdir(OUT))))
