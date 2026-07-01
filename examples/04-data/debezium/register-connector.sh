#!/usr/bin/env bash
set -euo pipefail

CONNECT_URL="${1:-http://localhost:8083}"

curl -sf -X POST "$CONNECT_URL/connectors" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "outbox-connector",
    "config": {
      "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
      "database.hostname": "postgres",
      "database.port": "5432",
      "database.user": "appuser",
      "database.password": "apppass",
      "database.dbname": "appdb",
      "topic.prefix": "cndp",
      "table.include.list": "public.outbox",
      "plugin.name": "pgoutput",
      "publication.name": "outbox_pub",
      "transforms": "outbox",
      "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
      "transforms.outbox.table.field.event.id": "id",
      "transforms.outbox.table.field.event.key": "aggregate_id",
      "transforms.outbox.table.field.event.type": "event_type",
      "transforms.outbox.table.field.event.payload": "payload",
      "transforms.outbox.route.by.field": "event_type",
      "transforms.outbox.route.topic.replacement": "${routedByValue}",
      "transforms.outbox.table.expand.json.payload": "true"
    }
  }'

echo ""
echo "Debezium outbox connector registered."
