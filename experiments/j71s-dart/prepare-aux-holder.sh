#!/usr/bin/env bash
# Add the isolated AUX holder to a disposable, previously prepared test tree.
set -euo pipefail
if (( $# != 1 )); then
  echo 'Usage: bash prepare-aux-holder.sh KERNEL_CHECKOUT' >&2
  exit 2
fi
kernel=$(realpath "$1")
here=$(cd "$(dirname "$0")" && pwd)
[[ $(git -C "$kernel" rev-parse HEAD) == 6831bc701a6ce059e71e5aaa9488c9195bea6927 ]] || { echo 'Unexpected kernel revision' >&2; exit 1; }
(cd "$kernel" && sha256sum -c - <<'CHECKSUMS'
1ba9d48cac20489784838e58172d10ef67324b0022861cc5bc44a393902357c1  drivers/iommu/Makefile
6c00598102ab6c9400af1ec955f5efa018788ddd9c98638b820bc89451fbb66c  drivers/iommu/j71s-dart-software-test.c
CHECKSUMS
)
(cd "$here" && sha256sum -c - <<'CHECKSUMS'
00b7ca9172b0d10d53fb0818543a72f41dc5e29c30186eadbbb663127791489e  aux-power-holder.c
CHECKSUMS
)
dest="$kernel/drivers/iommu/j71s-aux-hold-test.c"
[[ ! -e "$dest" && ! -L "$dest" ]] || { echo 'AUX holder already exists' >&2; exit 1; }
cp "$here/aux-power-holder.c" "$dest"
printf '\nobj-$(CONFIG_APPLE_DART) += j71s-aux-hold-test.o\n' >> "$kernel/drivers/iommu/Makefile"
(cd "$kernel" && sha256sum -c - <<'CHECKSUMS'
fe22a77b02554a18a63e2ef409e56cd5d52cdda7507832c1fd4f5d81166a76b9  drivers/iommu/Makefile
CHECKSUMS
)
echo 'Prepared AUX holder source; no device tree or hardware was changed.'
