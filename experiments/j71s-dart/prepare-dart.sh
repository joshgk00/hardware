#!/usr/bin/env bash
# Apply the field fix and maintainer-guided separate lock to a disposable checkout.
set -euo pipefail
if (( $# != 1 )); then
  echo 'Usage: bash prepare-dart.sh KERNEL_CHECKOUT' >&2
  exit 2
fi
kernel=$(realpath "$1")
here=$(cd "$(dirname "$0")" && pwd)
[[ $(git -C "$kernel" rev-parse HEAD) == 6831bc701a6ce059e71e5aaa9488c9195bea6927 ]] || {
  echo 'Unexpected kernel revision' >&2; exit 1;
}
(cd "$kernel" && sha256sum -c - <<'EOF'
158d1a7b4ce870d106f8a0295066c523a8b8ccd196b13e5f6bc8922484c75bdf  drivers/iommu/apple-dart.c
EOF
)
(cd "$here" && sha256sum -c - <<'EOF'
608f0bb8d39bc55b82de626770694de51a0dfdb2fd5f620830ddf5b0180b4374  fix-s5l-tcr-stream.patch
4f1498db0ebc7bde3e5c545a9d11073d37782499d9286114bea8c9aa2066b7eb  j71s-dart-distinct-tcr-lock.patch
EOF
)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
mkdir -p "$scratch/drivers/iommu"
cp "$kernel/drivers/iommu/apple-dart.c" "$scratch/drivers/iommu/apple-dart.c"
patch --batch --forward -p1 -d "$scratch" < "$here/fix-s5l-tcr-stream.patch"
(cd "$scratch" && sha256sum -c - <<'EOF'
68740d3c74ba9bda8acc0582df1a6b547e1f894057aaa2afecab85a41e03e7d1  drivers/iommu/apple-dart.c
EOF
)
python3 "$here/test-tcr.py" "$scratch"
patch --batch --forward -p1 -d "$scratch" < "$here/j71s-dart-distinct-tcr-lock.patch"
(cd "$scratch" && sha256sum -c - <<'EOF'
5a4feff26b66f6393ab2796e4fd05e8f954480406e2913c17b801aadc73f6d48  drivers/iommu/apple-dart.c
EOF
)
python3 "$here/test-tcr-distinct-lock.py" "$scratch"
cp "$scratch/drivers/iommu/apple-dart.c" "$kernel/drivers/iommu/apple-dart.c"
echo 'Prepared DART source only; no device tree or hardware was changed.'
