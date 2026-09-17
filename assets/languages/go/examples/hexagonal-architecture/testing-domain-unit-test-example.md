```go
func TestPledgeContribution_RejectsContributionExceedingAvailableBalance(t *testing.T) {
	occasion := newOccasion()
	poorContributor := newContributor(withAvailableBalance(newMoney(500, "GBP")))
	largePledge := newPledge(withAmount(newMoney(5_000, "GBP")))

	result := PledgeContribution(occasion, poorContributor, largePledge)

	if result.Success {
		t.Errorf("Success = true, want false for a pledge exceeding available balance")
	}
}
```
