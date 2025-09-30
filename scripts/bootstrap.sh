#!/usr/bin/env bash
set -euo pipefail

# Automated deployment helper tailored for Oracle Linux 8 ARM (dnf-based).
# Run as root from the repository root.
#
# Required environment variable:
#   DATABASE_URL  Postgres connection string exposed to the app.
#
# Optional environment variables:
#   APP_USER=semanticsearch
#   APP_GROUP=nginx
#   APP_DOMAIN=example.com
#   APP_HOME=<repo root>
#   COURSE_SCHOOLS="ASU UIUC"
#   PORT=8000
#   DATABASE_MIN_CONNECTIONS=1
#   DATABASE_MAX_CONNECTIONS=10

if [[ "$EUID" -ne 0 ]]; then
    echo "[bootstrap] Please run as root (sudo)." >&2
    exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "[bootstrap] DATABASE_URL must be set before running this script." >&2
    exit 1
fi

APP_USER=${APP_USER:-semanticsearch}
APP_GROUP=${APP_GROUP:-nginx}
APP_DOMAIN=${APP_DOMAIN:-example.com}
PORT=${PORT:-8000}
DATABASE_MIN_CONNECTIONS=${DATABASE_MIN_CONNECTIONS:-1}
DATABASE_MAX_CONNECTIONS=${DATABASE_MAX_CONNECTIONS:-10}
COURSE_SCHOOLS=${COURSE_SCHOOLS:-}
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
APP_HOME=${APP_HOME:-$REPO_ROOT}
ENV_FILE="$APP_HOME/.env"
SYSTEMD_UNIT=/etc/systemd/system/semanticsearch.service
NGINX_CONF=/etc/nginx/conf.d/semanticsearch.conf
UV_BIN=/usr/local/bin/uv
PATH_UPDATE="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

log() {
    echo "[bootstrap] $*"
}

run_as_app() {
    local user=$1
    shift
    runuser -u "$user" -- env PATH="$PATH_UPDATE" HOME="$(getent passwd "$user" | cut -d: -f6)" "$@"
}

dnf_install() {
    log "Installing base packages via dnf..."
    dnf install -y oracle-epel-release-el8 || true
    dnf module enable -y python:3.12 || log "python:3.12 module not available; uv fallback will be used"
    dnf install -y \
        gcc \
        gcc-c++ \
        make \
        git \
        python3-pip \
        postgresql \
        nginx \
        certbot \
        python3-certbot-nginx \
        curl \
        pkgconf-pkg-config \
        ca-certificates
}

install_node() {
    if ! command -v node >/dev/null || [[ $(node -v | cut -c2- | cut -d. -f1) -lt 18 ]]; then
        log "Installing Node.js 18..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
        dnf install -y nodejs
    fi
}

install_uv() {
    if ! command -v uv >/dev/null; then
        log "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    if [[ ! -x "$UV_BIN" ]]; then
        if [[ -x "/root/.local/bin/uv" ]]; then
            ln -sf /root/.local/bin/uv "$UV_BIN"
        elif [[ -x "$HOME/.local/bin/uv" ]]; then
            ln -sf "$HOME/.local/bin/uv" "$UV_BIN"
        fi
    fi
    if [[ ! -x "$UV_BIN" ]]; then
        log "uv binary not found after installation attempt." >&2
        exit 1
    fi
}

ensure_python() {
    if command -v python3.12 >/dev/null 2>&1; then
        return
    fi

    log "python3.12 not detected; installing via uv..."
    "$UV_BIN" python install 3.12
    PY_PREFIX=$("$UV_BIN" python find 3.12 | tail -n1)
    if [[ -z "${PY_PREFIX:-}" ]]; then
        log "uv could not locate Python 3.12 installation." >&2
        exit 1
    fi
    ln -sf "$PY_PREFIX/bin/python3.12" /usr/local/bin/python3.12
    ln -sf "$PY_PREFIX/bin/pip3.12" /usr/local/bin/pip3.12
    export PATH="$PY_PREFIX/bin:$PATH"
}

create_accounts() {
    if ! getent group "$APP_GROUP" >/dev/null; then
        log "Creating system group $APP_GROUP"
        groupadd --system "$APP_GROUP"
    fi
    if ! id -u "$APP_USER" >/dev/null 2>&1; then
        log "Creating system user $APP_USER"
        useradd --system --gid "$APP_GROUP" --shell /usr/sbin/nologin --home "$APP_HOME" "$APP_USER"
    fi
    mkdir -p "$APP_HOME"
    chown -R "$APP_USER":"$APP_GROUP" "$APP_HOME"
}

bootstrap_python() {
    log "Running uv sync..."
    run_as_app "$APP_USER" "$UV_BIN" sync --frozen --no-dev --project "$APP_HOME"
}

build_frontend() {
    log "Installing node dependencies..."
    run_as_app "$APP_USER" npm --prefix "$APP_HOME/client" ci
    log "Building frontend artifacts..."
    run_as_app "$APP_USER" npm --prefix "$APP_HOME/client" run build
}

load_course_data() {
    if [[ -z "${COURSE_SCHOOLS// }" ]]; then
        return
    fi
    read -ra SCHOOL_ARRAY <<< "$COURSE_SCHOOLS"
    if [[ ${#SCHOOL_ARRAY[@]} -eq 0 ]]; then
        return
    fi
    log "Bootstrapping course data for: ${COURSE_SCHOOLS}"
    run_as_app "$APP_USER" env DATABASE_URL="$DATABASE_URL" \
        "$UV_BIN" run --project "$APP_HOME" python make_dbs.py "${SCHOOL_ARRAY[@]}" --yes
}

write_env_file() {
    log "Writing environment file to $ENV_FILE"
    cat > "$ENV_FILE" <<ENV
DATABASE_URL=$DATABASE_URL
DATABASE_MIN_CONNECTIONS=$DATABASE_MIN_CONNECTIONS
DATABASE_MAX_CONNECTIONS=$DATABASE_MAX_CONNECTIONS
PORT=$PORT
ENV
    chown "$APP_USER":"$APP_GROUP" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
}

write_systemd_service() {
    log "Creating systemd unit at $SYSTEMD_UNIT"
    cat > "$SYSTEMD_UNIT" <<SERVICE
[Unit]
Description=Semantic Course Search API
After=network.target

[Service]
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_HOME
EnvironmentFile=$ENV_FILE
Environment=PATH=$APP_HOME/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$APP_HOME/.venv/bin/gunicorn --bind 127.0.0.1:$PORT app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE
}

write_nginx_config() {
    log "Writing nginx config to $NGINX_CONF"
    cat > "$NGINX_CONF" <<NGINX
server {
    listen 80;
    server_name $APP_DOMAIN;

    location /static/ {
        alias $APP_HOME/client/dist/;
        try_files \$uri \$uri/ =404;
        add_header Cache-Control "public, max-age=31536000";
    }

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }
}
NGINX
}

finalize() {
    systemctl daemon-reload
    systemctl enable --now semanticsearch.service
    nginx -t
    systemctl reload nginx
    cat <<SUMMARY

[bootstrap] Completed.
Next steps:
  1. Check the service logs: sudo journalctl -u semanticsearch.service -f
  2. Issue TLS certificate (optional): sudo certbot --nginx -d $APP_DOMAIN
  3. Visit http://$APP_DOMAIN/ to confirm the deployment.

SUMMARY
}

# Execution flow
dnf_install
install_node
install_uv
ensure_python
create_accounts
bootstrap_python
build_frontend
load_course_data
write_env_file
write_systemd_service
write_nginx_config
finalize
