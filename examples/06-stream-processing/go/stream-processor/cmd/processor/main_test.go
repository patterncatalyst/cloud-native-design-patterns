package main

import (
	"math/big"
	"testing"
)

func TestMoneyHalfUp(t *testing.T) {
	for in, want := range map[string]string{"0": "0.00", "12.345": "12.35", "12.344": "12.34", "-2.005": "-2.01", "5": "5.00", "1e2": "100.00", "0.005": "0.01"} {
		r, ok := decimal(in)
		if !ok {
			t.Fatalf("decimal(%q) rejected", in)
		}
		if got := money(r); got != want {
			t.Errorf("money(%s)=%s want %s", in, got, want)
		}
	}
}

func TestParse(t *testing.T) {
	cases := []struct {
		in       string
		merchant string
		total    string
		ok       bool
	}{
		{`{"merchant_id":"m","total":12.5}`, "m", "12.5", true},
		{`{"merchant_id":7,"total":"3"}`, "7", "3", true},
		{`{"merchant_id":"m"}`, "m", "0", true},
		{`{"merchant_id":null}`, "", "", false},
		{`{"merchant_id":""}`, "", "", false},
		{`{"merchant_id":{}}`, "", "", false},
		{`not json`, "", "", false},
	}
	for _, c := range cases {
		m, tot, ok := parse([]byte(c.in))
		if ok != c.ok || m != c.merchant || tot != c.total {
			t.Errorf("parse(%s)=(%q,%q,%v)", c.in, m, tot, ok)
		}
	}
	for _, bad := range []string{"abc", "NaN", "Infinity", "true", "1e999999", "{}"} {
		if _, ok := decimal(bad); ok {
			t.Errorf("decimal(%q) should be rejected", bad)
		}
	}
}

func TestStoredTotalRoundTrip(t *testing.T) {
	a, _ := decimal("10.005")
	sum := new(big.Rat).Add(new(big.Rat), a)
	stored := sum.RatString() // "2001/200": a fraction the input parser would reject
	back, ok := new(big.Rat).SetString(stored)
	if !ok || back.Cmp(a) != 0 {
		t.Fatalf("round trip of %q failed", stored)
	}
}
