#!/usr/bin/env bash
# Apply the HDQ-related subset of the pinned Orchard J71b patch to a separate
# kernel checkout. This prepares an experiment; it does not access the iPad.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo 'Usage: bash prepare-j71s-hdq.sh KERNEL_CHECKOUT ORCHARD_J71B_PATCH' >&2
  exit 2
fi
kernel=$1
patch=$2
expected_commit=6831bc701a6ce059e71e5aaa9488c9195bea6927
expected_patch=0ffc48f47cd5845d9f700efd3cfd31421eaf4971cf7533d4dce347708f178e50
[[ $(git -C "$kernel" rev-parse HEAD) == "$expected_commit" ]] || { echo 'Wrong kernel revision' >&2; exit 1; }
[[ $(sha256sum "$patch" | cut -d' ' -f1) == "$expected_patch" ]] || { echo 'Unexpected Orchard patch' >&2; exit 1; }
patch=$(realpath "$patch")
includes=(
  --include=drivers/power/supply/bq27xxx_battery_hdq.c
  --include=drivers/tty/serdev/core.c
  --include=drivers/tty/serdev/serdev-ttyport.c
  --include=drivers/tty/serial/samsung_tty.c
  --include=drivers/w1/masters/w1-uart.c
  --include=include/linux/serdev.h
)
git -C "$kernel" apply --check "${includes[@]}" "$patch"
git -C "$kernel" apply "${includes[@]}" "$patch"
