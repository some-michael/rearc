# rearc Quest
#### Author: Michael Morris
##### Date 2025-10-09
## Initial Review and Plan
1. Use this opportunity to learn about AWS data engineering patterns.
     - Let's hope the free credits are sufficient!
    - Alternatives:
        1. Databricks Community

            Upside:

            - fast, easy and self contained
            
            Downside:

            - low compute availability
            - lowers experience with IaC on AWS

        2. Azure

            Upside:

            - quite fast via experience
            - likely cost-effective (due to experience)

            Downside:

            - no additional AWS experience gained

2. Work from the bottom up - i.e. ensure assets comply with the final data pipeline structure and DevOps requirements while developing, not afterwards.

    - Build code that works immediately within Lambda functions.
    - Deploy and schedule Ingest via IaC
    - Add SQS Queue publisher and subscriber
    - Deploy and schedule Ingest+Transform via IaC

3. Use AI (Claude via CoPilot) as in normal production development - as a multiplier not a crutch.

### Unknowns to solve in approximate order
- [X] AWS Free Account
- [X] Local Personal Dev Environment
- [X] Github Copilot Login
- [ ] AWS S3 Bucket
- [ ] AWS Lambda Functions resource
- [ ] AWS Lambda Functions local dev
- [ ] AWS Lambda Functions Spark instance/access
- [ ] AWS IaC
- [ ] AWS SQS Queue resource
- [ ] AWS SQS Queue pub/sub