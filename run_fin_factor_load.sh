#!/bin/bash
   # Script to reproduce results

 Foldername="1141_rdagent_fin_factor_load_aa"
 mkdir -p out_logs/${Foldername} &> /dev/null
 RICH_NO_COLOR=1 PYTHONUNBUFFERED=1 rdagent fin_factor --path log/2025-10-29_01-12-54-858255/__session__/17/3_feedback --loop-n 50 >>out_logs/${Foldername}/rdagent_fin_factor_load.txt 2>&1