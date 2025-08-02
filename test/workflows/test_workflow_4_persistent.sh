#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/dbw

echo "Running: dbw blooop/test_dbw touch persistent.txt to confirm that persistent files work as expected"
dbw blooop/test_dbw touch persistent.txt

echo "Running: dbw blooop/test_dbw ls to confirm that persistent files are present"
dbw blooop/test_dbw ls