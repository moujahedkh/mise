# starship-theme: switch between the themes in ~/.config/starship/themes.
#
#   starship-theme                 list themes, mark the active one
#   starship-theme <nr|name>       use theme in this shell only (STARSHIP_CONFIG)
#   starship-theme save <nr|name>  use it here and in every new shell
#   starship-theme reset           back to ~/.config/starship.toml (mise repo)
#   starship-theme preview [nr..]  render themes with a sample prompt
#
# Source from ~/.zshrc. The saved choice lives in ~/.local/state/starship-theme,
# so ~/.config/starship.toml (symlink into the mise repo) is never touched.

STARSHIP_THEME_DIR="$HOME/.config/starship/themes"
STARSHIP_THEME_STATE="${XDG_STATE_HOME:-$HOME/.local/state}/starship-theme/active"

# apply the saved theme at shell start
if [[ -r $STARSHIP_THEME_STATE && -r $STARSHIP_THEME_DIR/$(<$STARSHIP_THEME_STATE) ]]; then
  export STARSHIP_CONFIG="$STARSHIP_THEME_DIR/$(<$STARSHIP_THEME_STATE)"
fi

_starship_theme_resolve() {
  local -a hits
  if [[ $1 == <-> ]]; then
    hits=("$STARSHIP_THEME_DIR"/${(l:2::0:)1}-*.toml(N))
  else
    hits=("$STARSHIP_THEME_DIR"/*${1}*.toml(N))
  fi
  if (( ${#hits} != 1 )); then
    print -u2 "starship-theme: '$1' matches ${#hits} themes"
    return 1
  fi
  print -r -- "$hits[1]"
}

_starship_theme_demo() {
  local d="${XDG_CACHE_HOME:-$HOME/.cache}/starship-theme-demo"
  if [[ ! -d $d/.git ]]; then
    mkdir -p "$d" && (
      cd "$d" && git init -q && print '{"name":"demo"}' > package.json &&
      print a > file.txt && git add . &&
      git -c user.name=demo -c user.email=demo@localhost commit -qm init &&
      print b >> file.txt && : > untracked.txt
    )
  fi
  print -r -- "$d"
}

_starship_theme_preview() {
  local demo f; demo=$(_starship_theme_demo) || return 1
  local -a files
  if (( $# )); then
    for f in "$@"; do files+=("$(_starship_theme_resolve "$f")") || return 1; done
  else
    files=("$STARSHIP_THEME_DIR"/*.toml(N))
  fi
  local -a args=(--status 1 --cmd-duration 4200 --jobs 1 --terminal-width $COLUMNS)
  for f in $files; do
    print -P "\n%B%F{8}━━ ${f:t:r} %f%b%F{8}$(sed -n '1s/^# .* -- //p' "$f")%f"
    (
      cd "$demo"
      export STARSHIP_PWD=${(D)demo}   # normally set by project-prompt.zsh
      local right
      STARSHIP_CONFIG=$f STARSHIP_SHELL= starship prompt "${args[@]}" | sed '/^$/d'
      right=$(STARSHIP_CONFIG=$f STARSHIP_SHELL= starship prompt --right "${args[@]}")
      [[ -n $right ]] && print -r -- "    right: $right"
    )
  done
  print
}

starship-theme() {
  local f
  case $1 in
    '' | list)
      for f in "$STARSHIP_THEME_DIR"/*.toml(N); do
        [[ $f == ${STARSHIP_CONFIG:-} ]] && print -n '* ' || print -n '  '
        print -r -- "${f:t:r}  $(sed -n '1s/^# .* -- //p' "$f")"
      done
      [[ -z ${STARSHIP_CONFIG:-} ]] && print '* (default) ~/.config/starship.toml'
      ;;
    preview) shift; _starship_theme_preview "$@" ;;
    reset)
      unset STARSHIP_CONFIG
      rm -f "$STARSHIP_THEME_STATE"
      print "starship-theme: back to ~/.config/starship.toml"
      ;;
    save)
      f=$(_starship_theme_resolve "$2") || return 1
      export STARSHIP_CONFIG=$f
      mkdir -p "${STARSHIP_THEME_STATE:h}"
      print -r -- "${f:t}" > "$STARSHIP_THEME_STATE"
      print "starship-theme: ${f:t:r} saved for all new shells"
      ;;
    -h | --help) sed -n '3,8s/^# \{0,1\}//p' "$HOME/.config/starship/starship-theme.zsh" ;;
    *)
      f=$(_starship_theme_resolve "$1") || return 1
      export STARSHIP_CONFIG=$f
      print "starship-theme: ${f:t:r} (this shell only; 'starship-theme save $1' to keep)"
      ;;
  esac
}
