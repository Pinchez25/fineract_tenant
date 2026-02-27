#!/usr/bin/env bash

set -euo pipefail

echo "Example for Creating tenant: bank_a ..."

python main.py \
  --tenant-id my_tenant \
  --tenant-name "My Tenant" \
  --db-name bank_a \
  --db-username root \
  --db-password mysql \
  --sys-db-username root \
  --sys-db-password mysql \
  --master-password fineract \

echo "Tenant bank_a created successfully."