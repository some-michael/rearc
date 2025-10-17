"""
AWS Lambda Function: Rearc Quest Data Ingestion

This Lambda function ingests data from two sources:
1. Bureau of Labor Statistics (BLS) - https://download.bls.gov/pub/time.series/pr/
2. DataUSA API (Census Buerea) - https://datausa.io/about/api/

The function downloads files from these sources and stores them in designated
S3 bucket directories, replacing existing files to ensure data synchronization.

Author: Michael Morris
Email: michaelmorris+rearc@gmail.com
Created: 2025-10-14
Runtime: Python 3.13

Dependencies:
- Standard AWS Lambda environment libraries
    - boto3 (AWS SDK)
    - urllib3 (HTTP client)
    - Standard library: json, re, datetime
- No Layers or external packages required

Execution:
- Manual invocation via AWS Console/CLI
- Scheduled execution via EventBridge (daily)

Environment Variables: None (uses hardcoded values for simplicity)

"""

import json
import boto3
import urllib3
import re
from botocore.exceptions import ClientError
from urllib.parse import urlparse

##### BEGIN hardcoded values - would not be used in production
bucket_name = 'bucket-rearc-quest-mmorris'

# BLS Source - https://download.bls.gov/pub/time.series/pr/
bls_bucket_directory = 'bls_data' # for simplicity, the contents of this directory will be deleted to ensure synchronization from the BLS source on each run
bls_url="https://download.bls.gov/pub/time.series/pr/"

# DataUSA Source - https://datausa.io/api/data?drilldowns=Nation&measures=Population
datausa_bucket_directory = 'datausa_data' # this location will be overwritten on each execution
datausa_filename = 'datausa_acs_yg_total_population_1.json' # static filename for the single file we are downloading
datausa_url="https://honolulu-api.datausa.io/tesseract/data"
datausa_api_call = ".jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population" # as taken from the Quest

# User Agent string with contact to satisfy BLS requirements
# https://www.bls.gov/bls/requests-for-data.htm#policies
# Should typically be constructed dynamically
user_agent="AWS-Lambda-DirectoryParser/1.0 (urllib3; Python/3.13; michaelmorris+bls@gmail.com)"

###### END hardcoded values

# Initialize S3 client
s3_client = boto3.client('s3')

# Initialize HTTP client
http = urllib3.PoolManager()

# get base url of BLS - this is a bit of an oversimplification due to not handling possible roots other than /
parsed_bls = urlparse(bls_url)
bls_base = f"{parsed_bls.scheme}://{parsed_bls.netloc}"

# set headers for BLS requests
# hardcoded values are not production ready - would use environment variables or metadata database in production
headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Cache-Control': 'no-cache'
    }

def get_directory(url, headers):
    """
    List contents of the passed directory (http path) and return the HTML content.
    
    Args:
        url (str): The URL of the directory to list.
        headers (dict): HTTP headers to include in the request.
    """

    try:
        response = http.request('GET', url, headers=headers)
        status_code = response.status
        html_content = response.data.decode('utf-8')

        return html_content

    except Exception as e:
        raise

def get_file_by_url(url, headers):
    """
    Get a single file by its url and return the HTTP response object.
    Assumes the URL indicates a binary file.

    Args:
        url (str): The URL of the file to download.
        headers (dict): HTTP headers to include in the request.
    """

    try:
        response = http.request('GET', url, headers=headers)
        return response
    
    except Exception as e:
        raise

def parse_html_content(html_content):
    """
    Parse specifically the BLS Apache directory structure HTML content to extract file details. 
    Returns a list of dictionaries with keys: filename, url, last_modified, size.

    Args:
        html_content (str): The HTML content of the directory listing.    
    """
    pattern = r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)\s+(\d+)\s+<A HREF="([^"]+)">([^<]+)</A>'

    return [
        {
            'filename': match[3],
            'url': f"{bls_base}{match[2]}",
            'last_modified': match[0],
            'size': int(match[1])
        }
        for match in re.findall(pattern, html_content)
    ]

def copy_http_files_to_s3(bucket, directory, headers, parsed_file_list):
    """
    Copy files from HTTP URLs to the specified S3 bucket and directory. Returns a list of dictionaries with keys: filename, status (HTTP status code from S3 put_object).
    First the directory is cleaned of existing files.
    Each file is individually fetched and uploaded to S3. This is likely non-performant for large files or many files.
    A production solution would likely use a robust, parallelized ETL tool or library.

    Args:
        bucket (str): The name of the S3 bucket.
        directory (str): The S3 directory (prefix) to copy files into. ALL OBJECTS WITH THIS PREFIX WILL BE DELETED FIRST.
        headers (dict): HTTP headers to include in the requests.
        parsed_file_list (list): List of dictionaries with file details (filename, url, last_modified, size).
    """

    # Clean the output directory first for synchronization
    deleted_count = delete_s3_folder(bucket, f"{directory}/")

    try:
        output_list = []

        for file in parsed_file_list:
            file_copied = {}
            file_response = get_file_by_url(file["url"], headers)

            response = s3_client.put_object(
                Bucket=bucket,
                Key=f'{directory}/{file["filename"]}',
                Body=file_response.data,
                ContentType=file_response.headers.get('content-type', 'application/octet-stream')
            )

            file_copied["filename"] = file["filename"]
            file_copied["status"] = response['ResponseMetadata']['HTTPStatusCode']

            output_list.append(file_copied)
    
        return output_list
    
    except ClientError as e:
        return []  # Return empty list instead of None
        raise

def delete_s3_folder(bucket, folder_prefix):
    """
    Delete all objects in an S3 'folder' (prefix). Returns the count of deleted objects.
    
    Args:
        bucket (str): The name of the S3 bucket.
        folder_prefix (str): The S3 folder prefix to delete.
    """
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=folder_prefix
        )
        
        if 'Contents' not in response:
            return 0
        
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        
        if objects_to_delete:
            delete_response = s3_client.delete_objects(
                Bucket=bucket,
                Delete={
                    'Objects': objects_to_delete,
                    'Quiet': False
                }
            )
            
            deleted_count = len(delete_response.get('Deleted', []))
            
            return deleted_count
            
    except ClientError as e:
        raise

def lambda_handler(event, context):
    """
    Main Lambda handler function. Orchestrates the data ingestion process.
    Business Logic:
    1. Construct a placeholder file list for the DataUSA API call.
    2. Fetch and parse the BLS directory listing.
    3. Copy files from both sources to their respective S3 directories.
    4. Return a summary of the operation in the HTTP response.

    """

    # hardcoding a single file instance for the DataUSA API call
    # This is sidejacking the API call into the same processing function as the BLS files for simplicity
    datausa_file = [{
        'filename': datausa_filename,
        'url': f"{datausa_url}{datausa_api_call}",
        'last_modified': __import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'size': None
    }]
    
    try:
        
        file_list = get_directory(bls_url, headers)

        parsed_file_list = parse_html_content(file_list)
        
        copied_file_list = copy_http_files_to_s3(bucket_name, bls_bucket_directory, headers, parsed_file_list)

        copied_file_list += copy_http_files_to_s3(bucket_name, datausa_bucket_directory, headers, datausa_file)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Data ingestion completed successfully, files copied={len(copied_file_list)}',
                'copied_file_list': copied_file_list,
                'trigger_source': event.get("source", "manual")
            })
        }

    except Exception as e:
        raise
