#!/bin/bash
   # Script to reproduce results

 Foldername="1134_rdagent_fin_quant_load_aa"
 mkdir -p out_logs/${Foldername} &> /dev/null
 RICH_NO_COLOR=1 PYTHONUNBUFFERED=1 rdagent fin_quant --path log/2025-10-28_10-33-07-398267/__session__/2/3_feedback --loop-n 10 >>out_logs/${Foldername}/rdagent_fin_quant_load.txt 2>&1