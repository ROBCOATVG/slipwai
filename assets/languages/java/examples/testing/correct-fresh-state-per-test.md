```java
@Test
void one() {
    User user = aUser().name("Modified User").build();  // fresh state
    // ...
}

@Test
void two() {
    User user = aUser().build();                        // unaffected by the test above
    assertThat(user.name()).isEqualTo("Test User");     // passes in any order
}
```
