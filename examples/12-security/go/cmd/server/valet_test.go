package main

import "testing"

func TestValetRoundTrip(t *testing.T) {
	valetSecret = "test-secret"
	v := mintValet("exports/report.csv", "GET")
	tok, exp := v["token"].(string), v["expires"].(int64)
	if !verifyValet("exports/report.csv", "GET", exp, tok) {
		t.Fatal("valid key rejected")
	}
	if verifyValet("exports/report.csv", "DELETE", exp, tok) {
		t.Fatal("operation mismatch accepted")
	}
	if verifyValet("other", "GET", exp, tok) {
		t.Fatal("resource mismatch accepted")
	}
	if verifyValet("exports/report.csv", "GET", 9999999999, tok) {
		t.Fatal("expiry mismatch accepted")
	}
	if verifyValet("exports/report.csv", "GET", 9999999999, "tampered") {
		t.Fatal("garbage accepted")
	}
	valetSecret = "other"
	if verifyValet("exports/report.csv", "GET", exp, tok) {
		t.Fatal("wrong secret accepted")
	}
}
