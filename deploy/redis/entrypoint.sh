#!/bin/sh
# Redis entrypoint: enable ACL when REDIS_PASSWORD is set; otherwise open (dev).
set -eu

ACL_FILE=/tmp/brevio-redis.acl
DATA_DIR=/data

mkdir -p "$DATA_DIR"

if [ -n "${REDIS_PASSWORD:-}" ]; then
  USERNAME="${REDIS_USERNAME:-brevio}"
  # Escape ACL-special characters in password for the ACL file.
  # Redis ACL plaintext passwords after '>' cannot contain spaces unquoted;
  # we reject whitespace to avoid ambiguous ACL lines.
  case "$REDIS_PASSWORD" in
    *[[:space:]]*)
      echo "REDIS_PASSWORD must not contain whitespace" >&2
      exit 1
      ;;
  esac

  cat >"$ACL_FILE" <<EOF
user default off
user ${USERNAME} on >${REDIS_PASSWORD} ~* &* +@all -@admin -@dangerous
EOF
  echo "Starting Redis with ACL user '${USERNAME}' (default user disabled)"
  exec redis-server \
    --appendonly yes \
    --protected-mode yes \
    --dir "$DATA_DIR" \
    --aclfile "$ACL_FILE"
fi

echo "Starting Redis without ACL (REDIS_PASSWORD unset — development only)"
exec redis-server --appendonly yes --protected-mode yes --dir "$DATA_DIR"
