"""
TenantManager orchestrates the full tenant-creation workflow:
  1. Validate inputs
  2. Encrypt credentials
  3. Resolve next connection ID from the live system DB
  4. Create the tenant database
  5. Insert records into the system database
"""

import argparse
import logging

from constants import MYSQL_DEFAULT_CONN_PARAMS
from db_client import DatabaseClient
from encryptor import TenantEncryption
from sql_builder import (
    build_create_database,
    build_insert_connection,
    build_insert_tenant,
    build_rollback_connection,
)

log = logging.getLogger(__name__)


class TenantManager:
    """Orchestrates the full tenant creation workflow."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.tenant_id = args.tenant_id
        self.tenant_name = args.tenant_name
        self.timezone = args.timezone
        self.db_type = args.db_type.lower()
        self.dry_run = args.dry_run

        # Tenant DB
        self.db_host = args.db_server
        self.db_port = args.db_port
        self.db_name = args.db_name
        self.db_user = args.db_username
        self.db_pass = args.db_password
        self.db_params = args.db_connection_params or (
            MYSQL_DEFAULT_CONN_PARAMS if self.db_type == "mysql" else ""
        )

        # System DB
        self.sys_host = args.sys_db_server
        self.sys_port = args.sys_db_port
        self.sys_db = args.sys_db_name
        self.sys_user = args.sys_db_username
        self.sys_pass = args.sys_db_password

        # Encryption
        self.master_pass = args.master_password

        self._encrypted_pass: str = ""
        self._master_hash: str = ""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> bool:
        errors: list[str] = []

        if not self.tenant_id or not self.tenant_id.replace("_", "").isalnum():
            errors.append("--tenant-id must be alphanumeric (underscores allowed)")
        if not self.tenant_name:
            errors.append("--tenant-name is required")
        if not self.db_name or not self.db_name.replace("_", "").isalnum():
            errors.append("--db-name must be alphanumeric (underscores allowed)")
        for label, port in [("--db-port", self.db_port), ("--sys-db-port", self.sys_port)]:
            if not 1 <= port <= 65535:
                errors.append(f"{label} is out of range (1–65535)")
        if self.db_type not in ("mysql", "postgresql"):
            errors.append("--db-type must be 'mysql' or 'postgresql'")

        for msg in errors:
            log.error("Validation error: %s", msg)
        return not errors

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_sys_client(self) -> DatabaseClient:
        return DatabaseClient(
            self.db_type, self.sys_host, self.sys_port,
            self.sys_user, self.sys_pass, self.sys_db,
        )

    def _make_tenant_db_client(self) -> DatabaseClient:
        return DatabaseClient(
            self.db_type, self.db_host, self.db_port,
            self.db_user, self.db_pass,
        )

    def _next_connection_id(self) -> int:
        val = self._make_sys_client().query_scalar(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM tenant_server_connections;"
        )
        try:
            return int(val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            log.warning("Could not determine next connection ID; defaulting to 2")
            return 2

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _create_tenant_database(self) -> bool:
        log.info("Creating tenant database '%s'...", self.db_name)
        sql, target_db = build_create_database(self.db_type, self.db_name)
        if not self.dry_run:
            ok = self._make_tenant_db_client().execute(sql, target_db=target_db)
            if not ok:
                log.warning("Database may already exist — continuing")
        log.info("Tenant database ready.")
        return True

    def _insert_system_records(self, insert_conn: str, insert_tenant: str) -> bool:
        log.info("Inserting records into system database '%s'...", self.sys_db)
        client = self._make_sys_client()

        if not self.dry_run:
            if not client.execute(insert_conn):
                log.error("Failed to insert tenant_server_connections record")
                return False
            if not client.execute(insert_tenant):
                log.error("Failed to insert tenants record — rolling back connection record...")
                client.execute(build_rollback_connection(self.db_name))
                return False

        log.info("System database records inserted.")
        return True

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self) -> bool:
        log.info("=" * 60)
        log.info("Apache Fineract — New Tenant Setup")
        log.info("=" * 60)

        if not self._validate():
            return False

        log.info(
            "Tenant ID: %s | Name: %s | Timezone: %s | DB: %s://%s:%s/%s | "
            "SysDB: %s://%s:%s/%s%s",
            self.tenant_id, self.tenant_name, self.timezone,
            self.db_type, self.db_host, self.db_port, self.db_name,
            self.db_type, self.sys_host, self.sys_port, self.sys_db,
            " [DRY RUN]" if self.dry_run else "",
        )

        # 1. Encrypt credentials
        log.info("Encrypting credentials...")
        self._encrypted_pass = TenantEncryption.encrypt(self.master_pass, self.db_pass)
        self._master_hash = TenantEncryption.hash_master_password(self.master_pass)
        log.info("Credentials encrypted.")

        # 2. Resolve next connection ID
        conn_id = self._next_connection_id() if not self.dry_run else 2

        # 3. Build SQL
        insert_conn = build_insert_connection(
            conn_id, self.db_host, self.db_name, self.db_port,
            self.db_user, self._encrypted_pass, self._master_hash, self.db_params,
        )
        insert_tenant = build_insert_tenant(
            self.tenant_id, self.tenant_name, self.timezone, conn_id,
        )

        # 4. Create tenant DB
        if not self._create_tenant_database():
            return False

        # 5. Register in system DB
        if not self._insert_system_records(insert_conn, insert_tenant):
            return False

        log.info("=" * 60)
        log.info("Tenant created successfully!")
        log.info("=" * 60)
        log.info(
            "\nNext steps:\n"
            "  1. Run Liquibase migrations for the new tenant:\n"
            "       ./gradlew migrateTenantDB -PdbName=%s\n"
            "     (or restart Fineract — it will auto-migrate on startup)\n"
            "  2. Test with:\n"
            "       curl -u admin:password \\\n"
            "            -H 'Fineract-Platform-TenantId: %s' \\\n"
            "            http://localhost:8080/fineract-provider/api/v1/offices",
            self.db_name, self.tenant_id,
        )

        if self.dry_run:
            log.info("[DRY RUN] SQL that would be executed:\n\n%s\n\n%s", insert_conn, insert_tenant)

        return True
