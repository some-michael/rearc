import json
import boto3
import urllib3
import re
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import ClientError
from urllib.parse import urlparse

# Initialize Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="RearcQuest")  

# Initialize S3 client
s3_client = boto3.client('s3')

# Initialize HTTP client
http = urllib3.PoolManager()

# hardcoded values - would not be used in production
bucket_name = 'bucket-rearc-quest-mmorris'
bucket_directory = 'output' # for simplicity, this directory will be deleted to ensure synchronization from the BLS source on each run
user_agent="AWS-Lambda-DirectoryParser/1.0 (urllib3; Python/3.13; michaelmorris+bls@gmail.com)"
bls_url="https://download.bls.gov/pub/time.series/pr/"


# get base url of BLS - this is a bit of an oversimplification due to not handling possible roots other than /
parsed_bls = urlparse(bls_url)
bls_base = f"{parsed_bls.scheme}://{parsed_bls.netloc}"

# set headers for BLS requests
headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Cache-Control': 'no-cache'
    }

@tracer.capture_method
def get_directory(url, headers):
    """
    List contents of the passed directory. 
    """

    logger.info("Starting get_directory()")

    try:
        response = http.request('GET', url, headers=headers)
        status_code = response.status
        html_content = response.data.decode('utf-8')

        return html_content
    
    except NameError as e:
        raise Exception(f"NameError occurred: {str(e)}")

    except Exception as e:
        logger.exception(f"HTTP get_directory() operations error occurred: {str(e)}")

        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        http_status = e.response['ResponseMetadata']['HTTPStatusCode']

        return {
            'statusCode': http_status, #500
            'body': json.dumps({
                'error': str(e)
            })
        }

@tracer.capture_method
def get_file_by_url(url, headers):
    """
    Get a single file by its url.
    Production note: Probably better to merge this as an alternative operation with get_directory to reduce code duplication.
    """

    logger.info("Starting get_file_by_url()")

    try:
        response = http.request('GET', url, headers=headers)

        return response
    
    except NameError as e:
        raise Exception(f"NameError occurred: {str(e)}")

    except Exception as e:
        logger.exception(f"HTTP get_directory() operations error occurred: {str(e)}")

        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        http_status = e.response['ResponseMetadata']['HTTPStatusCode']

        return {
            'statusCode': http_status, #500
            'body': json.dumps({
                'error': str(e)
            })
        }

@tracer.capture_method
def parse_html_content(html_content):
    """ Parse specifically the BLS Apache directory structure and return a list of dicts:
        [
        {
            'name': 'filename.txt',           # File/directory name from the link text
            'href': 'filename.txt',           # Relative URL from href attribute
            'last_modified': '2024-01-15 10:30',  # Date string from the listing
            'size': '1234567',                   # Size string from the listing
            'description': 'Text file'        # Description (if present)
        },...
        ]
    """
    # hat tip to Claude for building this regex
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

@tracer.capture_method
def copy_http_files_to_s3(bucket, directory, headers, parsed_file_list):
    logger.info("Starting copy_http_files_to_s3()")

    # Clean the output directory first for synchronization
    deleted_count = delete_s3_folder(bucket, f"{directory}/")
    logger.info(f"Deleted {deleted_count} existing files from {directory}/")

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
            logger.debug(response['ResponseMetadata'])

            file_copied["filename"] = file["filename"]
            file_copied["status"] = response['ResponseMetadata']['HTTPStatusCode']

            output_list.append(file_copied)
    
        return output_list
    
    except ClientError as e:
        logger.exception(f"S3 operations error occurred: {str(e)}")

        # Access error response metadata
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        http_status = e.response['ResponseMetadata']['HTTPStatusCode']

        return {
            'statusCode': http_status, #500
            'body': json.dumps({
                'error': str(e)
            })
        }

@tracer.capture_method
def delete_s3_folder(bucket, folder_prefix):
    """
    Delete all objects in an S3 'folder' (prefix).
    
    Args:
        bucket (str): Name of the S3 bucket
        folder_prefix (str): Folder prefix to delete (e.g., 'output/' or 'data/2024/')
    """
    try:
        # List all objects with the prefix
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=folder_prefix
        )
        
        # Check if any objects exist
        if 'Contents' not in response:
            logger.info(f"No objects found with prefix: {folder_prefix}")
            return
        
        # Prepare objects for deletion
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        
        # Delete objects in batches (max 1000 per batch)
        if objects_to_delete:
            delete_response = s3_client.delete_objects(
                Bucket=bucket,
                Delete={
                    'Objects': objects_to_delete,
                    'Quiet': False  # Set to True to reduce response size
                }
            )
            
            deleted_count = len(delete_response.get('Deleted', []))
            logger.info(f"Successfully deleted {deleted_count} objects from {folder_prefix}")
            
            return deleted_count
            
    except ClientError as e:
        logger.exception(f"Error deleting S3 folder {folder_prefix}: {str(e)}")
        raise

@tracer.capture_method
def check_s3_bucket():
    logger.info("Starting S3 Bucket Check")
    
    try:
        # Example 1: List objects in bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        objects = response.get('Contents', [])
        status_code_list = response['ResponseMetadata']['HTTPStatusCode']
        logger.debug(response['ResponseMetadata'])
        
        # Example 2: Read an object
        obj_key = 'output/result.txt'
        response = s3_client.get_object(Bucket=bucket_name, Key=obj_key)
        file_content = response['Body'].read().decode('utf-8')
        status_code_get = response['ResponseMetadata']['HTTPStatusCode']
        logger.debug(response['ResponseMetadata'])

        # Example 3: Write an object
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key='output/result.txt',
            Body='Hello from Lambda!',
            ContentType='text/plain'
        )
        status_code_put = response['ResponseMetadata']['HTTPStatusCode']
        logger.debug(response['ResponseMetadata'])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'S3 operations completed with list status: {status_code_list}, get status: {status_code_get}, put status: {status_code_put}',
                'objects_count': len(objects),
                'file_content': file_content[:100]  # First 100 chars
            })
        }
        
    except ClientError as e:
        logger.exception(f"S3 operations error occurred: {str(e)}")

        # Access error response metadata
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        http_status = e.response['ResponseMetadata']['HTTPStatusCode']

        return {
            'statusCode': http_status, #500
            'body': json.dumps({
                'error': str(e)
            })
        }
        
# Lambda Powertools decorators
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event, context):
    # Automatic context injection (request_id, function_name, etc.)
    logger.info("Processing request", extra={"user_id": event.get("userId")})
    
    try:
        # Add custom fields to all subsequent logs
        logger.append_keys(user_id=event.get("userId"))
        
        # result = check_s3_bucket()

        file_list = get_directory(bls_url, headers)

        parsed_file_list = parse_html_content(file_list)
        
        logger.info("parse_html_content() processed successfully", 
                   extra={"result_count": len(parsed_file_list)})

        metrics.add_metric(name="ProcessedItems", unit=MetricUnit.Count, value=len(parsed_file_list))

        copied_file_list = copy_http_files_to_s3(bucket_name, bucket_directory, headers, parsed_file_list)

        logger.info("copy_http_files_to_s3() processed successfully")

        metrics.add_metric(name="FilesCopied", unit=MetricUnit.Count, value=len(copied_file_list))

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'copy_http_files_to_s3() operations completed, files copied={len(copied_file_list)}',
                'copied_file_list': copied_file_list
            })
        }
        
    except NameError as e:
        logger.exception("Name error occurred")
        raise
    except ValueError as e:
        logger.exception("Validation error occurred")
        raise
    except Exception as e:
        logger.exception("Unexpected error occurred")
        raise