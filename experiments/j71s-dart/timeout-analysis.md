# DART invalidation timeout: error handling review

In Hoolock kernel revision `6831bc701a6ce059e71e5aaa9488c9195bea6927`,
`apple_dart_s5l8960x_hw_stream_command()` returns an error when its busy-bit
poll times out. During paging-domain attachment,
`apple_dart_setup_translation()` ignores that error, and
`apple_dart_attach_dev_paging()` consequently returns success. On the J71s
software-consumer boot this allowed a DMA domain to be reported despite the
logged timeout. No physical DMA was attempted.

This should not be fixed by merely returning the error: before invalidation,
the driver adds stream IDs to the new domain and writes its page-table and
translation settings. The IOMMU core's group rollback does not restore the
failed device itself; it assumes a driver handles failure of its own attach
operation. Multiple devices may share stream IDs, so unconditionally removing
all the failed device's IDs from a domain can also remove stream IDs still
needed by another device. A safe change needs an explicit rollback design,
including previously attached domains, multiple DARTs, shared streams, and
failures during rollback; a stuck invalidation may make restoration itself
unreliable.

The separate `apple_dart_domain_flush_tlb()` also ignores errors, and
`apple_dart_iotlb_sync_map()` returns zero even when its flush times out.
The callbacks for whole-domain flush and unmap synchronization return void,
whereas the map synchronization callback returns an error to the IOMMU core.
Any change must account for mappings already installed and unmap cleanup,
not simply stop processing other DARTs at the first error.

These are source-review findings and a single timeout observation, not a
validated error-recovery patch. Further tests should model shared streams,
multiple DARTs, failure at each step, and transitions from existing domains
before attempting to use a modified driver with physical DMA.
