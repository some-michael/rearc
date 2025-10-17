# Rearc Quest - Deliverables

**Author:** Michael Morris  
**Date:** 2025-10-16

This document is a short index to the output files for the Quest. The long form exploration and explaination is found in the README.md.

**README:** [`README.md`](README.md)

### Q. What do I have to submit?
1. Link to data in S3 and source code (Step 1)
2. Source code (Step 2)
3. Source code in .ipynb file format and results (Step 3)
4. Source code of the data pipeline infrastructure (Step 4)
5. Any README or documentation you feel would help us navigate your quest.

## 1. S3 data and Source Code (Step 1)
Python code for Lamda function:
**Lambda function python code:** [`lambda-function/function-rearc-quest-mmorris-ingest.py`](lambda-function/function-rearc-quest-mmorris-ingest.py)

Output to S3 bucket:
**BLS Data Bucket:** [`https://bucket-rearc-quest-mmorris.s3.us-east-2.amazonaws.com/bls_data/'](https://bucket-rearc-quest-mmorris.s3.us-east-2.amazonaws.com/bls_data/)

## 2. Source Code (Step 2)

Also contained in the same Lambda function code: 
**Lambda function python code:** [`lambda-function/function-rearc-quest-mmorris-ingest.py`](lambda-function/function-rearc-quest-mmorris-ingest.py)

Output to S3 bucket:
**DataUSA Data Bucket:** [`https://bucket-rearc-quest-mmorris.s3.us-east-2.amazonaws.com/datausa_data/'](https://bucket-rearc-quest-mmorris.s3.us-east-2.amazonaws.com/datausa_data/)

## 3. Source code (.ipynb) and results (Step 3)

**Jupyter Data Analysis Notebook:** [`jupyter-notebook/notebook-rearc-quest-mmorris.ipynb`](jupyter-notebook/notebook-rearc-quest-mmorris.ipynb)

Results are given in the /reports folder in this code tree:

**Req 0 BLS Data:** [`reports/part_3_req_0_bls_data.csv`](reports/part_3_req_0_bls_data.csv)

**Req 0 DataUSA Data:** [`reports/part_3_req_0_datausa_data.csv`](reports/part_3_req_0_datausa_data.csv)

**Req 1 Population Statistics:** [`reports/part_3_req_1_population_statistics.csv`](reports/part_3_req_1_population_statistics.csv)

**Req 2 Best Years:** [`reports/part_3_req_2_best_years.csv`](reports/part_3_req_2_best_years.csv)

**Req 3 First Quarter Combined Stats:** [`reports/part_3_req_3_first_qtr_combined.csv`])(reports/part_3_req_3_first_qtr_combined.csv)

**Req 3 First Quarter Combined Stats Chart:** [`reports/part_3_req_3_labor_population_chart_PRS30006032_Q01.jpg`])(reports/part_3_req_3_labor_population_chart_PRS30006032_Q01.jpg)

## 4. Source code for data pipeline IaC (Step 3)

> **Note**: This template covers Parts 0 and 1, the missing parts 2 and 3 are outlined at the end of the README.md.

**CloudFormation template file:** [`cloudformation/rearc-quest-template.yml`](cloudformation/rearc-quest-template.yml) 

