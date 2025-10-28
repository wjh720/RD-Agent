#!/bin/bash
   # Script to reproduce results

 Foldername="1128_rdagent_fin_quant_aa"
 mkdir -p out_logs/${Foldername} &> /dev/null
 rdagent fin_quant > out_logs/${Foldername}/rdagent_fin_quant.txt 2>&1