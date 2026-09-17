```java
// WRONG — a wrapper that adds a layer and no information. The stack trace already said where it happened,
// and "Failed to pledge" says less than the cause did.
try {
    persistence.save(occasion);
} catch (SQLException failure) {
    throw new PledgeException("Failed to pledge", failure);
}

// Wrap only when the wrapper adds something the caller can use: a different type it is meant to catch, or
// a fact the cause did not carry — which stream, which id, which expected version.
```
