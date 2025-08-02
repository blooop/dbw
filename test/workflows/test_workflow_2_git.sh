#!/usr/bin/env bash
set -e
cd /tmp


echo "Running: dbw blooop/test_dbw and confirming the git status works as expected"
dbw blooop/test_dbw git status
