package ledger

// Balance is what the ledger existed to keep.
func Balance(entries []int) int {
	total := 0
	for _, entry := range entries {
		total += entry
	}
	return total
}
