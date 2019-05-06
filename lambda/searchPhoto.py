'''
    LF2: Lambda proxy for API gateway to search photos based on user query
'''

import json
import datetime
import time
import os
import dateutil.parser
import logging
import boto3

from botocore.vendored import requests

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# For safe slot extraction
def try_ex(func):
    try:
        return func()
    except KeyError:
        return None

def lambda_handler(event, context):
    logger.debug(event)

    raw_query = try_ex(lambda: event['queryStringParameters']['query'])
    if not raw_query:
        return {
            'statusCode': 400,
            'body': 'No query found in event'
        }

    # Use Lex to disambiguate query
    keywords = []
    client = boto3.client('lex-runtime')
    response = client.post_text(
        botName = 'AnnexBot',
        botAlias = '$LATEST',
        userId = 'searchPhotosLambda',
        inputText = raw_query
    )

    slots = try_ex(lambda: response['slots'])
    for _, v in slots.items():
        if v: # ignore empty slots
            keywords.append(v)

    # Query Elasticsearch
    # query = 'https://vpc-nyu-hw3-qjxhglnxwxfchoep2ylzrohydq.us-east-1.es.amazonaws.com/photos/_search?pretty=true&q=*:*'
    # r = requests.get(query)
    # data = json.loads(r.content.decode('utf-8'))
    query = 'https://vpc-nyu-hw3-qjxhglnxwxfchoep2ylzrohydq.us-east-1.es.amazonaws.com/photos/_search'
    headers = {'Content-Type': 'application/json'}
    prepared_q = []
    for k in keywords:
        prepared_q.append({"match": {"labels": k}})
    q = {"query": {"bool": {"should": prepared_q}}}
    r = requests.post(query, headers=headers, data=json.dumps(q))
    data = json.loads(r.content.decode('utf-8'))

    # Extract images
    all_photos = []
    prepend_url = 'https://s3.amazonaws.com'
    hits = try_ex(lambda: data['hits']['hits'])
    for h in hits:
        photo = {}
        obj_bucket = try_ex(lambda: h['_source']['bucket'])
        obj_key = try_ex(lambda: h['_source']['objectKey'])
        full_photo_path = '/'.join([prepend_url, obj_bucket, obj_key])
        photo['url'] = full_photo_path
        photo['labels'] = try_ex(lambda: h['_source']['labels'])
        all_photos.append(photo)

    return {
        'statusCode': 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        'body': json.dumps({'results': all_photos})
    }