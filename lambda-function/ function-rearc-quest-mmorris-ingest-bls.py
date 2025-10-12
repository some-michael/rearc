import json
import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import ClientError

# Initialize Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="RearcQuest")  

# Initialize S3 client
s3_client = boto3.client('s3')

# hardcoded values - would not be used in production
bucket_name = 'bucket-rearc-quest-mmorris'

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics

def lambda_handler(event, context):
    # Automatic context injection (request_id, function_name, etc.)
    logger.info("Processing request", extra={"user_id": event.get("userId")})
    
    try:
        # Add custom fields to all subsequent logs
        logger.append_keys(user_id=event.get("userId"))
        
        # Log with different levels
        logger.debug("Validating input parameters")
        logger.info("Starting business logic processing")
        
        # Add custom metrics
        metrics.add_metric(name="ProcessedItems", unit=MetricUnit.Count, value=1)
        
        result = process_business_logic(event)
        
        logger.info("Request processed successfully", 
                   extra={"result_count": len(result)})
        
        return result
        
    except ValueError as e:
        logger.exception("Validation error occurred")
        raise
    except Exception as e:
        logger.exception("Unexpected error occurred")
        raise

@tracer.capture_method
def process_business_logic(event):
    logger.info("Processing business logic")
    
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
        logger.exception("S3 operations error occurred")

        print(f"Error: {e}")

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
