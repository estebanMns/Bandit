#!/usr/bin/env bash
# Puente RTSP para Bandit. Corre en un equipo que SÍ llega a la cámara (por ejemplo Kali)
# y reenvía sus dos lentes a rtsp://bandit:<clave>@<ip-de-este-equipo>:8554/lente1 y /lente2.
# Nunca imprime el código de la cámara.
set -euo pipefail

# Compatible con Linux y macOS (incluido el bash 3.2 que trae macOS).
VERSION="v1.12.2"
DIR="${HOME}/bandit-puente"

case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) PLATFORM="darwin_arm64"; SHA256="df388cb70bcefe3822a63eb884576191120e63099d1fac4314d63d38b60eb238" ;;
    Darwin-x86_64) PLATFORM="darwin_amd64"; SHA256="572a766870f821196ec0977fda7993ac5a8c45ba34174b3a048f000e3fe1dd0b" ;;
    Linux-x86_64) PLATFORM="linux_amd64"; SHA256="f0ec6e21c3cde41d02f186f58636f0ea8ee67c9d44dacf5b9391e85600f56e74" ;;
    Linux-aarch64 | Linux-arm64) PLATFORM="linux_arm64"; SHA256="35803953e27a7b242efb1f25b4d48e3cc24999bcb43f6895383a85d6f8000651" ;;
    *) echo "Sistema no soportado: $(uname -s) $(uname -m)"; exit 1 ;;
esac
ARCHIVE="mediamtx_${VERSION}_${PLATFORM}.tar.gz"

checksum() {
    if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi
}

mkdir -p "$DIR"
cd "$DIR"

if [[ ! -x ./mediamtx ]]; then
    echo "Descargando MediaMTX ${VERSION}..."
    curl -fsSL --proto '=https' --tlsv1.2 -o "$ARCHIVE" "https://github.com/bluenviron/mediamtx/releases/download/${VERSION}/${ARCHIVE}"
    if [[ "$(checksum "$ARCHIVE" | awk '{print $1}')" != "$SHA256" ]]; then
        echo "La descarga no coincide con el checksum oficial."; rm -f "$ARCHIVE"; exit 1
    fi
    tar -xzf "$ARCHIVE" mediamtx
    rm -f "$ARCHIVE"
fi

if [[ -f mediamtx.yml ]]; then
    read -rp "Ya hay una configuración. ¿Crear una nueva? [s/N]: " again
    case "$again" in s | S) ;; *) exec ./mediamtx mediamtx.yml ;; esac
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

if [[ "$(uname -s)" == "Linux" ]]; then
    if command -v ufw >/dev/null && sudo -n ufw status 2>/dev/null | grep -q "Status: active"; then
        sudo ufw allow 8554/tcp >/dev/null
    fi
    my_ip="$(ip -4 route get "$camera_ip" | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}')"
else
    # macOS: la interfaz que usa para llegar a la cámara, y su IP.
    interface="$(route -n get "$camera_ip" 2>/dev/null | awk '/interface:/ {print $2}')"
    my_ip="$(ipconfig getifaddr "${interface:-en0}" 2>/dev/null || true)"
    echo "Si macOS pregunta si mediamtx puede aceptar conexiones, responde Permitir."
fi
cat <<INFO

Puente listo. Registra en Bandit estas dos cámaras:
  Lente 1: rtsp://bandit:${bridge_password}@${my_ip}:8554/lente1
  Lente 2: rtsp://bandit:${bridge_password}@${my_ip}:8554/lente2
Guarda la clave del puente; está también en ${DIR}/mediamtx.yml.
Deja esta terminal abierta. Ctrl+C detiene el puente.

INFO
exec ./mediamtx mediamtx.yml
