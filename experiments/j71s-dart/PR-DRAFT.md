# iommu/apple-dart: fix packed S5L stream control updates

The older DART implementation stores four eight-bit stream controls in one
register. Its write function retains the selected old byte but clears the
other bytes, then ORs the new value into the low byte. For example, enabling
stream 1 can alter stream 0 and erase streams 2 and 3.

Replace only the selected byte, reject invalid stream IDs or values, and hold
the existing DART lock during the shared-register read/modify/write. This
preserves independent stream state and prevents concurrent updates from losing
each other.

Validation: the corrected driver compiled with the J71s kernel configuration
and LLVM 19. A host-side test executes the actual patched function with a
mocked register, checking enable and disable for all four streams, other-byte
preservation, lock use and invalid arguments. The original and unlocked variants
fail the corresponding checks. The test is available at
`experiments/j71s-dart/test-tcr.py` in
`joshgk00/hardware`'s `ipad-5-battery-experiment` branch. On an iPad 5, the
corrected driver completed an isolated DART reset. A
subsequent software-only consumer boot registered a DMA domain but logged an
invalidate timeout; the driver does not propagate that error on attachment.
Neither observation verifies address translation, physical DMA or storage.
This fix does not claim S8000 hardware support.
