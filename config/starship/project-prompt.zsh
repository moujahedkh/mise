# project-prompt: feed starship the project context it cannot work out itself.
# Starship's language modules only look at the current directory; this looks
# from $PWD upwards to the git root (or $HOME), so src/main/java counts too.
# Results go out as environment variables the themes read:
#
#   STARSHIP_KUBE    set -> [kubernetes] shows (it lists it in detect_env_vars)
#                      - while the command line starts with a kube tool
#                      - inside a helm / helmfile / kustomize / skaffold project
#                      - always while the context matches STARSHIP_KUBE_PROD_PATTERN
#   STARSHIP_JAVA    JDK version inside a gradle / maven project
#   STARSHIP_GRADLE  gradle wrapper version, STARSHIP_MAVEN maven wrapper version
#   STARSHIP_GO      go toolchain version inside a go module
#   STARSHIP_PWD     $PWD, shortened only when the first prompt line would overflow
#
# Everything is read from files (kubeconfig, wrapper properties, the JDK's
# release file, GOROOT/VERSION): no kubectl/java/go process per prompt.
# Source from ~/.zshrc after `starship init zsh`.

typeset -ga STARSHIP_KUBE_COMMANDS=(kubectl helm k9s kubectx kubens kustomize stern)
typeset -g  STARSHIP_KUBE_PROD_PATTERN='*prod*'
typeset -ga STARSHIP_KUBE_PROJECT_FILES=(
  Chart.yaml helmfile.yaml helmfile.yaml.gotmpl kustomization.yaml skaffold.yaml
  helm/Chart.yaml chart/Chart.yaml deploy/Chart.yaml
  'helm/*/Chart.yaml' 'charts/*/Chart.yaml' 'deploy/*/Chart.yaml'
  deploy/kustomization.yaml k8s/kustomization.yaml kustomize/kustomization.yaml
  'k8s/*/kustomization.yaml' 'kustomize/*/kustomization.yaml'
)  # quoted entries are globs, expanded per directory in _pp_scan
typeset -ga STARSHIP_JVM_PROJECT_FILES=(build.gradle build.gradle.kts settings.gradle settings.gradle.kts pom.xml)
typeset -ga STARSHIP_GO_PROJECT_FILES=(go.mod go.work)

typeset -g _pp_prod= _pp_kube_base= _pp_kube_ctx=
typeset -g _pp_kube_project= _pp_jvm= _pp_go= _pp_gradle= _pp_maven= _pp_git_root=
typeset -g _pp_java_key= _pp_java_ver= _pp_go_key= _pp_go_ver=

# one walk from $PWD up to the git root / $HOME collects every marker
_pp_scan() {
  local d=$PWD f
  local -a hit
  _pp_kube_project= _pp_jvm= _pp_go= _pp_gradle= _pp_maven= _pp_git_root=
  while true; do
    if [[ -z $_pp_kube_project ]]; then
      for f in $STARSHIP_KUBE_PROJECT_FILES; do
        hit=($d/${~f}(N[1]))
        (( $#hit )) && { _pp_kube_project=1; break }
      done
    fi
    if [[ -z $_pp_jvm ]]; then
      for f in $STARSHIP_JVM_PROJECT_FILES; do
        [[ -e $d/$f ]] && { _pp_jvm=1; break }
      done
    fi
    if [[ -z $_pp_go ]]; then
      for f in $STARSHIP_GO_PROJECT_FILES; do
        [[ -e $d/$f ]] && { _pp_go=1; break }
      done
    fi
    [[ -z $_pp_gradle && -r $d/gradle/wrapper/gradle-wrapper.properties ]] &&
      _pp_gradle=$d/gradle/wrapper/gradle-wrapper.properties
    [[ -z $_pp_maven && -r $d/.mvn/wrapper/maven-wrapper.properties ]] &&
      _pp_maven=$d/.mvn/wrapper/maven-wrapper.properties
    if [[ -e $d/.git ]]; then
      _pp_git_root=$d
      break
    fi
    [[ $d == $HOME || $d == / ]] && break
    d=${d:h}
  done
}

# current-context straight from the kubeconfig file(s)
_pp_kube_context() {
  local f line
  _pp_kube_ctx=
  for f in ${(s.:.)${KUBECONFIG:-$HOME/.kube/config}}; do
    [[ -r $f ]] || continue
    line=${(M)${(f)"$(<$f)"}:#current-context:*}
    line=${${line#current-context:}//[\"\' ]/}
    if [[ -n $line ]]; then
      _pp_kube_ctx=$line
      return
    fi
  done
}

# $1 properties file, $2 artifact name: distributionUrl=.../<name>-<ver>-bin.zip
_pp_wrapper_version() {
  local line=${(M)${(f)"$(<$1)"}:#distributionUrl=*}
  if [[ $line =~ "$2-([0-9][^-/]*)-(bin|all)\.zip" ]]; then
    REPLY=$match[1]
  else
    REPLY=
  fi
}

# JDK version from the active java's release file (cached per java binary)
_pp_java_version() {
  local j=${commands[java]:A} rel line
  if [[ "$j|$JAVA_HOME" != $_pp_java_key ]]; then
    _pp_java_key="$j|$JAVA_HOME" _pp_java_ver=
    rel=${j:h:h}/release
    # a mise shim resolves to the mise binary, not a JDK: use JAVA_HOME then
    [[ -r $rel ]] || rel=${JAVA_HOME:+$JAVA_HOME/release}
    if [[ -n $rel && -r $rel ]]; then
      line=${(M)${(f)"$(<$rel)"}:#JAVA_VERSION=*}
      _pp_java_ver=${${line#JAVA_VERSION=}//\"/}
    fi
  fi
  REPLY=$_pp_java_ver
}

# go version from GOROOT/VERSION (cached per go binary)
_pp_go_version() {
  local g=${commands[go]:A} f line
  if [[ $g != $_pp_go_key ]]; then
    _pp_go_key=$g _pp_go_ver=
    for f in ${g:h:h}/VERSION ${GOROOT:+$GOROOT/VERSION}; do
      if [[ -r $f ]]; then
        line=${${(f)"$(<$f)"}[1]}
        _pp_go_ver=${line#go}
        break
      fi
    done
  fi
  REPLY=$_pp_go_ver
}

# $1 export name, $2 value; empty value unsets so starship hides the segment
_pp_export() {
  if [[ -n $2 ]]; then
    export $1=$2
  else
    unset $1
  fi
}

# $PWD with ~, shortened only past $1 columns: first fish-style (parents to
# their first letter, the last dir stays whole), then dropping leading dirs
_pp_pwd() {
  local -i budget=$1
  local p=${(D)PWD} lock=
  [[ -w $PWD ]] || lock=$' \uf023'
  if (( ${#p} + ${#lock} > budget )); then
    local -a parts=("${(@s:/:)p}")
    local -i i
    for (( i = 2; i < $#parts; i++ )); do
      (( ${#${(j:/:)parts}} + ${#lock} <= budget )) && break
      [[ $parts[i] == .* ]] && parts[i]=${parts[i][1,2]} || parts[i]=${parts[i][1]}
    done
    p=${(j:/:)parts}
    while (( ${#p} + ${#lock} > budget && $#parts > 1 )); do
      parts=("${(@)parts[2,-1]}")
      p="…/${(j:/:)parts}"
    done
  fi
  REPLY=$p$lock
}

# git branch name length without running git
_pp_branch_len() {
  local head
  if [[ -f $_pp_git_root/.git/HEAD ]]; then
    head=$(<$_pp_git_root/.git/HEAD)
    [[ $head == ref:* ]] && REPLY=${#${head#ref: refs/heads/}} || REPLY=9
  else
    REPLY=20
  fi
}

_pp_precmd() {
  local -i last_status=${STARSHIP_CMD_STATUS:-$?}  # starship's precmd runs first
  _pp_scan
  _pp_kube_context
  [[ -n $_pp_kube_ctx && $_pp_kube_ctx == ${~STARSHIP_KUBE_PROD_PATTERN} ]] && _pp_prod=1 || _pp_prod=
  _pp_kube_base=${_pp_prod:-$_pp_kube_project}
  _pp_export STARSHIP_KUBE $_pp_kube_base

  # everything else on the first prompt line, so the path knows its budget
  local -i reserve=29   # frame, caps, os icon, separators, time, some fill
  if [[ -n $_pp_jvm ]]; then
    _pp_java_version; _pp_export STARSHIP_JAVA $REPLY; (( reserve += ${#REPLY} + 5 ))
  else
    unset STARSHIP_JAVA
  fi
  if [[ -n $_pp_jvm && -n $_pp_gradle ]]; then
    _pp_wrapper_version $_pp_gradle gradle; _pp_export STARSHIP_GRADLE $REPLY; (( reserve += ${#REPLY} + 5 ))
  else
    unset STARSHIP_GRADLE
  fi
  if [[ -n $_pp_jvm && -n $_pp_maven ]]; then
    _pp_wrapper_version $_pp_maven apache-maven; _pp_export STARSHIP_MAVEN $REPLY; (( reserve += ${#REPLY} + 5 ))
  else
    unset STARSHIP_MAVEN
  fi
  if [[ -n $_pp_go ]]; then
    _pp_go_version; _pp_export STARSHIP_GO $REPLY; (( reserve += ${#REPLY} + 5 ))
  else
    unset STARSHIP_GO
  fi
  [[ -n $_pp_kube_base ]] && (( reserve += ${#_pp_kube_ctx} + 18 ))  # + namespace, PROD tag
  if [[ -n $_pp_git_root ]]; then
    _pp_branch_len; (( reserve += REPLY + 10 ))                       # + icon, git status
  fi
  (( last_status )) && (( reserve += 7 ))                             # exit status segment
  _pp_pwd $(( COLUMNS - reserve > 10 ? COLUMNS - reserve : 10 ))
  export STARSHIP_PWD=$REPLY
}

_pp_redraw() {
  local want=$_pp_kube_base
  local -a words=(${(z)BUFFER})
  (( ${STARSHIP_KUBE_COMMANDS[(Ie)${words[1]}]} )) && want=1
  # re-render only on a change, so normal typing never re-runs starship
  [[ $want == ${STARSHIP_KUBE:+1} ]] && return 0
  _pp_export STARSHIP_KUBE $want
  zle reset-prompt
  return 0
}

autoload -Uz add-zsh-hook add-zle-hook-widget
add-zsh-hook precmd _pp_precmd
add-zle-hook-widget line-pre-redraw _pp_redraw
