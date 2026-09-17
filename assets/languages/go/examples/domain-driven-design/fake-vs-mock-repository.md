```go
package users

// UserID and User are minimal domain stand-ins.
type UserID string

type User struct {
	ID    UserID
	Email string
}

// UserRepository is the port both examples below implement.
type UserRepository interface {
	FindByID(id UserID) (User, bool, error)
	Save(user User) error
}

// Good: a fake — maintains real state behind the real interface. A test
// built on it exercises the same contract production code uses, so it
// proves the use case actually works, not just that a call happened.
type FakeUserRepository struct {
	store map[UserID]User
}

func NewFakeUserRepository(initial []User) *FakeUserRepository {
	store := make(map[UserID]User, len(initial))
	for _, user := range initial {
		store[user.ID] = user
	}
	return &FakeUserRepository{store: store}
}

func (f *FakeUserRepository) FindByID(id UserID) (User, bool, error) {
	user, ok := f.store[id]
	return user, ok, nil
}

func (f *FakeUserRepository) Save(user User) error {
	f.store[user.ID] = user
	return nil
}

// Bad: a "mock" that only records whether a method was called. It knows
// nothing about state, so it can't catch bugs like "saved the wrong user"
// or "saved twice" — it can only prove a call happened, which is rarely
// what the business rule actually requires.
type mockUserRepository struct {
	saveCalled bool
}

func (m *mockUserRepository) FindByID(id UserID) (User, bool, error) {
	return User{}, false, nil
}

func (m *mockUserRepository) Save(user User) error {
	m.saveCalled = true
	return nil
}
```
