# Rearc Quest

**Author:** Michael Morris  
**Date:** 2025-10-09

## Initial Review and Plan

Outlining the goals and approach I would like to take with the Quest.

### 1. Learn AWS Data Engineering Patterns
- Let's hope the free credits are sufficient!

**Alternatives considered:**

#### Databricks Community
**Upside:**
- Fast, easy and self-contained

**Downside:**
- Low compute availability
- Lowers experience with IaC on AWS

#### Azure
**Upside:**
- Quite fast via experience
- Likely cost-effective (due to experience)

**Downside:**
- No additional AWS experience gained

### 2. Requirements-Driven Development
Work from the delivery requirements up - i.e. ensure assets comply with the final data pipeline structure and DevOps requirements while developing, not afterwards.

- Build code that works immediately within Lambda functions
- Deploy and schedule Ingest via IaC
- Add SQS Queue publisher and subscriber
- Deploy and schedule Ingest+Transform via IaC

### 3. AI-Assisted Development
Use AI (Claude via Copilot) as in normal production development - as a multiplier not a crutch.

## Setup Progress

Items to solve in approximate order:

- [x] AWS Free Account
- [x] Local Isolated Dev Environment
- [x] GitHub Copilot Login
- [x] AWS S3 Bucket
- [x] AWS Lambda Functions resource
- [X] AWS Lambda Functions local dev
- [ ] AWS Lambda Functions Spark instance/access
- [X] AWS IaC
- [ ] AWS SQS Queue resource
- [ ] AWS SQS Queue pub/sub

---

## Infrastructure

### Lower Privilege User Group and Account

The login screen reminded me I should examine operating as a non-root user.

**Configuration:**
- **Group:** `rearc-quest`
- **User:** `mmorris-rearc-quest`
- **User tag:** `resource-group:rearc-quest`

### Resource Grouping

I asked Q what the analogy was to Azure Resource Groups and it suggested tags and CloudFormation Stacks. We will start with tags and circle back to the IaC needs shortly (keeping in mind the delivery requirements upward development plan).

> **Note:** Parenthetically, if I had heard that Amazon's LLM Assistant was named Q, I forgot. Shades of Star Trek, I suppose. Or is it James Bond? Have to ask it. [It said "I'm actually named after the Amazon Q service", so I suppose it's named in recursive fashion like GNU.]
### Group Permissions for S3 Bucket

I asked Q: *"I'd like to add the ability to create, manage, read and write to S3 buckets in the tag resource-group:rearc-quest, for the user group rearc-quest"* expecting a quick guide. It seems I blew up the free tier capability, as it failed to return, so I took my prompt over to Claude.

Well, Q came back after I reviewed Claude's response, and seemed to say Claude's approach of managing to tags wouldn't work. It wants to try a naming approach. Putting Claude's version in the Policy editor, sure enough it has errors on the conditionals for tags, so I guess Claude is getting put aside for now.

**Policy file:** [`policies/Bucket-Rearc-Quest.json`](policies/Bucket-Rearc-Quest.json)

### Group Permissions for Lambda Functions

I prompted Q: *"I'd like to add the ability to create, manage, edit, execute Lambda functions tagged with resource-group:rearc-quest for the user group rearc-quest"*. It agreed tag-based restrictions were available for these resources. Interesting difference...

> **Note:** It seems the attached policy limit of 10 means these should be combined, but for now for my own clarity I will maintain them separately.

**Policy file:** [`policies/Lambda-Rearc-Quest.json`](policies/Lambda-Rearc-Quest.json)

### S3 Bucket

Logged in as the reduced privilege user.

**Configuration:**
- **Bucket name:** `bucket-rearc-quest-mmorris`
- **Tag:** `resource-group:rearc-quest`

On creation, an error was given regarding missing the permission `s3:PutEncryptionConfiguration`. The system created the bucket but did not apply encryption settings, and gave a note about how to add the encryption settings once permission was granted. 

> **Note:** I must say, this felt easier to deal with than Azure, which would have puked on creation and likely not supplied the necessary permission to add to solve the condition.

### Lambda Function

Creating a Python lambda function for the initial ingestion from the BLS source. With this created, we will work on the IaC angle to be sure nothing is misconfigured, before proceeding with development.

Well, more permissions fun, an error with lacking `iam:CreateRole`. I took the less permissive route suggested by Q and created a static execution role for the lambda service rather than granting the user the ability to create roles at will.

Then, the user cannot see the roles, missing `iam:ListRoles`. One more update to [`policies/Lambda-Rearc-Quest.json`](policies/Lambda-Rearc-Quest.json) (and remembering to add the required **Tag:** `resource-group:rearc-quest`!), and a function is created. 

> **Note:** The post creation pop-up nicely addresses the next item on the setup list, local development.

## Cloudformation Stack - IaC Setup

Q earlier recommended using CloudFormation stacks. Even though Terraform is more familiar from ARM template development, let's check it out.

Prompt: *Give me a quick guide to setting up infrastructure as code for S3 buckets and Lambda functions, using Cloudformation stacks.*

Well, that gave me some sample CloudFormation template parts, but not really the conceptual overview I was hoping for. Off to the documentation...

After reading about the concepts and reviewing the 'Create your first stack' walkthrough, I will see if I can create the appropriate template for these two resources by modifying the samples Q gave me.

**Cloudformation template file:** [`cloudformation/rearc-quest-template.yml`](cloudformation/rearc-quest-template.yml)

I assume you can export templates similar to exporting an ARM template in the Azure Portal. Q pointed me to the IaC generator. Following that, I exported the template and also imported it into a stack, which showed no changes, just the import operation.

I see that the Lambda function code can be embedded in the Cloudformation template. Interesting. Presumably there is a better way to do it, but I will save doing that for a bit later on. 

After some merging of the exported template into Q's initial template suggestion, the stack successfully imported. The exported template failed to import due to missing parameter values in the Lambda function. The exported template apparently pulls code zips from an S3 bucket - something I may want to come back and do, but not right now.

**Configuration:**
- **Stack name:** `stack-rearc-quest-mmorris`
- **Tag:** `resource-group:rearc-quest`

> **Production Note:** I see in the docs where Cloudformation templates can be stored in and synced from GitHub, setting this up plus CI/CD (to dev, gated to stage and prod after QA) would be my typical recommendation.

## Part 1 Approach

I assume there are frameworks for robust Lambda function data extraction/ingest that are nearly plug and play, once you know the framework.  Instead of learning one of those or having Q/Claude build it, let's approach this from first principles, in keeping with the goal #1 to learn AWS data engineering patterns.

> **Production Note:** Obviously we could go with Airflow or another heavier approach but that seems to be more than required/requested here. For prodution use I would recommend something like this to handle future expansion capability, maintainability for client teams, robustness in observability, in all but the most specialized of bespoke needs.

### Part 1 Development Outline:

0. Setup testable operation of the Lambda function.
1. Connect to S3 destination, write a test file.
2. Connect to source, list available files.
3. Perform file ingest and write (probably ignoring resumability, intermediate caching, etc), for smaller files to avoid the rate limiting mentioned in the docs.
4. Add rate limiting protection and copy bigger files.
5. Add file property comparison for changed-file-only add/replace/delete operations.
6. Re-incorporate into IaC framework.
7. Add daily trigger (in IaC?)

#### 0. Lambda function testing

The built in Test function looks promising but does not fit directly into the local development approach. Taking a look at the local environment configuration requirements, it's probably prudent to stick to the console development and testing experience for this project. Especially looking forward to building the Spark based dataframe transformations.

> **Note:** I saw a permissions error regarding codwhisperer in the Lambda function interface so I went to add a policy allowance for my reduced privilege user. Then I ran into the 5120 byte inline policy limitation. Converting everything to managed policies. Setting up reduced privilege users has definitely been an eye opening but time consuming endeavor! 

I also want to be able to easily view logs, so I added Lambda Powertools after asking Q about methods to get log outputs. Working in the Code source console editor is getting a bit annoying, what with having to deploy changes to test, and with the nested scrollbars. I might wind up going to local development sooner than I thought.

#### 1. Add S3 ~~destination~~ output

Looks like AWS lingo uses 'destination' as a streaming/message/queue output handler. This will be useful when getting to part 4's SQS queue I think.

- [ ] Add lambda function destination for SQS queue

Q prompt: *What do I need to add to a lambda function to connect to an S3 bucket*

> **AI Note:** I am treating Q like we used to treat StackOverflow, in other words I would have typically looked for example Python code that makes the connection, then looked at the documentation for the objects to add status codes extraction. Fortunately it can find and generate code snippets for the status code syntax much faster than I can search and read. (You just have to test and make sure it isn't halucinating! Test early and often - don't let it write 1000 lines like Claude always wants to.) This is consistent with the goal of using AI as a multiplier not a crutch.

I added an S3 SDK example function call to list files in the bucket and write a test file. It required another permission on the lambda role, similar to using user managed identity in Azure. I am not sure yet if I should be including the permissions in the Cloudformation stack, or if environment variables with keys would be a better solution (do keys exist in S3?)

- [ ] Examine adding permissions to the lambda execution role via Cloudformation template. Maybe have to put the role itself in the stack?

> **Production Note:** I have the bucket name hard coded at the moment in the function. This is obviously not production ready. I would use environment variables, a metadata database source, or possibly send the value in the trigger event (would need to solve security concern in this case of course). It doesn't seem instructive to solve at this stage however.

#### 2. Connect to BLS Source

I immediately considered using Beautiful Soup for the BLS file download portion. However, I suspect it could be too heavy for a simple file index. In the Linux shell I probably have used wget to list the files and their properties, so perhaps there is something like that for Python.

Q prompt *Is there a python library easily available in Lambda functions that can get a list of files from a simple Apache directory structure index, along with their properties, similar to wget on Linux?*

From this suggestion I chose urllib3 as it is available without adding additional dependencies. I added the User-Agent header and got the html_content response from a test. 

#### 3. Parse BLS source file list

For speed, I then asked Q to create a parsing regex. This wouldn't be the most robust approach but should suffice here. (I am thankful for not needing to hand write regex anymore!)

Claude prompt *What regex can I use to parse this html_content into a list of files, with their urls and last modified times?* (included raw html output from urllib http.request().data.decode())

> **Note**: Around here Q started slowing down quite a bit, presumably the Free Tier was running out or being otherwise heavily used. That's ok, its pretty much Pythonic from here.

#### 4. Write BLS files to S3 Bucket

Now I just needed to combine the file list with the S3 upload already proven out. I wrote a simple iterator over the list of file dicts already parsed.

> **Production Note: At this stage I decided to cut out incremental comparisons and start moving faster through the quest. It would, however, be best to store the last modified dates of the files on the BLS source, and compare them to the current dates from the daily execution. Perhaps there is a way to fake up dates on S3 buckets, like `touch` in *nix, so that a database or other store is not needed?

#### 5. Establish Sync Operation

Once the upload tested successfully, I just need to delete the output destination folder prior to performing the upload. Since there is no hierarchical namespace in S3 buckets, it looks like objects to be deleted must be discovered by prefix (a la blob storage). I decided in the interest of time to prompt this task to Claude:

Claude prompt: *Write a Python function using the boto3 s3_client that can delete all the files in a given bucket with a given folder prefix.*

After adding and testing the file deletion function, its time to add a trigger and combine the code with the IaC template.

#### 6. Add daily execution trigger

Again working to speed up, gave Claude the prompt: *What do I add to an AWS Cloudformation template to include a daily execution trigger for a Lambda function?* 

I chose the direct approach in the YAML template because I am still working toward the Part 4 automation, and know I can execute a stack change set to deploy it.

#### 7. Lambda function CloudFormation template update

I pasted the updated Lambda function code into the template as well (Again knowing this is a non-production operation for development speed.)

> **Note**: At this point I started getting failures on permissions on deploying the stack updates. Attempting to allow the Lambda Powertools layer was triggering a permissions error, even when running as the root user. Removed the logging from the template version of the Lambda function in order to keep going. I had to execute the stack as the root user to avoid another 'events' schema permissions error as well.

I also ran into an issue with the Code: Zipfile syntax appearing to upload the file as 'index.py' despite having  `Handler: "lambda_function.lambda_handler"` defined in the template. Probably there is some ticky problem I am missing here, so I fixed it in the console.

## Part 2 Approach

