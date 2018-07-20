import re
import os
import boto3
import json
import youtube_dl
from youtube_dl.utils import UnsupportedError
from boto3.exceptions import S3UploadFailedError

os.environ['PATH'] = os.environ['PATH'] + ':/var/task' # so ffmpeg is in path
s3 = boto3.client('s3')

def strip_reddit_id(url):
    """
    strips id from reddit url
    supports either full link or short link:
    full link -> https://www.reddit.com/r/bjj/comments/84c4kv/guikoji/
    short link ->https://redd.it/84c4kv (short link)
    """
    pattern = r'.*(?:comments)?\/(\w{6})(?:\/|$)'
    matchObj = re.match(pattern, url)
    if matchObj != None:
        return matchObj.groups()[0]

def s3_key_to_link(region, bucket, key):
    """generates public link of s3 object"""
    return "https://s3-{0}.amazonaws.com/{1}/{2}".format(
        region,
        bucket,
        key)

def s3_key_exists(bucket, key):
    """return true if the key exists in bucket"""
    response = s3.list_objects_v2(
        Bucket=bucket,
        Prefix=key,
    )
    for obj in response.get('Contents', []):
        if obj['Key'] == key:
            return True

def lambda_response(code, body):
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*', 
            'Access-Control-Allow-Credentials': True
        },
        'body': json.dumps(body)
    }

def main(event, context):
    bucket = os.getenv('AWS_BUCKET', 'reddit-hosted-videos')
    region = os.getenv('AWS_REGION', 'eu-central-1')

    url = event['queryStringParameters'].get('url', None)
    if url == None:
        return lambda_response(400, {'error': 'url is missing'})
    print('request received: {}'.format(url))

    id = strip_reddit_id(url)
    if id == None:
        return lambda_response(400, {'error': 'url is invalid'})
    print('id stripped: {}'.format(id))
    
    key = '{}.mp4'.format(id)
    if s3_key_exists(bucket, key):
        print('video already exists in s3')
        link = s3_key_to_link(region, bucket, key)
        return lambda_response(200, {'link': link})
    
    filename = '/tmp/' + key
    try:
        ydl = youtube_dl.YoutubeDL({
            'outtmpl': filename, 
            'format': 'bestvideo[filesize<100M,ext=mp4]+bestaudio/best[filesize<100M]/best'}
        )
        with ydl:
            ydl.download([url])
    except UnsupportedError:
        return lambda_response(400, {'error': 'url is invalid'})
    except Exception as e:
        print('error while downloading: {}'.format(e))
        return lambda_response(500, {})

    try:
        print('uploading to s3...')
        s3.upload_file(filename, bucket, key, ExtraArgs={'ACL':'public-read'})
    except S3UploadFailedError as e:
        print('upload failed: {}'.format(e))
        return lambda_response(500, {})
    print('upload complete')

    return lambda_response(200, {'link': s3_key_to_link(region, bucket, key)})

if __name__ == "__main__":
    main({'queryStringParameters': {
        'url': 'https://www.reddit.com/r/WTF/comments/904nw6/isssssss_that_a_snake/'
    },'body': ''}, '')