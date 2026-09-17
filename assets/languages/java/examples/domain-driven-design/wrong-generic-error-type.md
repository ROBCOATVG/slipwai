```java
// WRONG — a String tells the caller nothing it can act on, so every caller either ignores it or parses it.
// A parsed error message is a contract nobody wrote down.
public record Result<T>(boolean success, T data, String error) { }

// Use named reasons instead, and let the compiler check that each one is handled.
```
