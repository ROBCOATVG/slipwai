MINOR

**`slipwai language install java` installs Java.** It did not: it brought the family and its default
framework, and the loader refused what it could not read — *family java's prune_rows name `spring-web`,
which is not a feature the pruner knows*. Asking for `java-spring` instead failed the same way on
`quarkus-rest`. Only naming both at once ever worked, and nothing said so.

A family's `prune_rows` are the family's, and may name a feature that any of its backends declares — and a
feature arrives with the backend declaring it. So a family whose frameworks are separate packages cannot be
loaded one framework at a time. Installing a family now brings every framework of it the index offers,
whichever half was asked for, and says which came along. Java is the only family with more than one
framework package today, so this changes nothing anywhere else.
