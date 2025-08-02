#!/usr/bin/env bash
set -e
cd /tmp

echo "Running: dbw launch blooop/test_dbw launch and confirming the working directory is test_dbw launch to match the name of the git repo"
dbw launch blooop/test_dbw launch pwd
