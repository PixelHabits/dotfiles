# Purpose: Offer Hyprland start on local tty1, never over SSH.

# Only run in interactive shells
case $- in
  *i*) ;;
  *) return 0 ;;
esac

# Skip over SSH
if [[ -n "${SSH_CONNECTION-}" || -n "${SSH_TTY-}" || -n "${SSH_CLIENT-}" ]]; then
  return 0
fi

# Skip if inside tmux
if [[ -n "${TMUX-}" ]]; then
  return 0
fi

# Only offer on tty1 so tty2+ stays a rescue shell (recommended)
if [[ "${XDG_VTNR:-}" != "1" ]]; then
  return 0
fi

echo "Start Hyprland? (y/n)"
read -r start_hyprland
case "$start_hyprland" in
  y|Y|yes|YES)
    if command -v uwsm >/dev/null 2>&1; then
      exec uwsm start hyprland-uwsm.desktop
    else
      echo "uwsm not found; install it or start Hyprland manually."
    fi
    ;;
  n|N|no|NO|"")
    echo "ok, staying in TTY."
    ;;
  *)
    echo "please answer y or n."
    ;;
esac

