import boto3, json, os
ak = os.environ.get('NCP_ACCESS_KEY', '')
sk = os.environ.get('NCP_SECRET_KEY', '')
print(f"Using access key: {ak[:15]}...")
# Try multiple NCP endpoints
for endpoint in [
    'https://kr.object.ncloudstorage.com',
    'https://kr.objectstorage.ncloud.com',
    'https://objectstorage.kr-gov.ncloud.com',
]:
    print(f"Trying endpoint: {endpoint}")
    s3 = boto3.client('s3',
        endpoint_url=endpoint,
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        region_name='kr-standard')
    try:
        s3.list_objects_v2(Bucket='marketgate-auth', MaxKeys=1)
        print(f"  SUCCESS with {endpoint}")
        break
    except Exception as e:
        print(f"  FAILED: {e}")
s3.put_object(Bucket='marketgate-auth', Key='auth/users.json', Body=json.dumps({}).encode(), ContentType='application/json')
s3.put_object(Bucket='marketgate-auth', Key='auth/token_blacklist.json', Body=json.dumps([]).encode(), ContentType='application/json')
print('Upload OK')
for obj in s3.list_objects_v2(Bucket='marketgate-auth').get('Contents', []):
    print(f"  {obj['Key']} ({obj['Size']} bytes)")
