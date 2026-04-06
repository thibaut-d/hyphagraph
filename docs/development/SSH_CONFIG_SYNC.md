# Syncing `.ssh/config` Across Machines

VS Code Settings Sync does not sync your OpenSSH files.

That means this file is **not** propagated automatically:

```text
~/.ssh/config
```

To keep the same SSH aliases on multiple machines, sync the config file
yourself, but **never** sync your private key casually with it.

---

## What to sync

Sync:

- `~/.ssh/config`

Do not sync blindly:

- `~/.ssh/id_ed25519`
- `~/.ssh/id_rsa`
- any other private key file

If you already use a password manager, encrypted vault, or secure file sync
tool, use that for the config file and handle private keys separately.

---

## Recommended approach

Keep the same SSH alias on every machine, then copy only the config entry.

Example:

```sshconfig
Host hyphagraph-dev
  HostName <DEV_DOMAIN>
  User <SSH_USER>
  IdentityFile <PATH_TO_PRIVATE_KEY>
  IdentitiesOnly yes
  ServerAliveInterval 30
```

On each machine:

1. Create or update `~/.ssh/config`
2. Paste the same host block
3. Adjust `IdentityFile` to the local path on that machine
4. Save the file with permissions restricted to your user

The alias can stay the same everywhere:

```bash
ssh hyphagraph-dev
```

---

## Windows

Typical path:

```text
C:\Users\<YOUR_USER>\.ssh\config
```

Example:

```sshconfig
Host hyphagraph-dev
  HostName <DEV_DOMAIN>
  User <SSH_USER>
  IdentityFile C:/Users/<YOUR_USER>/.ssh/id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
```

---

## Linux and macOS

Typical path:

```text
~/.ssh/config
```

Example:

```sshconfig
Host hyphagraph-dev
  HostName <DEV_DOMAIN>
  User <SSH_USER>
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
```

---

## Safe ways to keep machines aligned

Choose one:

1. Copy the host block manually each time you add a new machine.
2. Store a sanitized copy of `.ssh/config` in a private notes or vault system.
3. Keep a private dotfiles repository that contains `config` but excludes private keys.

If you use a dotfiles repo, make sure it does **not** include:

- private keys
- `known_hosts`
- `authorized_keys` from unrelated machines unless intentional

---

## Suggested dotfiles layout

Example private repo structure:

```text
dotfiles/
  ssh/
    config
```

Then on each machine:

```bash
mkdir -p ~/.ssh
cp dotfiles/ssh/config ~/.ssh/config
chmod 600 ~/.ssh/config
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.ssh
Copy-Item .\dotfiles\ssh\config $HOME\.ssh\config
```

---

## Verification

After syncing the file:

```bash
ssh hyphagraph-dev
```

Or inspect the resolved SSH settings:

```bash
ssh -G hyphagraph-dev
```

In VS Code Remote SSH, the same host alias should then appear as:

```text
hyphagraph-dev
```

---

## Notes

- Keep the alias name stable across machines to avoid confusion in VS Code.
- If a machine stores the private key in a different path, only `IdentityFile` needs to change.
- If DNS is not propagated yet, you can temporarily use the server IP in `HostName`.
