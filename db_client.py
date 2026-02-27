"""
Thin database client that executes SQL via the CLI tools (mysql / psql).

Design decisions:
  - Passwords are NEVER passed as CLI arguments; MySQL uses a temp option file
    (chmod 0600, deleted in a finally block) and PostgreSQL uses PGPASSWORD.
  - A single private _run() method drives both execute() and query_scalar(),
    eliminating the duplication present in the original code.
  - subprocess calls honour SUBPROCESS_TIMEOUT to prevent hung DB calls.
"""

import logging
import os
import subprocess
import tempfile
import textwrap
from contextlib import contextmanager
from typing import Generator

from constants import SUBPROCESS_TIMEOUT

log = logging.getLogger(__name__)


@contextmanager
def _mysql_option_file(password: str) -> Generator[str, None, None]:
    """
    Write a MySQL option file containing only the client password,
    restricted to owner-read (0o600), and delete it on exit.
    """
    cfg = textwrap.dedent(f"""\
        [client]
        password={password}
    """)
    # delete=False so we can chmod before first use; we unlink manually.
    fd = tempfile.NamedTemporaryFile(mode="w", suffix=".cnf", delete=False)
    try:
        fd.write(cfg)
        fd.flush()
        fd.close()
        os.chmod(fd.name, 0o600)
        yield fd.name
    finally:
        try:
            os.unlink(fd.name)
        except OSError:
            log.warning("Could not remove temporary option file: %s", fd.name)


class DatabaseClient:
    """Execute SQL against MySQL or PostgreSQL without exposing credentials."""

    def __init__(
            self,
            db_type: str,
            host: str,
            port: int,
            username: str,
            password: str,
            dbname: str | None = None,
    ) -> None:
        self.db_type = db_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.dbname = dbname

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cmd(self, sql: str, target_db: str | None, scalar: bool) -> tuple[list[str], dict]:
        """
        Return (cmd, env) appropriate for the configured database type.

        *scalar* adds flags that strip column headers / whitespace so the
        caller can parse the first line directly.
        """
        db = target_db or self.dbname
        env = os.environ.copy()

        if self.db_type == "mysql":
            # Password injected via option file, never via argv
            # Caller is responsible for using _mysql_option_file context manager
            raise NotImplementedError("Call _build_mysql_cmd instead")

        # PostgreSQL
        env["PGPASSWORD"] = self.password
        cmd = [
            "psql",
            "-h", self.host,
            "-p", str(self.port),
            "-U", self.username,
        ]
        if db:
            cmd += ["-d", db]
        if scalar:
            cmd += ["-t", "-A"]  # tuples-only, unaligned
        cmd += ["-c", sql]
        return cmd, env

    def _run(self, sql: str, target_db: str | None, *, scalar: bool = False) -> tuple[int, str, str]:
        """
        Execute *sql* and return (returncode, stdout, stderr).

        Handles credential injection for both MySQL and PostgreSQL.
        """
        db = target_db or self.dbname

        if self.db_type == "mysql":
            with _mysql_option_file(self.password) as cfg_path:
                cmd = [
                    "mysql",
                    f"--defaults-extra-file={cfg_path}",
                    f"-h{self.host}",
                    f"-P{self.port}",
                    f"-u{self.username}",
                ]
                if db:
                    cmd.append(db)
                if scalar:
                    cmd += ["--skip-column-names", "--batch"]
                    cmd += ["-e", sql]
                else:
                    cmd += ["--execute", sql]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=SUBPROCESS_TIMEOUT,
                )
        else:
            env = os.environ.copy()
            env["PGPASSWORD"] = self.password
            cmd = [
                "psql",
                "-h", self.host,
                "-p", str(self.port),
                "-U", self.username,
            ]
            if db:
                cmd += ["-d", db]
            if scalar:
                cmd += ["-t", "-A"]
            cmd += ["-c", sql]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=SUBPROCESS_TIMEOUT,
            )

        return result.returncode, result.stdout, result.stderr



    def execute(self, sql: str, target_db: str | None = None) -> bool:
        """Execute *sql* (no result needed). Returns True on success."""
        code, _, err = self._run(sql, target_db)
        if code != 0:
            log.error("DB error: %s", err.strip())
            return False
        return True

    def query_scalar(self, sql: str, target_db: str | None = None) -> str | None:
        """
        Return the first cell of the first row as a string, or None on failure.
        """
        code, stdout, _ = self._run(sql, target_db, scalar=True)
        if code != 0 or not stdout.strip():
            return None
        return stdout.strip().splitlines()[0]
