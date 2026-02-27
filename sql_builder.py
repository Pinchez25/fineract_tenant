"""
SQL generation for Fineract tenant provisioning.

All user-supplied strings pass through _escape_sql_string() before being
interpolated into SQL, preventing SQL injection via tenant names, db names, etc.

Note: parameterised queries via the Python DB-API would be ideal, but since we
shell out to mysql/psql CLIs we mitigate injection by explicit escaping and
strict input validation in TenantManager._validate().
"""

from datetime import datetime, timezone

from constants import (
    POOL_ABANDON_WHEN_PERCENTAGE_FULL,
    POOL_INITIAL_SIZE,
    POOL_LOG_ABANDONED,
    POOL_MAX_ACTIVE,
    POOL_MAX_IDLE,
    POOL_MIN_EVICTABLE_IDLE_TIME_MS,
    POOL_MIN_IDLE,
    POOL_REMOVE_ABANDONED,
    POOL_REMOVE_ABANDONED_TIMEOUT,
    POOL_SUSPECT_TIMEOUT,
    POOL_TEST_ON_BORROW,
    POOL_TIME_BETWEEN_EVICTION_RUNS_MS,
    POOL_VALIDATION_INTERVAL,
)


def _escape_sql_string(value: str) -> str:
    """
    Escape a string for safe interpolation inside SQL single quotes.

    Doubles single quotes and removes NUL bytes — the minimum needed when
    you cannot use parameterised queries.
    """
    return value.replace("\\", "\\\\").replace("'", "''").replace("\x00", "")


def build_insert_connection(
        conn_id: int,
        db_host: str,
        db_name: str,
        db_port: int,
        db_user: str,
        encrypted_pass: str,
        master_hash: str,
        db_params: str,
) -> str:
    """Return the INSERT INTO tenant_server_connections statement."""
    return (
        "INSERT INTO tenant_server_connections ("
        "    id, schema_server, schema_name, schema_server_port,"
        "    schema_username, schema_password, master_password_hash,"
        "    schema_connection_parameters, auto_update,"
        "    pool_initial_size, pool_validation_interval,"
        "    pool_remove_abandoned, pool_remove_abandoned_timeout,"
        "    pool_log_abandoned, pool_abandon_when_percentage_full,"
        "    pool_test_on_borrow, pool_max_active, pool_min_idle,"
        "    pool_max_idle, pool_suspect_timeout,"
        "    pool_time_between_eviction_runs_millis,"
        "    pool_min_evictable_idle_time_millis"
        ") VALUES ("
        f"    {conn_id},"
        f"    '{_escape_sql_string(db_host)}',"
        f"    '{_escape_sql_string(db_name)}',"
        f"    '{db_port}',"
        f"    '{_escape_sql_string(db_user)}',"
        f"    '{_escape_sql_string(encrypted_pass)}',"
        f"    '{_escape_sql_string(master_hash)}',"
        f"    '{_escape_sql_string(db_params)}',"
        f"    1,"
        f"    {POOL_INITIAL_SIZE}, {POOL_VALIDATION_INTERVAL},"
        f"    {POOL_REMOVE_ABANDONED}, {POOL_REMOVE_ABANDONED_TIMEOUT},"
        f"    {POOL_LOG_ABANDONED}, {POOL_ABANDON_WHEN_PERCENTAGE_FULL},"
        f"    {POOL_TEST_ON_BORROW}, {POOL_MAX_ACTIVE}, {POOL_MIN_IDLE},"
        f"    {POOL_MAX_IDLE}, {POOL_SUSPECT_TIMEOUT},"
        f"    {POOL_TIME_BETWEEN_EVICTION_RUNS_MS},"
        f"    {POOL_MIN_EVICTABLE_IDLE_TIME_MS}"
        ");"
    )


def build_insert_tenant(
        tenant_id: str,
        tenant_name: str,
        timezone_id: str,
        conn_id: int,
) -> str:
    """Return the INSERT INTO tenants statement."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return (
        "INSERT INTO tenants ("
        "    identifier, name, timezone_id, oltp_id, report_id,"
        "    created_date, lastmodified_date"
        ") VALUES ("
        f"    '{_escape_sql_string(tenant_id)}',"
        f"    '{_escape_sql_string(tenant_name)}',"
        f"    '{_escape_sql_string(timezone_id)}',"
        f"    {conn_id}, {conn_id},"
        f"    '{now}', '{now}'"
        ");"
    )


def build_create_database(db_type: str, db_name: str) -> tuple[str, str | None]:
    """
    Return (sql, target_db) for the CREATE DATABASE statement.

    MySQL's CREATE DATABASE does not require a target DB; PostgreSQL must
    connect to the maintenance database ('postgres').
    """
    safe_name = _escape_sql_string(db_name)
    if db_type == "mysql":
        sql = (
            f"CREATE DATABASE IF NOT EXISTS `{safe_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        return sql, None
    # PostgreSQL
    return f'CREATE DATABASE "{safe_name}";', "postgres"


def build_rollback_connection(db_name: str) -> str:
    """Return a best-effort DELETE to undo a partially inserted connection row."""
    return (
        "DELETE FROM tenant_server_connections "
        f"WHERE schema_name = '{_escape_sql_string(db_name)}';"
    )
