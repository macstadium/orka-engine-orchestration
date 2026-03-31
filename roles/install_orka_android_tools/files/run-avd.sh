#!/bin/bash

set -eux -o pipefail

AVD_NAME="${1:-}"
VM_BRIDGE_IP="${2:-192.168.64.1}"
CONSOLE_PORT="${3:-5554}"
ADBD_PORT=$((CONSOLE_PORT + 1))
RELAY_PORT=$((ADBD_PORT + 10000))

if [[ -z "$AVD_NAME" ]]; then
  echo "AVD name is required!"
  exit 1
fi

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

socat TCP-LISTEN:${RELAY_PORT},fork,bind=${VM_BRIDGE_IP} TCP:127.0.0.1:${ADBD_PORT} 2>&1 &
RELAY_PID=$!

set +x

while kill -0 $EMULATOR_PID 2>/dev/null && kill -0 $RELAY_PID 2>/dev/null; do
  sleep 5
done
