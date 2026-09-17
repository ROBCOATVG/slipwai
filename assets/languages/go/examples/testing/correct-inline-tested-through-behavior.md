```go
// loadParticipantView.go
func loadParticipantView(ctx context.Context, db DB, eventID EventID, userID UserID) (ParticipantView, error) {
	items, err := getItems(ctx, db, eventID, userID)
	if err != nil {
		return ParticipantView{}, err
	}

	view := ParticipantView{}
	for _, item := range items {
		if item.IsClaimed && item.IsClaimedByCurrentUser {
			view.YourClaims = append(view.YourClaims, item)
		} else if !item.IsClaimedByCurrentUser {
			view.Available = append(view.Available, item)
		}
	}
	return view, nil
}

// The behavioral test for loadParticipantView covers the filtering:
func TestLoadParticipantView_SplitsClaimedAndAvailable(t *testing.T) {
	result, err := loadParticipantView(context.Background(), db, eventID, userID)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(result.YourClaims) != 1 {
		t.Fatalf("len(YourClaims) = %d, want 1", len(result.YourClaims))
	}
	if len(result.Available) != 2 {
		t.Fatalf("len(Available) = %d, want 2", len(result.Available))
	}
}
```
