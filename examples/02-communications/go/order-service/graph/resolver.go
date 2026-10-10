package graph

import "github.com/jackc/pgx/v5/pgxpool"

// Resolver holds the database pool shared by every request.
type Resolver struct {
	Pool *pgxpool.Pool
}
