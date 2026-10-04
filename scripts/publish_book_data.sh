#!/bin/sh
# Copy the book text and embeddings (volumes, parts, sections, paragraphs, chunks) from the local
# database to another PostgreSQL, such as the Neon database of a deployment. Accounts,
# conversations and logs stay local.
#
# The target must already have the schema: the deployed backend migrates at start, or run
#   docker compose exec -e DATABASE_URL='postgresql+psycopg://...' backend alembic upgrade head
#
# Run from the repository root, with the stack up (it uses the db container's pg_dump/psql):
#   TARGET_URL='postgresql://USER:PASSWORD@HOST/DB?sslmode=require' sh scripts/publish_book_data.sh
set -eu
: "${TARGET_URL:?set TARGET_URL to the target database (postgresql://..., without +psycopg)}"

docker compose exec -T -e TARGET_URL="$TARGET_URL" db sh -eu -c '
  TABLES="volumes book_parts book_sections book_paragraphs book_chunks"
  existing=$(psql "$TARGET_URL" -tAc "SELECT count(*) FROM volumes")
  if [ "$existing" != "0" ]; then
    echo "The target already has $existing volumes; nothing copied." >&2
    exit 1
  fi
  args=""
  for t in $TABLES; do args="$args -t $t"; done
  echo "Copying $TABLES ..."
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --data-only --no-owner --no-privileges $args \
    | psql "$TARGET_URL" -q -v ON_ERROR_STOP=1 --single-transaction > /dev/null
  for t in $TABLES; do
    printf "%-16s local %8s   target %8s\n" "$t" \
      "$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM $t")" \
      "$(psql "$TARGET_URL" -tAc "SELECT count(*) FROM $t")"
  done
  psql "$TARGET_URL" -q -c "ANALYZE"
'
