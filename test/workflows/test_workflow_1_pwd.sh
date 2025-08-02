#!/usr/bin/env bash
set -e
cd /tmp

echo "Running: dbw blooop/test_dbw and confirming the working directory is test_dbw to match the name of the git repo"
dbw blooop/test_dbw pwd
