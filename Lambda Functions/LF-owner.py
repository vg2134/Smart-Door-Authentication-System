import json
import boto3
#from botocore.vendored import requests
import time
import random
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    print (event)
    name = event['name']
    number = event['phone']
    # status = event['status']
    collectionId = 'rekVideoBlog'
    frame_name = "frame.jpg"
    # if status == 'access':

    rekognition = rekognition = boto3.client('rekognition')
    try:
        rekognition_index_response = rekognition.index_faces(CollectionId=collectionId, Image={'S3Object': {'Bucket':'<Name of the S3 bucket storing unknown visitor faces>','Name':frame_name}},
                                    #ExternalImageId=frame_name,
                                    MaxFaces=1,
                                    QualityFilter="AUTO",
                                    DetectionAttributes=['ALL'])
    except:
        return {
        'statusCode': 500,
        'body': 'Internal Server Error'
    }
    print (rekognition_index_response)
    faceId = ''
    for faceRecord in rekognition_index_response['FaceRecords']:
            faceId = faceRecord['Face']['FaceId']

    print(faceId)

    dynamo_client = boto3.resource('dynamodb')
    visitor_table = dynamo_client.Table('visitors')

    rekognition_bucket = "<Name of the S3 bucket storing known visitor faces>"
    photos = []
    photo_dict = {}
    object_key = str(faceId) + str(name) + ".jpg"
    bucket = rekognition_bucket
    createdTimeStamp = int(time.time())
    photo_dict["objectKey"] = object_key
    photo_dict["bucket"] = bucket
    photo_dict["createdTimeStamp"] = createdTimeStamp

    photos.append(photo_dict)

    visitor_table.put_item(
        Item={
                "name": name,
                "faceId" : faceId,
                "phoneNumber" : number,
                "photos" : photos
            }
    )

    s3 = boto3.resource('s3')
    copy_source = {
        'Bucket': '<Name of the S3 bucket storing unknown visitor faces>',
        'Key': frame_name
    }
    known_visitors_bucket = s3.Bucket('<Name of the S3 bucket storing unknown visitor faces>')
    known_visitors_bucket.copy(
            copy_source, object_key
        )

    otp = generate_otp(faceId, int(time.time()+30))
    send_sns(otp,faceId)

    return {
        'statusCode': 200,
        'body': json.dumps('Success')
    }
    # else:
    #     return {
    #         'statusCode': 400,
    #         'body': json.dumps('Denied')
    #     }
def generate_otp(faceId, expirationTime):
    dynamo_client = boto3.resource('dynamodb')
    otp_table = dynamo_client.Table('passcodes')

    otp=""
    for i in range(6):
        otp+=str(random.randint(1,9))

    otp_table.put_item(
        Item={
            "uName": "Visitor",
            "faceId" : faceId,
            "otp" : int(otp),
            "expirationTime" : int(expirationTime)}
    )

    return otp

def send_sns(otp,faceId):
    dynamoClient = boto3.resource('dynamodb')
    visitors_table = dynamoClient.Table('visitors')
    visitorResponseData = visitors_table.query(KeyConditionExpression=Key('faceId').eq(faceId))
    item_list = visitorResponseData["Items"]
    visitor_data = item_list[0]
    phoneNumber = visitor_data["phoneNumber"]
    topic_arn = "<ARN of SNS topic for known visitors>"
    sns = boto3.client("sns")
    msg = "Your One Time Password is " + str(otp) + " Enter it in this link.  " + "https://<Name of the S3 bucket hosting your website>.s3-us-west-2.amazonaws.com/auth.html"
    sub = "Your Smart Gate OTP"
    response = sns.publish(
    TopicArn=topic_arn,
    Message=msg,
    Subject=sub
    )
    print("sns sent" + json.dumps(response))