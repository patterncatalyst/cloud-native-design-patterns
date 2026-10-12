#!/bin/bash
# Sourced by run-postgresql from postgresql-start/, after initdb has created the role
# and the database from POSTGRESQL_USER, POSTGRESQL_PASSWORD and POSTGRESQL_DATABASE.
# (postgresql-init/ runs earlier, before the role exists, so it cannot be used here.)
# The sclorg image sources this file on every start; the schema uses IF NOT EXISTS,
# so a restart is a no-op. Running as appuser makes appuser the owner of the tables.
# uuid-ossp is a trusted extension, so the database owner may create it.
# shellcheck shell=bash
for sql in /opt/app-root/schema/*.sql; do
    echo "applying ${sql##*/}"
    psql -v ON_ERROR_STOP=1 -U "$POSTGRESQL_USER" -d "$POSTGRESQL_DATABASE" -f "$sql"
done
