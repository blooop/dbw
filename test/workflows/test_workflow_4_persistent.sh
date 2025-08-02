#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/dbw launch

echo "Running: dbw launch blooop/test_dbw launch touch persistent.txt to confirm that persistent files work as expected"
dbw launch blooop/test_dbw launch touch persistent.txt

echo "Running: dbw launch blooop/test_dbw launch ls to confirm that persistent files are present"
dbw launch blooop/test_dbw launch ls