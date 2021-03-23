#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE mal2user WITH LOGIN PASSWORD 'change_pass' SUPERUSER INHERIT CREATEDB CREATEROLE;
    CREATE DATABASE mal2restdb OWNER mal2user;
EOSQL

