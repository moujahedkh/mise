# mise bootstrap

One-shot script that sets up a new macOS machine with [mise](https://mise.jdx.dev):
it installs mise, fetches the decryption key from Bitwarden, and then adopts the
global mise config via `mise bootstrap --adopt`.

Inspired by Josh Long's
[`bootstrap.sh`](https://github.com/joshlong/mise/blob/main/bootstrap.sh).

## Usage

```bash
curl -fsSL https://raw.githubusercontent.com/moujahedkh/mise/main/bootstrap.sh | bash
```

or, from a checkout:

```bash
bash bootstrap.sh
```

> **Warning:** the script starts with `rm -rf ~/.config/mise/`, because
> `--adopt` refuses to clone into an existing directory that is not a git
> checkout. Back up anything in there you want to keep.

## What it does

1. **Installs mise** via `https://mise.run` and puts `~/.local/bin` plus the mise
   shims on `PATH`. It also writes a block to `~/.zshenv` (rewritten on every
   run) that puts `~/.local/bin` on `PATH` and sets `MISE_EXPERIMENTAL=1` and
   `MISE_AGE_SSH_IDENTITY_FILES`, so new shells can find `mise` and decrypt the
   `[env]` values.
2. **Breaks the chicken-and-egg problem.** The adopted `mise.toml` holds
   age-encrypted `[env]` values, and mise decrypts them when the config loads.
   Without the key, every mise command that reads the config fails. The script
   therefore runs Bitwarden through `mise x` under an empty
   `MISE_GLOBAL_CONFIG_FILE`, from a temp directory with no config.
3. **Fetches the SSH key** (used as the age identity) from Bitwarden into
   `~/.ssh/mise_private_key` with mode `600`, and checks it is a valid key.
4. **Runs the real bootstrap:**
   `mise bootstrap --adopt https://github.com/moujahedkh/mise.git --yes`. This
   clones the config into `~/.config/mise`, then applies packages, repos, tools and the
   `bootstrap` task.

The script can be run again: it handles an already logged-in or unlocked
Bitwarden vault.

## Configuration

`mise.toml` is the global config that `--adopt` clones into `~/.config/mise`.
It is modeled on Josh Long's
[`mise.toml`](https://github.com/joshlong/mise/blob/main/mise.toml) and holds:

- `[tools]`: tools managed by mise (Java, Node, jq, Bitwarden CLI).
- `[env]`: Homebrew's `shellenv` variables, `EDITOR`, and age-encrypted secrets.
- `[shell_alias]`: `eza` and `git` aliases.
- `[bootstrap.packages]` and `[bootstrap.brew.taps]`: Homebrew formulae, casks
  and taps.
- `[bootstrap.hooks.final]`: writes a zsh setup block (history, completion,
  fzf, fzf-tab, zoxide, starship, atuin, plugins) into `~/.zshrc`. It skips
  a `~/.zshrc` that already has the block or its own `starship init`.
- `[tasks.bootstrap]`: post-install sanity checks.

## Day-to-day use

After the bootstrap, `~/.config/mise` is a git checkout of this repo. Run these
commands from a shell where mise is set up.

### Check packages

Show which packages from the config are missing:

```bash
mise bootstrap packages status
```

### Reinstall removed packages

If you removed a Homebrew package by hand and want mise to bring it back:

```bash
mise bootstrap packages apply --yes
```

### Import packages added with Homebrew

If you installed packages with Homebrew directly and want to add them to the
global mise config:

```bash
mise bootstrap packages import --manager brew --global
```

This records each linked formula you installed yourself. Add `--all` to include
formulae installed only as dependencies. Without `--global`, mise writes to the
local config instead.

### Add an encrypted secret

```bash
mise set --global --age-encrypt --age-ssh-recipient ~/.ssh/mise_private_key.pub --prompt MY_KEY
```

This encrypts the value for the bootstrap SSH key and writes it to the global
config. Without `--global`, mise writes to the nearest config, creating
`mise.toml` in the current directory if none exists. `--prompt` asks for the
value after you press Enter, with masked input, so the raw secret never ends up
in your shell history.

### Share changes

Edits to `~/.config/mise` take effect on this machine right away. To get them
to other machines, commit and push them from `~/.config/mise`, then run
`git pull` there on each machine that is already set up.

## Requirements

- macOS with zsh, `curl` and `ssh-keygen`.
- `jq`. macOS 15+ ships `/usr/bin/jq`. On older releases the script installs it
  with Homebrew if `brew` is available, and otherwise runs it through `mise x`.
- A Bitwarden account with one SSH key item named
  `mise-bootstrap-private-ssh-key`. The script reads both the private and the
  public key from it.

## Known caveats

- The key is stored as `~/.ssh/mise_private_key`, a non-default name. mise's
  age decryption only looks at `~/.ssh/id_ed25519` and `~/.ssh/id_rsa` by
  default, so the script sets `MISE_AGE_SSH_IDENTITY_FILES` (for the bootstrap
  and in `~/.zshenv`). Without it, decryption fails with
  `No matching keys found`.
- `mise bootstrap` and age encryption are experimental; the script turns them
  on with `MISE_EXPERIMENTAL=1` (for the bootstrap and in `~/.zshenv`).
- A new machine gets only config changes that have been pushed, because
  `--adopt` clones from the remote.
