#!/bin/sh
set -e

# Run pending migrations before the app starts.
# NOTE: fine for v1 (single container). If this ever runs as multiple
# replicas, concurrent `alembic upgrade head` calls can race - migrations
# should move to a separate release step before scaling out the backend.
alembic upgrade head

exec "$@"
