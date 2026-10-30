#!/usr/bin/env bash
# cron 入口：扫描 agentusecases.ai 并产出当日 digest
set -euo pipefail
cd /Users/hock/projects/agent-money-miner
exec python3 scan.py
