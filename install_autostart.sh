#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3)"
SERVICE_NAME="info-bridge.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
ENV_DIR="${HOME}/.config"
ENV_FILE="${ENV_DIR}/info-bridge.env"

if [[ "${EUID}" -ne 0 ]]; then
    echo "sudo 권한이 필요합니다. 다시 실행하세요:"
    echo "sudo bash install_autostart.sh"
    exit 1
fi

SERVICE_USER="${SUDO_USER:-${USER}}"
SERVICE_HOME="$(getent passwd "${SERVICE_USER}" | cut -d: -f6)"
ENV_FILE="${SERVICE_HOME}/.config/info-bridge.env"

mkdir -p "$(dirname "${ENV_FILE}")"
touch "${ENV_FILE}"
chown "${SERVICE_USER}:${SERVICE_USER}" "${ENV_FILE}"

cat > "${SERVICE_PATH}" <<EOF
[Unit]
Description=Info Bridge LCD application
After=local-fs.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=-${ENV_FILE}
ExecStart=${PYTHON_BIN} ${PROJECT_DIR}/main.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "자동 실행 등록 완료"
echo "상태 확인: sudo systemctl status ${SERVICE_NAME}"
echo "로그 확인: sudo journalctl -u ${SERVICE_NAME} -f"
echo "API 키 파일: ${ENV_FILE}"