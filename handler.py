import re
import os
import string
import boto3
import json
import youtube_dl
import requests
from youtube_dl.utils import UnsupportedError
from boto3.exceptions import S3UploadFailedError

os.environ['PATH'] = os.environ['PATH'] + ':/var/task' # for ffmpeg
s3 = boto3.client('s3')

def get_media_title(id):
    """
    returns title of media in reddit post identified by id
    title is in a file & S3 friendly format
    if no title present, returns empty string
    """
    try:
        j = requests.get('https://www.reddit.com/comments/{}.json'.format(id),
            headers={'User-Agent': 'Mozilla/5.0'}).json()
        title = j[0]['data']['children'][0]['data']['title']
        title = title.replace(' ', '-')
        valid_chars = "-_.()%s%s" % (string.ascii_letters, string.digits)
        return ''.join(c for c in title if c in valid_chars)
    except:
        return ''

def strip_reddit_id(url):
    """
    strips id from reddit url
    supports either full or short link:
      - https://www.reddit.com/r/bjj/comments/84c4kv/guikoji/
      - https://redd.it/84c4kv
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
        'statusCode': code,
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
    print('request received:', url)

    id = strip_reddit_id(url)
    if id == None:
        return lambda_response(400, {'error': 'url is invalid'})
    print('id stripped:', id)

    key = '{0}_{1}.mp4'.format(get_media_title(id), id)
    if s3_key_exists(bucket, key):
        link = s3_key_to_link(region, bucket, key)
        return lambda_response(200, {'link': link})
    
    f = '/tmp/' + key
    try:
        ydl = youtube_dl.YoutubeDL({
            'outtmpl': f, 
            'format': 'bestvideo[filesize<100M,ext=mp4]+bestaudio/best[filesize<100M]/best'}
        )
        with ydl:
            ydl.download([url])
    except UnsupportedError:
        return lambda_response(400, {'error': 'url is invalid'})
    except Exception as e:
        print('error while downloading:', e)
        return lambda_response(500, {})

    try:
        print('uploading to s3...')
        s3.upload_file(f, bucket, key, ExtraArgs={'ACL':'public-read'})
    except S3UploadFailedError as e:
        print('upload failed:', e)
        return lambda_response(500, {})

    link = s3_key_to_link(region, bucket, key)
    print('upload complete:', link)
    return lambda_response(200, {'link': link})

if __name__ == "__main__":
    main({'queryStringParameters': {
        'url': 'https://www.reddit.com/r/WTF/comments/90q99g/airplane_trying_to_lift_flight_on_a_street/'
    },'body': ''}, '')