#!/usr/bin/env bash
# Add the explicitly experimental software-only driver to a disposable tree.
set -euo pipefail
if (( $# != 1 )); then
  echo 'Usage: bash prepare-software-consumer.sh KERNEL_CHECKOUT' >&2
  exit 2
fi
kernel=$(realpath "$1")
here=$(cd "$(dirname "$0")" && pwd)
[[ $(git -C "$kernel" rev-parse HEAD) == 6831bc701a6ce059e71e5aaa9488c9195bea6927 ]] || exit 1
dart_hash=$(sha256sum "$kernel/drivers/iommu/apple-dart.c")
dart_hash=${dart_hash%% *}
case "$dart_hash" in
  68740d3c74ba9bda8acc0582df1a6b547e1f894057aaa2afecab85a41e03e7d1|49e5bc33efa7761dc138565ff71fb78bdeef8ed5a0627adcabde1a26d9481255) ;;
  *) echo 'Expected the tested DART correction, optionally with reset markers' >&2; exit 1 ;;
esac
(cd "$kernel" && sha256sum -c - <<'EOF'
5771370b162d475f21cf0412ad33f43e91b912f68cb60e92423beff8e7c30398  drivers/iommu/Makefile
EOF
)
(cd "$here" && sha256sum -c - <<'EOF'
6c00598102ab6c9400af1ec955f5efa018788ddd9c98638b820bc89451fbb66c  software-consumer.c
EOF
)
dest="$kernel/drivers/iommu/j71s-dart-software-test.c"
[[ ! -e "$dest" && ! -L "$dest" ]] || { echo 'Consumer source already exists' >&2; exit 1; }
cp "$here/software-consumer.c" "$dest"
printf '\nobj-$(CONFIG_APPLE_DART) += j71s-dart-software-test.o\n' >> "$kernel/drivers/iommu/Makefile"
echo 'Prepared software-only consumer; no device tree or hardware was changed.'
