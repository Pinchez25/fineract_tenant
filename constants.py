"""
Named constants for Apache Fineract tenant configuration.

Connection pool values mirror Fineract's default DataSource settings.
Adjust to suit your environment before deploying.
"""

# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------
PBKDF2_ITERATIONS: int = 65_536
AES_KEY_SIZE: int = 32  # 256-bit
SALT_SIZE: int = 16  # bytes
IV_SIZE: int = 16  # bytes
BCRYPT_ROUNDS: int = 12

# ---------------------------------------------------------------------------
# Database defaults
# ---------------------------------------------------------------------------
DEFAULT_MYSQL_PORT: int = 3306
DEFAULT_POSTGRES_PORT: int = 5432
DEFAULT_SYS_DB_NAME: str = "fineract_tenants"
DEFAULT_TIMEZONE: str = "UTC"
DEFAULT_MASTER_PASSWORD: str = "fineract"  # Must be overridden in production

# Default MySQL JDBC connection parameters
MYSQL_DEFAULT_CONN_PARAMS: str = "allowPublicKeyRetrieval=true"

# ---------------------------------------------------------------------------
# Connection pool defaults (Tomcat JDBC / HikariCP compatible)
# ---------------------------------------------------------------------------
POOL_INITIAL_SIZE: int = 5
POOL_VALIDATION_INTERVAL: int = 30_000  # ms
POOL_REMOVE_ABANDONED: int = 1
POOL_REMOVE_ABANDONED_TIMEOUT: int = 60  # seconds
POOL_LOG_ABANDONED: int = 1
POOL_ABANDON_WHEN_PERCENTAGE_FULL: int = 50
POOL_TEST_ON_BORROW: int = 1
POOL_MAX_ACTIVE: int = 50
POOL_MIN_IDLE: int = 20
POOL_MAX_IDLE: int = 10
POOL_SUSPECT_TIMEOUT: int = 60  # seconds
POOL_TIME_BETWEEN_EVICTION_RUNS_MS: int = 34_000
POOL_MIN_EVICTABLE_IDLE_TIME_MS: int = 60_000

# subprocess timeout (seconds); prevents hung DB calls blocking indefinitely
SUBPROCESS_TIMEOUT: int = 30
