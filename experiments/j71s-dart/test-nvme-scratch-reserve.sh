#!/bin/sh
set -eu
: "${DTC:=dtc}" "${FDTOVERLAY:=fdtoverlay}"
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/base.dts" <<'DTS'
/dts-v1/;
/ {
    #address-cells = <2>;
    #size-cells = <2>;
    reserved-memory {
        #address-cells = <2>;
        #size-cells = <2>;
        ranges;
        existing@800000000 { reg = <8 0 0 0x100000>; no-map; };
    };
};
DTS
"$DTC" -@ -I dts -O dtb -o "$tmp/base.dtb" "$tmp/base.dts"
"$DTC" -@ -I dts -O dtb -o "$tmp/overlay.dtbo" "$here/j71s-nvme-scratch-reserve.dtso"
"$FDTOVERLAY" -i "$tmp/base.dtb" -o "$tmp/result.dtb" "$tmp/overlay.dtbo"
"$DTC" -I dtb -O dts -o "$tmp/result.dts" "$tmp/result.dtb"
python3 - "$tmp/result.dts" <<'PY'
import re, sys
s = open(sys.argv[1]).read()
m = re.search(r'j71s-nvme-scratch\s*\{([^{}]*)\}', s)
assert m, 'scratch reservation missing'
n = m.group(1)
assert re.search(r'size\s*=\s*<0x00\s+0xe00000>', n)
assert re.search(r'alignment\s*=\s*<0x00\s+0x100000>', n)
assert re.search(r'\bno-map\s*;', n)
assert not re.search(r'\breg\s*=', n), 'must be dynamically allocated'
assert 'existing@800000000' in s, 'existing reservation lost'
assert 'nvmmu-iova' not in s, 'no DMA address assigned'
print('Dynamic scratch reservation overlay validated; no DMA configured.')
PY
