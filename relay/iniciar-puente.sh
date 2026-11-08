#!/usr/bin/env bash
# Puente RTSP para Bandit. Corre en un equipo que SÍ llega a la cámara (por ejemplo Kali)
# y reenvía sus dos lentes a rtsp://bandit:<clave>@<ip-de-este-equipo>:8554/lente1 y /lente2.
# Nunca imprime el código de la cámara.
set -euo pipefail

VERSION="v1.12.2"
ARCHIVE="mediamtx_${VERSION}_linux_amd64.tar.gz"
SHA256="f0ec6e21c3cde41d02f186f58636f0ea8ee67c9d44dacf5b9391e85600f56e74"
DIR="${HOME}/bandit-puente"

mkdir -p "$DIR"
cd "$DIR"

if [[ ! -x ./mediamtx ]]; then
    echo "Descargando MediaMTX ${VERSION}..."
    curl -fsSL -o "$ARCHIVE" "https://github.com/bluenviron/mediamtx/releases/download/${VERSION}/${ARCHIVE}"
    echo "${SHA256}  ${ARCHIVE}" | sha256sum --check --quiet
    tar -xzf "$ARCHIVE" mediamtx
    rm -f "$ARCHIVE"
fi

if [[ -f mediamtx.yml ]]; then
    read -rp "Ya hay una configuración. ¿Crear una nueva? [s/N]: " again
    [[ "${again,,}" == "s" ]] || exec ./mediamtx mediamtx.yml
fi

read -rp "IP de la cámara [192.168.1.102]: " camera_ip
camera_ip="${camera_ip:-192.168.1.102}"
read -rsp "Código de la cámara (no se verá al escribir): " camera_code
echo
read -rp "Calidad: 1 = ligera 640x480 (recomendada), 0 = alta [1]: " subtype
subtype="${subtype:-1}"
[[ "$subtype" == "0" || "$subtype" == "1" ]] || { echo "La calidad debe ser 0 o 1."; exit 1; }

encoded_code="$(CODE="$camera_code" python3 -c 'import os, urllib.parse; print(urllib.parse.quote(os.environ["CODE"], safe=""))')"
bridge_password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
unset camera_code

source_url() {
    printf "rtsp://admin:%s@%s:554/cam/realmonitor?channel=%s&subtype=%s" "$encoded_code" "$camera_ip" "$1" "$subtype"
}

umask 077
cat > mediamtx.yml <<YAML
logLevel: info
rtsp: yes
rtspTransports: [tcp]
rtspAddress: :8554
rtmp: no
hls: no
webrtc: no
srt: no
api: no
metrics: no
pprof: no
playback: no

authMethod: internal
authInternalUsers:
  - user: bandit
    pass: '${bridge_password}'
    ips: []
    permissions:
      - action: read
        path: '~^lente[12]\$'

paths:
  lente1:
    source: '$(source_url 1)'
    rtspTransport: tcp
  lente2:
    source: '$(source_url 2)'
    rtspTransport: tcp
YAML
chmod 600 mediamtx.yml

if command -v ufw >/dev/null && sudo -n ufw status 2>/dev/null | grep -q "Status: active"; then
    sudo ufw allow 8554/tcp >/dev/null
fi

my_ip="$(ip -4 route get "$camera_ip" | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}')"
cat <<INFO

Puente listo. Registra en Bandit estas dos cámaras:
  Lente 1: rtsp://bandit:${bridge_password}@${my_ip}:8554/lente1
  Lente 2: rtsp://bandit:${bridge_password}@${my_ip}:8554/lente2
Guarda la clave del puente; está también en ${DIR}/mediamtx.yml.
Deja esta terminal abierta. Ctrl+C detiene el puente.

INFO
exec ./mediamtx mediamtx.yml
