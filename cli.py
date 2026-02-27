#!/usr/bin/env python3
"""
Apache Fineract Tenant Addition Utility — CLI entry point.

Usage:
    python -m fineract_tenant --help
    python -m fineract_tenant --tenant-id bank_a --tenant-name "Bank A" \\
        --db-name fineract_bank_a --db-username root --sys-db-username root

Sensitive credentials can be supplied via environment variables to avoid
them appearing in shell history:
    export FINERACT_DB_PASSWORD=secret
    export FINERACT_SYS_DB_PASSWORD=secret
    export FINERACT_MASTER_PASSWORD=change_me_in_production

License: Apache License 2.0
"""

import argparse
import getpass
import logging
import os
import sys

from constants import (
    DEFAULT_MASTER_PASSWORD,
    DEFAULT_MYSQL_PORT,
    DEFAULT_POSTGRES_PORT,
    DEFAULT_SYS_DB_NAME,
    DEFAULT_TIMEZONE,
)
from tenant_manager import TenantManager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Secret resolution
# ---------------------------------------------------------------------------

def _resolve_secret(cli_value: str | None, env_var: str, prompt: str, *, allow_default: str | None = None) -> str:
    """
    Return the first non-empty value from:
        CLI argument → environment variable → interactive prompt → allow_default

    Raises SystemExit if no value is obtained and allow_default is None.
    """
    if cli_value:
        return cli_value
    if env_value := os.environ.get(env_var):
        return env_value
    entered = getpass.getpass(f"{prompt}: ")
    if entered:
        return entered
    if allow_default is not None:
        log.warning("No value supplied for %s; using built-in default. Change this in production.", env_var)
        return allow_default
    raise SystemExit(f"ERROR: {env_var} is required but was not provided.")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m fineract_tenant",
        description="Apache Fineract Tenant Creation Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Environment variables (recommended for secrets):
              FINERACT_DB_PASSWORD       Tenant database password
              FINERACT_SYS_DB_PASSWORD   System database password
              FINERACT_MASTER_PASSWORD   Master encryption password
            
            Examples:
              # MySQL (minimal)
              python -m fineract_tenant --tenant-id bank_a --tenant-name "Bank A" \\
                  --db-name fineract_bank_a --db-username root --sys-db-username root
            
              # Dry run — prints SQL without executing
              python -m fineract_tenant --tenant-id bank_b --tenant-name "Bank B" \\
                  --db-name fineract_bank_b --db-username root --sys-db-username root --dry-run
            
              # PostgreSQL
              python -m fineract_tenant --tenant-id bank_c --tenant-name "Bank C" \\
                  --db-type postgresql --db-port 5432 \\
                  --db-name fineract_bank_c --db-username postgres --sys-db-username postgres
            """,
         )

    tenant = parser.add_argument_group("Tenant")
    tenant.add_argument("--tenant-id", required=True, help="Unique identifier, e.g. bank_a")
    tenant.add_argument("--tenant-name", required=True, help='Display name, e.g. "Bank A"')
    tenant.add_argument("--timezone", default=DEFAULT_TIMEZONE, help=f"Tenant timezone (default: {DEFAULT_TIMEZONE})")

    parser.add_argument(
        "--db-type",
        default="mysql",
        choices=["mysql", "postgresql"],
        help="Database engine (default: mysql)",
    )

    db = parser.add_argument_group("Tenant database")
    db.add_argument("--db-server", default="localhost")
    db.add_argument("--db-port", type=int, default=0,
                    help=f"Default: {DEFAULT_MYSQL_PORT} (MySQL) or {DEFAULT_POSTGRES_PORT} (PostgreSQL)")
    db.add_argument("--db-name", required=True)
    db.add_argument("--db-username", required=True)
    db.add_argument("--db-password", default=None,
                    help="Env: FINERACT_DB_PASSWORD  (prompted if omitted)")
    db.add_argument("--db-connection-params", default="")

    sys_db = parser.add_argument_group(f"System database (default: {DEFAULT_SYS_DB_NAME})")
    sys_db.add_argument("--sys-db-server", default="localhost")
    sys_db.add_argument("--sys-db-port", type=int, default=0,
                        help="Defaults to match --db-type")
    sys_db.add_argument("--sys-db-name", default=DEFAULT_SYS_DB_NAME)
    sys_db.add_argument("--sys-db-username", required=True)
    sys_db.add_argument("--sys-db-password", default=None,
                        help="Env: FINERACT_SYS_DB_PASSWORD  (prompted if omitted)")

    parser.add_argument("--master-password", default=None,
                        help="Env: FINERACT_MASTER_PASSWORD")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print SQL without executing any changes")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Resolve default ports
    default_port = DEFAULT_POSTGRES_PORT if args.db_type == "postgresql" else DEFAULT_MYSQL_PORT
    if args.db_port == 0:
        args.db_port = default_port
    if args.sys_db_port == 0:
        args.sys_db_port = default_port

    # Resolve secrets — master password has a (weak) built-in default for dev convenience
    args.db_password = _resolve_secret(
        args.db_password, "FINERACT_DB_PASSWORD", "Tenant DB password"
    )
    args.sys_db_password = _resolve_secret(
        args.sys_db_password, "FINERACT_SYS_DB_PASSWORD", "System DB password"
    )
    args.master_password = _resolve_secret(
        args.master_password, "FINERACT_MASTER_PASSWORD", "Master encryption password",
        allow_default=DEFAULT_MASTER_PASSWORD,
    )

    sys.exit(0 if TenantManager(args).run() else 1)


if __name__ == "__main__":
    main()
