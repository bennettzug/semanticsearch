#!/usr/bin/env bash
set -euo pipefail

# Automated deployment helper for Ubuntu 22.04+ and Oracle Linux 8.10.
# Run as root from the repository root.
#
# Required environment variables:
#   DATABASE_URL   Postgres connection string for the app.
#
# Optional environment variables:
#   APP_USER=semanticsearch
#   APP_GROUP=www-data
#   APP_DOMAIN=courses.example.com
#   APP_HOME=<repo root>
#   COURSE_SCHOOLS="ASU UIUC"
#   PORT=8000
#   DATABASE_MIN_CONNECTIONS=1
#   DATABASE_MAX_CONNECTIONS=10

# Detect OS family (Debian/Ubuntu vs RHEL/Oracle)
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
    fi

    if command -v apt-get >/dev/null; then
        OS_FAMILY="debian"
    elif command -v dnf >/dev/null; then
        OS_FAMILY="redhat"
    else
        echo "[bootstrap] Unsupported platform: require apt-get or dnf." >&2
        exit 1
    fi
}

if [[ $EUID -ne 0 ]]; then
    echo "[bootstrap] Please run as root (sudo)." >&2
    exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "[bootstrap] DATABASE_URL must be set before running this script." >&2
    exit 1
fi

APP_USER=${APP_USER:-semanticsearch}
APP_GROUP=${APP_GROUP:-www-data}
APP_DOMAIN=${APP_DOMAIN:-courses.example.com}
PORT=${PORT:-8000}
DATABASE_MIN_CONNECTIONS=${DATABASE_MIN_CONNECTIONS:-1}
DATABASE_MAX_CONNECTIONS=${DATABASE_MAX_CONNECTIONS:-10}
COURSE_SCHOOLS=${COURSE_SCHOOLS:-ASU UIUC}
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
APP_HOME=${APP_HOME:-$REPO_ROOT}
ENV_FILE="$APP_HOME/.env"
SYSTEMD_UNIT=/etc/systemd/system/semanticsearch.service
detect_os

if [[ "$OS_FAMILY" == "debian" ]]; then
    NGINX_CONF=/etc/nginx/sites-available/semanticsearch.conf
    NGINX_ENABLED=/etc/nginx/sites-enabled/semanticsearch.conf
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
else
    NGINX_CONF=/etc/nginx/conf.d/semanticsearch.conf
    NGINX_ENABLED=$NGINX_CONF
fi
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

install_packages() {
    if [[ "$OS_FAMILY" == "debian" ]]; then
        log "Updating apt repositories and installing base packages..."
        apt-get update -y
        apt-get install -y --no-install-recommends \
            build-essential \
            git \
            python3.12 \
            python3.12-venv \
            python3-pip \
            python3-dev \
            postgresql-client \
            libpq-dev \
            nginx \
            certbot \
            python3-certbot-nginx \
            curl \
            pkg-config \
            ca-certificates
    else
        log "Installing base packages with dnf..."
        if [[ -f /etc/oracle-release ]]; then
            dnf install -y oracle-epel-release-el8 || true
        fi
        if ! rpm -q python3.12 >/dev/null 2>&1; then
            if dnf module list python | grep -q "3\.12"; then
                dnf -y module enable python:3.12 || true
            fi
        fi
        dnf install -y \
            gcc \
            gcc-c++ \
            make \
            git \
            python3.12 \
            python3.12-venv \
            python3.12-devel \
            python3-pip \
            postgresql \
            postgresql-devel \
            nginx \
            certbot \
            python3-certbot-nginx \
            curl \
            pkgconf-pkg-config \
            ca-certificates
        if ! command -v psql >/dev/null && command -v dnf >/dev/null; then
            dnf install -y postgresql-client || true
        fi
    fi
}

install_node() {
    if ! command -v node >/dev/null || [[ $(node -v | cut -c2- | cut -d. -f1) -lt 18 ]]; then
        log "Installing Node.js 18 via NodeSource..."
        if [[ "$OS_FAMILY" == "debian" ]]; then
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y nodejs
        else
            curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
            dnf install -y nodejs
        fi
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

    log "Python 3.12 not found; installing via uv..."
    "$UV_BIN" python install 3.12
    PY_DIR=$("$UV_BIN" python find 3.12)
    if [[ -z "${PY_DIR:-}" ]]; then
        log "Failed to locate uv-managed Python 3.12 installation." >&2
        exit 1
    fi
    ln -sf "$PY_DIR/bin/python3.12" /usr/local/bin/python3.12
    ln -sf "$PY_DIR/bin/pip3.12" /usr/local/bin/pip3.12
    export PATH="$PY_DIR/bin:$PATH"
}

install_packages
install_node
install_uv
ensure_python

log "Ensuring application user ($APP_USER) exists..."
if ! id -u "$APP_USER" >/dev/null 2>&1; then
    adduser --system --group "$APP_USER"
fi

log "Setting repository ownership to $APP_USER:$APP_GROUP..."
chown -R "$APP_USER":"$APP_GROUP" "$APP_HOME"

export PATH="$PATH_UPDATE"

log "Installing Python dependencies via uv..."
run_as_app "$APP_USER" "$UV_BIN" sync --frozen --no-dev --project "$APP_HOME"

log "Installing Node dependencies and building frontend..."
run_as_app "$APP_USER" npm --prefix "$APP_HOME/client" ci
run_as_app "$APP_USER" npm --prefix "$APP_HOME/client" run build

if [[ -n "${COURSE_SCHOOLS:-}" ]]; then
    read -ra SCHOOL_ARRAY <<< "$COURSE_SCHOOLS"
    if [[ ${#SCHOOL_ARRAY[@]} -gt 0 ]]; then
        log "Bootstrapping course data for: ${COURSE_SCHOOLS}"
        run_as_app "$APP_USER" env DATABASE_URL="$DATABASE_URL" \
            "$UV_BIN" run --project "$APP_HOME" python make_dbs.py "${SCHOOL_ARRAY[@]}" --yes
    fi
fi

log "Writing environment file to $ENV_FILE ..."
cat > "$ENV_FILE" <<ENV
DATABASE_URL=$DATABASE_URL
DATABASE_MIN_CONNECTIONS=$DATABASE_MIN_CONNECTIONS
DATABASE_MAX_CONNECTIONS=$DATABASE_MAX_CONNECTIONS
PORT=$PORT
ENV
chown "$APP_USER":"$APP_GROUP" "$ENV_FILE"
chmod 600 "$ENV_FILE"

log "Creating systemd service at $SYSTEMD_UNIT ..."
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

log "Configuring nginx at $NGINX_CONF ..."
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
if [[ "$NGINX_ENABLED" != "$NGINX_CONF" ]]; then
    ln -sf "$NGINX_CONF" "$NGINX_ENABLED"
fi

log "Reloading systemd and nginx..."
systemctl daemon-reload
systemctl enable --now semanticsearch.service
nginx -t
systemctl reload nginx

cat <<SUMMARY

[bootstrap] Completed.
Next steps:
  1. Review logs: journalctl -u semanticsearch.service -f
  2. Obtain TLS certificates: sudo certbot --nginx -d $APP_DOMAIN
  3. Verify the site at: http://$APP_DOMAIN/

SUMMARY
