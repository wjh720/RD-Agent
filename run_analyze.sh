#!/bin/bash
   # Script to reproduce results

 Foldername="1128_analyze_aa"
 mkdir -p out_logs/${Foldername} &> /dev/null
 python -m analyze.py >& out_logs/${Foldername}/analyze.txt