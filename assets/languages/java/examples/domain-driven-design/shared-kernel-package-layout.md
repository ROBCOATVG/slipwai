```java
// A shared kernel is a package with a named owner and a reviewed public API — not a `common` bucket.
//
//   com.example.shop.monetaryvalues     — Money, Currency; owned by the payments team
//   com.example.shop.contactaddresses   — EmailAddress, PostalAddress; a separate owner
//
// Two packages rather than one `shared`, because sharing has to be earned per concept: everything in a
// shared kernel is something every consumer must agree to change together, and a bucket makes that
// agreement invisible.
//
// `module-info.java` states it out loud, so an accidental dependency on an internal is a compile error
// rather than a code-review question:
module com.example.shop.monetaryvalues {
    exports com.example.shop.monetaryvalues;   // the reviewed contract, and nothing else
}
```
