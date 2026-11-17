PATCH

**A stage that ends a moment before its captain ends it no longer parks its slice.** On macOS a signal to a
process group whose only member has exited and not yet been collected is refused, and the captain took the
refusal for a fault: the slice parked on "the captain met PermissionError: Operation not permitted". The
refusal is read as what it means, that the stage is gone.

**Catch-up:** run `slipwai migrate` to carry the corrected captain into a project; nothing else to do.
