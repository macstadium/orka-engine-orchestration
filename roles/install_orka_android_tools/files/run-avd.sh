#!/bin/bash

set -eu -o pipefail

CONSOLE_PORT="5554"
VMNET_BRIDGE_IP="192.168.64.1"
VERBOSE=0

RELAY_PORT=""

declare -a ARGS

usage () {
  echo "Usage: $0 AVD_NAME -b <VMNET_BRIDGE_IP> -p <CONSOLE_PORT> -r <RELAY_PORT>"
  exit 1
}

while [[ $# -gt 0 ]]; do
  unset OPTIND
  unset OPTARG
  while getopts "b:p:r:hv" opt; do
    case $opt in
      b) VMNET_BRIDGE_IP="$OPTARG" ;;
      p) CONSOLE_PORT="$OPTARG" ;;
      r) RELAY_PORT="$OPTARG" ;;
      h) usage ;;
      v) VERBOSE=1 ;;
    esac
  done
  shift $(($OPTIND - 1))

  if [[ -n "${1:-}" ]]; then
    ARGS+=($1)
    shift
  fi
done

if [[ ${#ARGS[@]} -ne 1 ]]; then
  echo "Error: AVD name is required!" >&2
  usage
fi

if [[ "$VERBOSE" -eq 1 ]]; then
  set -x
fi

AVD_NAME="${ARGS[0]}"
ADBD_PORT="$((CONSOLE_PORT + 1))"
DEFAULT_RELAY_PORT="$((ADBD_PORT + 10000))"

RELAY_PORT="${RELAY_PORT:-$DEFAULT_RELAY_PORT}"

EMULATOR_PID=""
RELAY_PID=""

cleanup () {
  echo "shutting down ..."
  kill $EMULATOR_PID $RELAY_PID 2>/dev/null || true
  wait $EMULATOR_PID $RELAY_PID 2>/dev/null || true
}

trap cleanup EXIT

emulator -avd "$AVD_NAME" -no-snapshot -no-window -ports ${CONSOLE_PORT},${ADBD_PORT} 2>&1 &
EMULATOR_PID=$!

until nc -z 127.0.0.1 $ADBD_PORT 2>/dev/null; do
  if ! kill -0 $EMULATOR_PID 2>/dev/null; then
    echo "emulator exited during boot"
    exit 1
  fi
  sleep 2
done

socat TCP-LISTEN:${RELAY_PORT},fork,bind=${VMNET_BRIDGE_IP} TCP:127.0.0.1:${ADBD_PORT} 2>&1 &
RELAY_PID=$!

while kill -0 $EMULATOR_PID 2>/dev/null && kill -0 $RELAY_PID 2>/dev/null; do
  sleep 5
done
