```go
// ❌ Route handler hits the database directly
func ListActiveUsers(w http.ResponseWriter, r *http.Request) {
	rows, err := db.QueryContext(r.Context(), `SELECT id, email FROM users WHERE active = true`)
	if err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	// ...
	_ = rows
}

// ✅ Route handler calls a use case, which goes through a port
func ListActiveUsers(w http.ResponseWriter, r *http.Request) {
	users, err := getActiveUsers.Execute(r.Context(), userRepo)
	if err != nil {
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}
	// ...
	_ = users
}
```
