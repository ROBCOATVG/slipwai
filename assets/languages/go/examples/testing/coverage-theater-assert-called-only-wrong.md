```go
func TestHandlePayment_CallsProcess(t *testing.T) {
	spy := &processSpy{}

	handlePayment(spy, payment)

	if !spy.calledWith(payment) {
		t.Fatal("expected process to be called with payment") // so what?
	}
}
```
