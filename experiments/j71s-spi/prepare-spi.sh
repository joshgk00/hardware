#!/usr/bin/env bash
# Prepare only the legacy SPI driver in a disposable, pinned kernel checkout.
set -euo pipefail
if (( $# != 2 )); then
  echo 'Usage: bash prepare-spi.sh KERNEL_CHECKOUT IPAD_NIXOS_CHECKOUT' >&2
  exit 2
fi
kernel=$(realpath "$1")
reference=$(realpath "$2")
[[ $(git -C "$kernel" rev-parse HEAD) == 6831bc701a6ce059e71e5aaa9488c9195bea6927 ]] || {
  echo 'Unexpected kernel revision' >&2; exit 1;
}
[[ $(git -C "$reference" rev-parse HEAD) == b94d42f78e04c5465e290340a5b6879bbc5956b6 ]] || {
  echo 'Unexpected reference revision' >&2; exit 1;
}
(cd "$kernel" && sha256sum -c - <<'EOF'
3f0c3791ec557f420b3264b4f2169bbc994b0f6109601c95c2b127d619974f76  drivers/spi/spi-apple.c
EOF
)
(cd "$reference" && sha256sum -c - <<'EOF'
cf4d17de1c0b52fd0a375319cfbee3da8b5f06980af798c640ebb6fc3adfa876  kernel/patches/0007-spi-apple-add-s5l8960x-support.patch
681443f899806de54e8c6a3ae9b0257adfe0e8a4ed1f174834ae364806382db1  kernel/patches/0096-spi-apple-s5l-word-delay.patch
2436deeeb29d641b2b1e8db622872d9b74e892e2c2505429d35d09226682aecd  kernel/patches/0098-spi-apple-s5l-do-not-end-large-transfers-after-one-fifo.patch
EOF
)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/drivers/spi"
cp "$kernel/drivers/spi/spi-apple.c" "$scratch/drivers/spi/spi-apple.c"
for name in 0007-spi-apple-add-s5l8960x-support.patch 0096-spi-apple-s5l-word-delay.patch 0098-spi-apple-s5l-do-not-end-large-transfers-after-one-fifo.patch; do
  patch --batch --forward -p1 -d "$scratch" < "$reference/kernel/patches/$name"
done
(cd "$scratch" && sha256sum -c - <<'EOF'
0c98d44614e8b31056acb5beaca511958d3e507b22f68f00eaec586f648d44b9  drivers/spi/spi-apple.c
EOF
)
cp "$scratch/drivers/spi/spi-apple.c" "$kernel/drivers/spi/spi-apple.c"
echo 'Prepared SPI source only; no device tree or hardware has been changed.'
