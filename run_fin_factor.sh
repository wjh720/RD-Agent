#!/bin/bash
   # Script to reproduce results

 Foldername="1134_rdagent_fin_factor_aa"
 mkdir -p out_logs/${Foldername} &> /dev/null
 RICH_NO_COLOR=1 PYTHONUNBUFFERED=1 rdagent fin_factor --loop-n 1 >>out_logs/${Foldername}/rdagent_fin_quant.txt 2>&1