```go
type observation struct {
	kind       string
	reason     PledgeRejectionReason
	amount     Money
	occasionID OccasionID
}

// RecordingPledgeInstrumentation is a recording fake for the
// PledgeInstrumentation port — each call appends an observation so
// use-case tests can assert on instrumentation as behavior, not as
// an afterthought.
type RecordingPledgeInstrumentation struct {
	Observed []observation
}

func (r *RecordingPledgeInstrumentation) PledgeRejected(reason PledgeRejectionReason, occasionID OccasionID) {
	r.Observed = append(r.Observed, observation{kind: "pledge-rejected", reason: reason, occasionID: occasionID})
}

func (r *RecordingPledgeInstrumentation) PledgeAccepted(amount Money, occasionID OccasionID) {
	r.Observed = append(r.Observed, observation{kind: "pledge-accepted", amount: amount, occasionID: occasionID})
}

func TestPledgingToOccasions_AnnouncesRejectionWhenFundingIsClosed(t *testing.T) {
	closedOccasion := newOccasion(withFundingClosed(true))
	instrumentation := &RecordingPledgeInstrumentation{}
	pledging := NewPledgingToOccasions(
		newFakeOccasionRepository(closedOccasion),
		newFakeContributorRepository(),
		instrumentation,
	)

	if _, err := pledging.PledgeToOccasion(newPledge(withOccasionID(closedOccasion.ID))); err != nil {
		t.Fatalf("PledgeToOccasion returned unexpected error: %v", err)
	}

	want := observation{kind: "pledge-rejected", reason: "funding-closed", occasionID: closedOccasion.ID}
	for _, got := range instrumentation.Observed {
		if got == want {
			return
		}
	}
	t.Errorf("Observed = %+v, want it to contain %+v", instrumentation.Observed, want)
}
```
