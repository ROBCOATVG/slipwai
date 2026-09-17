package health

type Status struct {
	Status string `json:"status"`
}

func Check() Status { return Status{Status: "ok"} }
