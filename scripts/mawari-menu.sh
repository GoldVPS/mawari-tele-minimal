#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/mawari-tele-minimal}"
CONTAINER="mawari_worker1"

# === Header (GoldVPS) ===
show_header() {
  clear
  echo -e "\e[38;5;220m"
  echo " ██████╗  ██████╗ ██╗     ██████╗ ██╗   ██╗██████╗ ███████╗"
  echo "██╔════╝ ██╔═══██╗██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝"
  echo "██║  ███╗██║   ██║██║     ██║  ██║██║   ██║██████╔╝███████╗"
  echo "██║   ██║██║   ██║██║     ██║  ██║╚██╗ ██╔╝██╔═══╝ ╚════██║"
  echo "╚██████╔╝╚██████╔╝███████╗██████╔╝ ╚████╔╝ ██║     ███████║"
  echo " ╚═════╝  ╚═════╝ ╚══════╝╚═════╝   ╚═══╝  ╚═╝     ╚══════╝"
  echo -e "\e[0m"
  echo -e "🚀 \e[1;33mNexus Node Installer\e[0m - Powered by \e[1;33mGoldVPS Team\e[0m 🚀"
  echo -e "🌐 \e[4;33mhttps://goldvps.net\e[0m - Best VPS with Low Price"
  echo
}

banner() { echo -e "\n==== $* ====\n"; }

choose() {
  echo "1) Install dependencies"
  echo "2) Edit config.yaml"
  echo "3) Edit telegram.yaml"
  echo "4) Run (notify-only)"
  echo "5) Show container logs (follow)"
  echo "6) Restart container"
  echo "7) Stop container"
  echo "8) Start container"
  echo "9) Backup burner cache"
  echo "10) Exit"
  echo -n "Choice: "
}

main() {
  show_header
  while true; do
    choose
    read -r c
    case "$c" in
      1) banner "Install dependencies"; bash "$REPO_DIR/scripts/install_deps.sh" ;;
      2) banner "Edit config.yaml";     ${EDITOR:-nano} "$REPO_DIR/config.yaml" ;;
      3) banner "Edit telegram.yaml";   ${EDITOR:-nano} "$REPO_DIR/telegram.yaml" ;;
      4) banner "Run (notify-only)";    bash "$REPO_DIR/scripts/run_notify.sh" ;;
      5) banner "Docker logs (Ctrl+C to exit)"; docker logs -f --tail=200 "$CONTAINER" || echo "Container not found." ;;
      6) banner "Docker restart"; docker restart "$CONTAINER" || echo "Container not found." ;;
      7) banner "Docker stop";    docker stop "$CONTAINER"    || echo "Container not found." ;;
      8) banner "Docker start";   docker start "$CONTAINER"   || echo "Container not found." ;;
      9)
        banner "Backup burner cache"
        SRC="$HOME/.mawari_automation/workers/worker1/cache/flohive-cache.json"
        DST="$HOME/flohive-cache.json.bak"
        if [ -f "$SRC" ]; then cp "$SRC" "$DST" && echo "Backed up to $DST"; else echo "Cache not found at $SRC"; fi
        ;;
      10) exit 0 ;;
      *) echo "invalid";;
    esac
  done
}

main
