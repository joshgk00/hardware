#!/usr/bin/env bash
# Build the exact experimentally tested J71s HDQ kernel in a separate directory.
set -euo pipefail
if (( $# < 2 || $# > 4 )); then
  echo 'Usage: bash build-kernel.sh PREPARED_KERNEL_CHECKOUT BUILD_OUTPUT [--resume] [--ambiguity]' >&2
  exit 2
fi
source_dir=$(realpath "$1")
output=$2
shift 2
resume=false
ambiguity=false
while (($#)); do
  case "$1" in
    --resume) "$resume" && { echo 'Duplicate --resume' >&2; exit 2; }; resume=true ;;
    --ambiguity) "$ambiguity" && { echo 'Duplicate --ambiguity' >&2; exit 2; }; ambiguity=true ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
w1_hash=9841dd764c32f814074d2f1edad76b89006e74940701099c2d0bc3bd42acea6f
"$ambiguity" && w1_hash=d3492b99e8b9a7213f8ab3b4ef23221ba951b00a944d275b8c618b82194d9f97
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
python=${ORCHARD_PYTHON:-python3}
[[ $(git -C "$source_dir" rev-parse HEAD) == 6831bc701a6ce059e71e5aaa9488c9195bea6927 ]] || {
  echo 'Unexpected kernel revision' >&2; exit 1;
}
git -C "$source_dir" diff --quiet HEAD -- . \
  ':(exclude)drivers/power/supply/bq27xxx_battery_hdq.c' \
  ':(exclude)drivers/tty/serdev/core.c' \
  ':(exclude)drivers/tty/serdev/serdev-ttyport.c' \
  ':(exclude)drivers/tty/serial/samsung_tty.c' \
  ':(exclude)drivers/w1/masters/w1-uart.c' \
  ':(exclude)include/linux/serdev.h' \
  ':(exclude)include/linux/serial_s3c.h' \
  ':(exclude)drivers/pinctrl/pinctrl-apple-gpio.c' || {
    echo 'Unexpected tracked kernel changes' >&2; exit 1;
  }
(cd "$source_dir" && sha256sum -c - <<EOF
b17c38886123f0a78560c782d3c2b1cf276f9e6466cafd1efc0f2d4d16a2b3fa  drivers/power/supply/bq27xxx_battery_hdq.c
f7a8fc40baa613f4a294ff4cc351fd67fa1f2cfbdcf2f5aaafd3096bd31ac65f  drivers/tty/serdev/core.c
76785766e4705349d80ef3fbecb5837a5826327ba3f6421a309a823bab952476  drivers/tty/serdev/serdev-ttyport.c
981982603c48ee7a8009db4d2c815f0f3610a205ad2136ce26f038c1768988c1  drivers/tty/serial/samsung_tty.c
$w1_hash  drivers/w1/masters/w1-uart.c
1567bc97d84fd4b54f5fbaccba75e50ac3afa48d9157da1760f6848980a60fab  include/linux/serdev.h
ea34a87ec3446319978cefa6bf439d024ac0da3007189a0001956733f9899729  include/linux/serial_s3c.h
2fde8a8ece3ab8de33b061a99dc0ad18d17a569cad59c0630c50f391d7711ac5  drivers/pinctrl/pinctrl-apple-gpio.c
EOF
)
if [[ -e "$output" ]] && ! "$resume"; then
  echo 'Output already exists; use a new directory or --resume' >&2; exit 1
fi
mkdir -p "$output"
output=$(realpath "$output")
if ! cmp -s "$repo/kernel/configs/j71s/config" "$output/.config"; then
  cp "$repo/kernel/configs/j71s/config" "$output/.config"
fi
"$python" -m orchard_hardware.buildenv build --file "$repo/kernel/Containerfile" \
  --image localhost/orchard-hardware-kernel-toolchain:bookworm --context "$repo/kernel"
"$python" -m orchard_hardware.buildenv run --bind "$source_dir:/src:ro" \
  --bind "$output:/out:rw" --bind "$repo/kernel/configs:/config:ro" \
  --image localhost/orchard-hardware-kernel-toolchain:bookworm -- bash -euc '
    export KBUILD_BUILD_USER=orchard KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=1
    export KBUILD_BUILD_TIMESTAMP="2026-10-22T00:00:00Z"
    make -C "$ORCHARD_SRC" O="$ORCHARD_OUT" LLVM=-19 ARCH=arm64 olddefconfig
    cmp "$ORCHARD_OUT/.config" "$ORCHARD_CONFIG/j71s/config"
    make -C "$ORCHARD_SRC" O="$ORCHARD_OUT" -j2 LLVM=-19 ARCH=arm64 \
      LOCALVERSION=-orchard-j71s Image.gz
  '
echo "Experimental kernel image: $output/arch/arm64/boot/Image.gz"
