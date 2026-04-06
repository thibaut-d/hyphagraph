# Remote Dev Access Guide

Use this guide to connect to the remote HyphaGraph development server with:

- VS Code Remote SSH
- Termius
- plain SSH

If you want the same SSH alias on multiple machines, see
`docs/development/SSH_CONFIG_SYNC.md`.

Replace these placeholders before use:

- `<DEV_DOMAIN>`: development domain, for example `dev.example.com`
- `<DEV_SERVER_IP>`: server public IPv4, for example `203.0.113.10`
- `<SSH_USER>`: remote Linux user, for example `ubuntu`
- `<PATH_TO_PRIVATE_KEY>`: local private key path

The repository is expected at:

```bash
/srv/hyphagraph
```

The remote development stack is expected to run with:

```bash
cd /srv/hyphagraph
make remote-dev-up
```

The dev site should then be reachable at:

```text
https://<DEV_DOMAIN>
```

---

## 1. VS Code Remote SSH

### 1.1 Local SSH config

Add a host entry to your local SSH config.

On Linux/macOS:

```sshconfig
Host hyphagraph-dev
  HostName <DEV_DOMAIN>
  User <SSH_USER>
  IdentityFile <PATH_TO_PRIVATE_KEY>
  IdentitiesOnly yes
  ServerAliveInterval 30
```

On Windows:

```sshconfig
Host hyphagraph-dev
  HostName <DEV_DOMAIN>
  User <SSH_USER>
  IdentityFile C:/Users/<YOUR_USER>/.ssh/id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
```

If DNS is not ready yet, use the server IP instead:

```sshconfig
Host hyphagraph-dev
  HostName <DEV_SERVER_IP>
  User <SSH_USER>
  IdentityFile <PATH_TO_PRIVATE_KEY>
  IdentitiesOnly yes
  ServerAliveInterval 30
```

### 1.2 Connect from VS Code

1. Install the `Remote - SSH` extension in VS Code.
2. Run `Remote-SSH: Connect to Host...`.
3. Choose `hyphagraph-dev`.
4. Open the folder `/srv/hyphagraph`.

Once connected, you can work directly on the VPS and benefit from the remote-dev
Docker stack:

- backend reload via FastAPI/uvicorn
- frontend reload via Vite
- public access via Caddy on `https://<DEV_DOMAIN>`

### 1.3 Useful commands

Run these from the VS Code integrated terminal on the remote host:

```bash
cd /srv/hyphagraph
make remote-dev-logs
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml ps
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml exec api pytest -q
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml exec web npx tsc --noEmit
```

---

## 2. Termius

Create a new host in Termius with:

- Address: `<DEV_DOMAIN>` or `<DEV_SERVER_IP>`
- Username: `<SSH_USER>`
- Authentication: `Key`
- Private key: import `<PATH_TO_PRIVATE_KEY>`
- Port: `22`

Recommended optional settings:

- Friendly name: `hyphagraph-dev`
- Keepalive: enabled

After connecting:

```bash
cd /srv/hyphagraph
make remote-dev-logs
```

If you want to edit files from Termius only, work directly in `/srv/hyphagraph`.

---

## 3. Plain SSH

### 3.1 One-off command

```bash
ssh -i <PATH_TO_PRIVATE_KEY> <SSH_USER>@<DEV_DOMAIN>
```

Or, before DNS propagation is complete:

```bash
ssh -i <PATH_TO_PRIVATE_KEY> <SSH_USER>@<DEV_SERVER_IP>
```

### 3.2 With a reusable SSH alias

Add this to `~/.ssh/config`:

```sshconfig
Host hyphagraph-dev
  HostName <DEV_DOMAIN>
  User <SSH_USER>
  IdentityFile <PATH_TO_PRIVATE_KEY>
  IdentitiesOnly yes
  ServerAliveInterval 30
```

Then connect with:

```bash
ssh hyphagraph-dev
```

### 3.3 Common remote commands

```bash
cd /srv/hyphagraph
git pull
make remote-dev-up
make remote-dev-logs
```

Check service status:

```bash
cd /srv/hyphagraph
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml ps
```

Stop the remote development stack:

```bash
cd /srv/hyphagraph
make remote-dev-down
```

---

## 4. Verification Checklist

Once connected and the stack is up:

```bash
cd /srv/hyphagraph
docker compose -p hyphagraph-dev -f docker-compose.remote-dev.yml ps
curl -I https://<DEV_DOMAIN>
curl -I https://<DEV_DOMAIN>/api/docs
```

Expected result:

- `caddy`, `web`, `api`, and `db` are running
- `https://<DEV_DOMAIN>` returns the frontend
- `https://<DEV_DOMAIN>/api/docs` returns the FastAPI docs

---

## 5. Notes

- If the domain is not propagated yet, SSH can use `<DEV_SERVER_IP>` while HTTPS may still fail until DNS is live.
- The remote-dev stack binds ports `80` and `443`, so it should not run in parallel with another stack using the same ports on the same machine.
- Keep secrets in the server `.env` file only. Do not commit them to the repository.
