"""Initialize a project-local PostgreSQL development cluster, never a system service.

Run with apps/api/.venv/Scripts/python.exe after extracting the official binaries
to .local/pgsql. Credentials remain in ignored project-local files.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
BIN = LOCAL / "pgsql" / "bin"
DATA = LOCAL / "pgdata"
ADMIN_FILE = LOCAL / "database-credentials.json"
ENV_FILE = ROOT / "apps" / "api" / ".env"
PORT = 55432


def run(*args: str, check: bool = True):
    return subprocess.run(args, check=check, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def main():
    if not (BIN / "initdb.exe").exists():
        raise SystemExit("Extract official PostgreSQL Windows binaries to .local/pgsql first.")
    if ADMIN_FILE.exists():
        credentials = json.loads(ADMIN_FILE.read_text())
    else:
        if DATA.exists() or ENV_FILE.exists():
            raise SystemExit("Existing database/environment found. Refusing to replace credentials.")
        credentials = {"admin": secrets.token_hex(32), "app": secrets.token_hex(32)}
        ADMIN_FILE.write_text(json.dumps(credentials), encoding="utf-8")
    if not (DATA / "PG_VERSION").exists():
        password_file = LOCAL / "initdb-password.tmp"
        try:
            password_file.write_text(credentials["admin"], encoding="ascii")
            run(str(BIN / "initdb.exe"), "-D", str(DATA), "-U", "postgres", "-A", "scram-sha-256",
                "--encoding=UTF8", "--locale=C", f"--pwfile={password_file}")
        finally:
            password_file.unlink(missing_ok=True)
        with (DATA / "postgresql.conf").open("a", encoding="utf-8") as config:
            config.write("\n# ProofAI local development only\nlisten_addresses = '127.0.0.1'\nport = 55432\n")
    if run(str(BIN / "pg_ctl.exe"), "-D", str(DATA), "status", check=False).returncode != 0:
        run(str(BIN / "pg_ctl.exe"), "-D", str(DATA), "-l", str(LOCAL / "postgres.log"), "-w", "start")
    with psycopg.connect(host="127.0.0.1", port=PORT, dbname="postgres", user="postgres",
                          password=credentials["admin"], autocommit=True) as connection:
        if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname = 'proofai'").fetchone():
            connection.execute(sql.SQL("CREATE ROLE proofai LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                sql.Literal(credentials["app"])))
        for name in ("proofai_dev", "proofai_test"):
            if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
                connection.execute(sql.SQL("CREATE DATABASE {} OWNER proofai").format(sql.Identifier(name)))
    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            f"DATABASE_URL=postgresql+psycopg://proofai:{credentials['app']}@127.0.0.1:{PORT}/proofai_dev\n"
            f"JWT_SECRET={secrets.token_urlsafe(48)}\nAPP_ORIGIN=http://localhost:5173\nCHAIN_ID=10143\n",
            encoding="utf-8")
    print("PostgreSQL is running on 127.0.0.1:55432; proofai_dev and proofai_test are ready.")
    print("Application credentials are in apps/api/.env (not printed). No Windows service was installed.")


if __name__ == "__main__":
    main()
