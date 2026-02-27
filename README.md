# Apache Fineract Tenant Management Utility

This utility provides a robust CLI tool for adding and managing tenants in
an [Apache Fineract](https://fineract.apache.org/) installation. It handles the creation of tenant-specific databases
and the necessary metadata registration in the Fineract system database.

## Features

- **Multi-database support**: Works with both MySQL and PostgreSQL.
- **Secure credential handling**: Secrets can be provided via environment variables or interactive prompts to avoid
  appearing in shell history.
- **Master Password Encryption**: Automatically handles password hashing and encryption required for Fineract's
  `tenants` table.
- **Dry-run mode**: Preview the SQL statements that would be executed without making any changes to the database.
- **Safe SQL execution**: Uses temporary option files (MySQL) or environment variables (PostgreSQL) to avoid exposing
  passwords in command-line arguments.

## Prerequisites

- **Python**: 3.10 or higher.
- **Database Clients**:
    - For MySQL: `mysql` client must be in your system's PATH.
    - For PostgreSQL: `psql` client must be in your system's PATH.
- **Fineract Databases**: Access to the Fineract system database (default name: `fineract_tenants`).

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Pinchez25/fineract_tenant.git
   cd fineract-tenant-manager
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The utility can be configured using command-line arguments or environment variables. Using environment variables is
recommended for sensitive information.

### Supported Environment Variables

| Variable                   | Description                                                        |
|----------------------------|--------------------------------------------------------------------|
| `FINERACT_DB_PASSWORD`     | Password for the new tenant's database.                            |
| `FINERACT_SYS_DB_PASSWORD` | Password for the Fineract system database (e.g., `root` password). |
| `FINERACT_MASTER_PASSWORD` | Fineract master encryption password (default: `fineract`).         |

## Usage

You can run the utility using `python -m main` or by invoking `cli.py` directly.

### Basic Examples

**Adding a MySQL tenant (Minimal):**

```bash
python main.py --tenant-id bank_a --tenant-name "Bank A" \
    --db-name fineract_bank_a --db-username root --sys-db-username root
```

**Adding a PostgreSQL tenant:**

```bash
python main.py --tenant-id bank_c --tenant-name "Bank C" \
    --db-type postgresql --db-port 5432 \
    --db-name fineract_bank_c --db-username postgres --sys-db-username postgres
```

**Dry Run (preview SQL only):**

```bash
python main.py --tenant-id bank_dry --tenant-name "Dry Run Test" \
    --db-name fineract_dry --db-username root --sys-db-username root \
    --dry-run
```

### Command Line Options

| Argument            | Required | Default     | Description                                |
|---------------------|----------|-------------|--------------------------------------------|
| `--tenant-id`       | Yes      | -           | Unique identifier for the tenant.          |
| `--tenant-name`     | Yes      | -           | Display name for the tenant.               |
| `--db-type`         | No       | `mysql`     | Database engine (`mysql` or `postgresql`). |
| `--db-name`         | Yes      | -           | Name of the tenant's database.             |
| `--db-username`     | Yes      | -           | Username for the tenant's database.        |
| `--sys-db-username` | Yes      | -           | Username for the system database.          |
| `--db-server`       | No       | `localhost` | Hostname of the tenant DB server.          |
| `--db-port`         | No       | 3306/5432   | Port of the tenant DB server.              |
| `--timezone`        | No       | `UTC`       | Timezone for the tenant.                   |
| `--dry-run`         | No       | `False`     | Print SQL without executing.               |

For a full list of options, run:

```bash
python main.py --help
```

## Security Design

- **Password Safety**: This tool never passes passwords as plain-text CLI arguments.
    - For **MySQL**, it creates a temporary option file with `0600` permissions that is deleted immediately after
      execution.
    - For **PostgreSQL**, it uses the `PGPASSWORD` environment variable.
- **No Residual Secrets**: Secrets are only held in memory or temporary files that are cleaned up upon exit, even if an
  error occurs.

## Licence

This project is licensed under the Apache Licence 2.0 – see the `cli.py` header for details.
