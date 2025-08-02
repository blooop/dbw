#!/usr/bin/env bash
set -e
cd /tmp

rm -rf /home/ags/.local/share/dbw

echo "Running: dbw blooop/test_dbw confirming the working directory is test_dbw to match the name of the git repo"
dbw blooop/test_dbw pwd
