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

## Requirements

- macOS with zsh, `curl` and `ssh-keygen`.
- A Bitwarden account with two secure notes:
  - `mise-bootstrap-private-ssh-key`
  - `mise-bootstrap-public-ssh-key`

## Known caveats

- The key is stored as `~/.ssh/mise_private_key`, a non-default name. mise's
  age decryption only looks at `~/.ssh/id_ed25519` and `~/.ssh/id_rsa` by
  default, so the script sets `MISE_AGE_SSH_IDENTITY_FILES` (for the bootstrap
  and in `~/.zshenv`). Without it, decryption fails with
  `No matching keys found`.
- `mise bootstrap` and age encryption are experimental; the script turns them
  on with `MISE_EXPERIMENTAL=1` (for the bootstrap and in `~/.zshenv`).
- Config changes take effect only after they are pushed, because `--adopt`
  clones from the remote.
