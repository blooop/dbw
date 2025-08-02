#!/usr/bin/env bash
set -e
cd /tmp


echo "Running: dbw launch blooop/test_dbw launch and confirming the git status works as expected"
dbw launch blooop/test_dbw launch git status
