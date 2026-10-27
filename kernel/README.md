# Kernel build

`build` fetches the pinned Linux revision, applies the selected target's patches
and config, compiles the kernel and external modules, stages the modules, and
runs the target's final-DTB recipe. Git and Podman are required.

```sh
./kernel/build j71b --output out/kernel/j71b
```

An experimental J71s kernel and unmodified device tree can be built with
`./kernel/build j71s --output out/kernel/j71s`. This is a RAM-boot bring-up
target for the S8000 iPad 5 Wi-Fi, not an installation image. It does not
enable touchscreen or internal storage; see [J71s device tree](devicetree/j71s/README.md).

Scratch remains in ignored `kernel/.work/j71b/`. `--resume` continues an
interrupted build using that scratch directory; `--output` must name a new
directory. The result contains `Image.gz`, `j71b.dtb`, `kernel.release` and
`lib/modules/`.

The J71b NVMe module has mutually exclusive load modes: `j71b_ro_test=1`
retains the command-level read-only whitelist; `j71b_rw=1` opts into normal
read-write commands. The separate `nvme-core` module also requires `j71b_rw=1`
to stop forcing the J71b namespace read-only. Both matching modules must be
loaded in a fresh recovery boot. The combined mode is compiled, not yet
hardware-proven.
