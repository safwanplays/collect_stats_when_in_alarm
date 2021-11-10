import boto3
import json
import os
from botocore.exceptions import ClientError

def collect_stats(event, context):
    ##First print the event. This is just to understand the context
    print(json.dumps(event, indent=4))
    message = json.loads(event['Records'][0]['Sns']['Message'])   ## Message is just a string. Need to load it to a dictionary so that we can process the info better
    #print("message is: ",message)
    alarm_name = message['AlarmName']
    region = alarm_name.split("_")[1]  ### Extract the region from the alarm name. I would like to extract the name from the sns but looking at the whole record it seems like that's more work
    instance_id = message['Trigger']['Dimensions'][0]['value']
    print("instance_id= ",instance_id)
    print("Need to run collect_stat_document on ",instance_id," in ",region," region")  
    ## We want to run a document in response to this alarm. The document output is of most value to us since it tells us about the situation. we can put this output in s3 or cloudwatch. I will put to cloudwatch. Also I will send a SNS notification for the execution of this document in email so that people know this was run.
    ## Create a log group so that ssm can put log in it. lambda will need permission to create loggroup and ssm will need permission to put logs in it.
    log_group_name = create_log_group(region,instance_id)
    if not log_group_name:
        print("There were some problems creating the log group")
        return False
    ssm = boto3.client('ssm', region_name=region)
    document_name = os.environ['document_name']
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName=document_name,
            CloudWatchOutputConfig={
           'CloudWatchLogGroupName': log_group_name ,
           'CloudWatchOutputEnabled': True
   	    }
    	   )
    except ClientError as e:
        print("There was an issue running the command. Exception:",e)


    return 200



def create_log_group(region, instance_id):
    ##Check if the log group exists already or not
    logs = boto3.client('logs', region_name=region)
    log_group_name = "stat_"+region+"_"+instance_id   ## We could tune the name more specifically
    response = logs.describe_log_groups(
    logGroupNamePrefix=log_group_name )
    if len(response['logGroups']) == 0:
        print("Loggroup ",log_group_name," already exists. No need to create it")
        return log_group_name
    else:
        print("Need to create Loggroup ",log_group_name)
    
    try:
        logs.create_log_group(logGroupName=log_group_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
            print("Log group already exist")
            return log_group_name
        else:
            print("Log group was not created. Reason:",e)
            return False


    print("Created the log Group ",log_group_name)
    return log_group_name

    

