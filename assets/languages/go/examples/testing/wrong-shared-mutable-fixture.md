```go
// ❌ Package-level mutable fixture shared by every test
var sharedUser = User{ID: "user-123", Name: "Test User"}

func TestOne(t *testing.T) {
	sharedUser.Name = "Modified User"
}

func TestTwo(t *testing.T) {
	if sharedUser.Name != "Test User" { // order-dependent failure
		t.Fatalf("Name = %q, want %q", sharedUser.Name, "Test User")
	}
}
```
