```go
// gifting/hexagon/domain/pledge.go — aggregate operation, pure function
package domain

// RecordPledge is the aggregate operation. No ports, no infrastructure, no
// goroutines: values in, a decision out. Invariant violations (as opposed
// to expected business rejections) panic, because they mean an Occasion or
// Money value was already corrupt before this function ran.
func RecordPledge(occasion Occasion, pledgeID PledgeID, contributorID ContributorID, amount Money) PledgeDecision {
	if occasion.IsFundingClosed {
		return PledgeDecision{Ok: false, Reason: ReasonFundingClosed}
	}

	if amount.Currency != occasion.TotalPledged.Currency || occasion.TotalPledged.Currency != occasion.Budget.Currency {
		return PledgeDecision{Ok: false, Reason: ReasonCurrencyMismatch}
	}

	if occasion.TotalPledged.MinorUnits < 0 || occasion.Budget.MinorUnits < 0 || amount.MinorUnits < 0 {
		panic("invalid Money invariant: minor units must not be negative")
	}

	if amount.MinorUnits <= 0 {
		return PledgeDecision{Ok: false, Reason: ReasonNonPositiveAmount}
	}

	if occasion.TotalPledged.MinorUnits > occasion.Budget.MinorUnits {
		panic("invalid Occasion invariant: total pledged exceeds budget")
	}

	remaining := occasion.Budget.MinorUnits - occasion.TotalPledged.MinorUnits
	if amount.MinorUnits > remaining {
		return PledgeDecision{Ok: false, Reason: ReasonExceedsBudget}
	}

	totalPledgedMinorUnits := occasion.TotalPledged.MinorUnits + amount.MinorUnits
	if totalPledgedMinorUnits < occasion.TotalPledged.MinorUnits {
		panic("money addition overflowed")
	}

	updatedOccasion := occasion
	updatedOccasion.TotalPledged = Money{
		MinorUnits: totalPledgedMinorUnits,
		Currency:   occasion.TotalPledged.Currency,
	}

	event := PledgeRecorded{
		ID:            pledgeID,
		OccasionID:    occasion.ID,
		ContributorID: contributorID,
		Amount:        amount,
	}

	return PledgeDecision{
		Ok:       true,
		Occasion: updatedOccasion,
		Events:   []PledgeRecorded{event},
	}
}
```
