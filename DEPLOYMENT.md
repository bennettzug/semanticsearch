# Deployment Guide

This guide covers two production-ready paths for shipping the semantic course
search application: (1) a fully self-managed VPS and (2) a managed deployment on
Railway. Both approaches assume you will bootstrap the PostgreSQL database using
the provided scripts (instructions included below).

> **Tip:** Keep secrets out of source control. Prefer the `DATABASE_URL`
environment variable whenever possible.

---

## Quick Bootstrap (Ubuntu 22.04+ or Oracle Linux 8.10 ARM)

After cloning the repository on a fresh server you can let the helper script
handle the heavy lifting (system packages, `uv sync`, frontend build, database
bootstrap, systemd/nginx wiring):

```bash
sudo -E DATABASE_URL="postgresql://user:pass@db-host:5432/vector_search" \
  APP_DOMAIN="courses.example.com" \
  COURSE_SCHOOLS="ASU UIUC" \
  bash scripts/bootstrap.sh
```

The script detects whether the host uses `apt` (Ubuntu/Debian) or `dnf`
(Oracle/RHEL family). On Oracle Linux it attempts to enable the Python 3.12
module and install the `oracle-epel-release` repository when available. If the
Python 3.12 packages are still missing, enable the appropriate AppStream/EPEL
repository manually before re-running the script.

The remainder of this guide walks through the manual process should you prefer
to configure each step by hand.

## Option A – Self-Managed VPS (Ubuntu 22.04+)

### 1. Provision & Secure the Server
- Create an Ubuntu 22.04 LTS VPS (2 vCPU / 4 GB RAM minimum; more if generating
  embeddings on CPU).
- Point your domain’s DNS `A` record to the server IP.
- SSH in as `root`, create a user, harden SSH, and enable the firewall:
  ```bash
  adduser deployer
  usermod -aG sudo deployer
  ufw allow OpenSSH
  ufw enable
  ```

### 2. Install System Packages & uv
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git python3.12 python3.12-venv python3-pip \
    python3-dev postgresql-client libpq-dev nginx certbot python3-certbot-nginx \
    curl pkg-config

# Install uv (places the binary in ~/.local/bin by default)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```
Add the `PATH` export to your shell profile (`~/.profile`) so the systemd unit
can find uv-managed virtualenv binaries.

#### Oracle Linux / RHEL Notes
- Install the analogous packages with `dnf` (Oracle Linux shown; adjust for
  RHEL as needed):
  ```bash
  sudo dnf install -y oracle-epel-release-el8      # Oracle Linux only, if available
  sudo dnf module enable -y python:3.12            # Enable AppStream module when required
  sudo dnf install -y gcc gcc-c++ make git python3.12 python3.12-venv \
      python3.12-devel python3-pip postgresql postgresql-devel nginx \
      certbot python3-certbot-nginx curl pkgconf-pkg-config ca-certificates
  ```
- Install uv and Node.js 18:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
  sudo dnf install -y nodejs
  ```
- If Python 3.12 packages are still unavailable, configure the appropriate
  repositories (AppStream/EPEL/CodeReady) or build Python 3.12 from source
  before continuing.

### 3. Prepare PostgreSQL With pgvector
- Use a managed PostgreSQL instance or install Postgres locally.
- Enable the `pgvector` extension once inside the target database:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- Create a dedicated database user with least-privilege access to the course and
  embeddings tables.

### 4. Clone the Repository
```bash
sudo mkdir -p /var/www/semanticsearch
sudo chown deployer:deployer /var/www/semanticsearch
cd /var/www/semanticsearch
git clone https://github.com/<your-org>/semanticsearch.git .
```

### 5. Configure Environment Variables
Create `/var/www/semanticsearch/.env` with contents similar to:
```
DATABASE_URL=postgresql://app_user:supersecret@db-host:5432/vector_search
DATABASE_MIN_CONNECTIONS=1
DATABASE_MAX_CONNECTIONS=10
PORT=8000
```
Restrict permissions:
```bash
chmod 600 .env
```

### 6. Build the Front-End Assets
```bash
cd client
npm ci
npm run build
cd ..
```
This populates `client/dist/`, which Flask serves in production.

### 7. Install Python Dependencies With uv
```bash
uv sync --frozen --no-dev
```
The command creates `.venv/` populated according to `uv.lock`.

### 8. Bootstrap Course Data & Embeddings
Run once per school before exposing the service (the scripts target the shared
`courses`/`course_embeddings` tables and only replace rows for the specified
schools):
```bash
uv run python make_dbs.py ASU UIUC UNC --yes
```
The script reads from `coursedata/` by default. Use `--keep-courses`,
`--keep-embeddings`, or `--limit` if you need partial rebuilds. Subsequent
updates can target individual schools:
```bash
uv run python create_courses_table.py --school ASU --yes
uv run python courses_to_embeddings.py --school ASU --yes
```
The first embedding run downloads the `thenlper/gte-base` model from Hugging
Face—ensure the server has outbound network access.

### 9. Create a Gunicorn Service
Create `/etc/systemd/system/semanticsearch.service`:
```
[Unit]
Description=Semantic Course Search API
After=network.target

[Service]
User=deployer
Group=www-data
WorkingDirectory=/var/www/semanticsearch
EnvironmentFile=/var/www/semanticsearch/.env
ExecStart=/var/www/semanticsearch/.venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    app:app
Restart=on-failure
Environment=PATH=/var/www/semanticsearch/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
```
Reload systemd and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now semanticsearch
sudo systemctl status semanticsearch
```

### 10. Configure Nginx as a Reverse Proxy
Create `/etc/nginx/sites-available/semanticsearch`:
```
server {
    listen 80;
    server_name courses.example.com;

    location /static/ {
        alias /var/www/semanticsearch/client/dist/;
        try_files $uri $uri/ =404;
        add_header Cache-Control "public, max-age=31536000";
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
    }
}
```
Enable the site and test the config:
```bash
sudo ln -s /etc/nginx/sites-available/semanticsearch /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 11. Secure With HTTPS
Use Let’s Encrypt to obtain a certificate:
```bash
sudo certbot --nginx -d courses.example.com
```
Certificates renew automatically; confirm with `sudo systemctl status certbot.timer`.

### 12. Operational Tips
- Deploy updates via `git pull`, `npm run build`, `uv sync --frozen`, data scripts
  as needed, and `sudo systemctl restart semanticsearch`.
- Tail logs with `journalctl -fu semanticsearch`.
- Monitor resource usage (Torch can be memory intensive when generating
  embeddings on the fly).

---

## Option B – Railway (Managed PaaS)

Railway supports both the web service and a managed PostgreSQL add-on. The
platform uses Nixpacks to build the app automatically.

### 1. Create Project & Database
1. Sign in to [Railway](https://railway.app/) and create a new project.
2. Add the **PostgreSQL** plugin. After provisioning, open the database and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Copy the generated `DATABASE_URL` from the plugin settings.

### 2. Deploy the Web Service
1. From the project dashboard choose **New > Repo** and connect this GitHub
   repository.
2. Set the following variables under the service → **Variables** tab:
   - `DATABASE_URL` – paste the value from the database plugin
   - `DATABASE_MIN_CONNECTIONS=1`
   - `DATABASE_MAX_CONNECTIONS=5`
3. Under **Settings → Nixpacks → Install Command**, install uv and build assets:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ~/.local/bin/uv sync --frozen --no-dev
   cd client && npm ci && npm run build && cd ..
   ```
4. Under **Start Command**, set:
   ```bash
   ~/.local/bin/uv run gunicorn --bind 0.0.0.0:$PORT app:app
   ```
5. Trigger a deployment. Railway builds the Python environment, compiles the
   Svelte assets, and starts Gunicorn via uv.

### 3. Bootstrap the Database
- Open a Railway shell for the web service and run:
  ```bash
  ~/.local/bin/uv run python make_dbs.py ASU UIUC --yes
  ```
  Alternatively, run individual scripts (`create_courses_table.py`,
  `courses_to_embeddings.py`) if you need fine-grained control. Each command
  uses the provisioned `DATABASE_URL` automatically.

### 4. Configure Domains & SSL
- In the service settings, add a custom domain or use the default `*.railway.app`
  domain.
- Railway manages TLS certificates automatically.

### 5. Database Maintenance
- Use the Railway SQL console or `railway connect` CLI to run migrations or
  insertions (e.g., rebuilding embeddings tables).
- Scale the Postgres tier as embeddings volume or query load grows.
- Re-run the data scripts via Railway shell whenever source CSVs change.

### 6. Troubleshooting
- Inspect build logs in the **Deployments** tab if builds fail (common culprits:
  insufficient memory during Torch install or missing pgvector extension).
- Use **Metrics** to watch CPU/RAM. Increase service size if embedding
  generation causes slow queries.
- Set `VITE_API_BASE_URL=https://<your-domain>` only if you decide to host the
  Svelte front-end separately; otherwise leave it blank so Flask serves the
  bundled assets produced during the build.

---

## Shared Production Considerations
- Cache control: the Flask static handler serves `client/dist`; configure CDN or
  proxy headers (see Nginx example) for aggressive caching of hashed assets.
- Background jobs: heavy embedding generation (e.g., rebuilding tables) should
  run out-of-band to avoid blocking the web dyno—consider a separate worker or
  manual invocation via SSH/CLI.
- Monitoring: wire up health checks to `/healthz` and consider uptime monitors
  that verify both the API and query latency.
- Secrets rotation: rotate database credentials regularly; both deployment
  approaches expect a single `DATABASE_URL` secret for the app runtime.
