'''
    LF1: Triggered by S3 bucket whenever a new image is uploaded
'''

from botocore.vendored import requests

import boto3
import datetime
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def try_ex(func):
    try:
        return func()
    except KeyError:
        return None

def get_photo_labels(bucket, photo):
    client=boto3.client('rekognition')
    response = client.detect_labels(Image={'S3Object':{'Bucket': bucket, 'Name': photo}}, MaxLabels=10)
    labels = try_ex(lambda: response['Labels'])
    all_labels = [l['Name'] for l in labels]
    return all_labels

def put_to_es(index, type, new_doc):
    endpoint = 'https://vpc-nyu-hw3-qjxhglnxwxfchoep2ylzrohydq.us-east-1.es.amazonaws.com/{}/{}'.format(index, type)
    headers = {'Content-Type': 'application/json'}
    r = requests.post(endpoint, data=new_doc, headers=headers)
    print(r.content)

def lambda_handler(event, context):
    logger.debug('Test LF invoked by S3')
    logger.debug(event)

    # Extract new img from the S3 event
    s3obj = try_ex(lambda: event['Records'])
    if not s3obj:
        return {
        'statusCode': 500,
        'errorMsg': 'Event message does not follow S3 JSON structure ver 2.1'
    }

    for obj in s3obj:
        bucket = try_ex(lambda: obj['s3']['bucket']['name'])
        photo = try_ex(lambda: obj['s3']['object']['key'])

        # Get all labels
        logger.debug('Getting label for  %s::%s' % (bucket, photo))
        labels = get_photo_labels(bucket, photo)
        logger.debug('Labels for %s::%s are %s' % (bucket, photo, labels))

        # Index the photo
        doc = {
            'objectKey': photo,
            'bucket': bucket,
            'createdTimestamp': datetime.datetime.now().strftime('%Y-%d-%m-T%H:%M:%S'),
            'labels': labels
        }
        put_to_es('photos', 'photo', json.dumps(doc))

    return {
        'statusCode': 200,
        'body': doc

    }