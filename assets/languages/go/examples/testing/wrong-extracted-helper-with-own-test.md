```go
// prepareParticipantData.go (new file, one caller)
func prepareParticipantData(items []Item) ParticipantView {
	view := ParticipantView{}
	for _, item := range items {
		if item.IsClaimed && item.IsClaimedByCurrentUser {
			view.YourClaims = append(view.YourClaims, item)
		} else if !item.IsClaimedByCurrentUser {
			view.Available = append(view.Available, item)
		}
	}
	return view
}

// prepareParticipantData_test.go (tests the helper directly)
func TestPrepareParticipantData_FiltersClaims(t *testing.T) {
	// ...
}
```
