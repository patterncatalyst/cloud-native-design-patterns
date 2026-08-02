package domain

type Order struct {
	ID       string
	SKU      string
	Quantity int
	Status   string
}

type PlaceOrderCmd struct {
	SKU      string
	Quantity int
}

type OrderPlaced struct {
	OrderID  string
	SKU      string
	Quantity int
}
