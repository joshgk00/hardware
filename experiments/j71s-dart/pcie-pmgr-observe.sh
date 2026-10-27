#!/bin/sh
set -eu
[ "$(tr '\000' '\n' </proc/device-tree/compatible | head -n 1)" = apple,j71s ] || exit 1
for entry in pcie:310 aux:318 ref:148 link0:320 link1:328 link2:330 link3:338; do
 name=${entry%:*}; offset=${entry#*:}
 reg=$(busybox devmem "0x20e080$offset" 32)
 printf '%s actual=%s target=%s auto=%s parent_off=%s disabled=%s reset=%s all_ones=%s\n' "$name" "$(((reg >> 4) & 15))" "$((reg & 15))" "$(((reg >> 28) & 1))" "$(((reg >> 11) & 1))" "$(((reg >> 10) & 1))" "$(((reg >> 31) & 1))" "$((reg == 0xffffffff))"
done
