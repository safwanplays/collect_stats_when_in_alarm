import boto3
import json
import os
import time
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    print(json.dumps(event, indent=4))
    region = event['region']
    instance_id = event['detail']['instance-id']
    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.describe_instances(
    InstanceIds=[
        instance_id,
    ],
    )
    instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
    if instance_state == "running":
        ## Get the dictionary of tags. we will make some decisions based on the tags
        tags = get_tags(region,instance_id)
        if not tags:
            print("There is no tag requesting alarms. so skipping ...")
            return 200
        print(tags)
        ## If you don't want to process instances that are part of an autoscaling group hash out the next three lines
        #if "aws:autoscaling:groupName" in tags:
            #print("Won't add any alarm since this is a part of an autoscaling group")
            #return 200

        ## Take a list of alrams that were requested. Suppose we have two types of alarms available like cpu, disk right now. if the tag has cpu-alarm=yes then we will add the cpu alarm, if it has disk-alarm=yes then we will add memory alarm. We can add more alarm as we go. This is just for demostration
        if "cpu-alarm" in tags and tags["cpu-alarm"] == "yes":
            create_cpu_alarm(region,instance_id)
        if "disk-alarm" in tags and tags["disk-alarm"] == "yes":
            create_disk_alarm(region,instance_id)
    elif instance_state == "terminated":
        delete_alarm(region,instance_id)   ### Delete alarm will be kinda brute force. it will go round a loop for every alarm. If it exists, it will dellte it. The alarm name has a pattern, which will be our cue to find the alarm. We could delete alarm based on a tag that identifies who created it and then delete it. But this will mean more work. We will have to add a tag on each alarm and then check that tag and make decision based on the result. At this point this would be too much work to achive something not so significant.
    else:
        ## No need to do anything. This is the state we are never expecting to find ourseleves in
        print("Nothing to do")
        return 200

def get_tags(region,instance_id):
    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.describe_instances(
    InstanceIds=[
        instance_id,
    ],
    )
    tags = {}
    if 'Tags' in response['Reservations'][0]['Instances'][0]:
        tag_list = response['Reservations'][0]['Instances'][0]['Tags']
        for i in tag_list:
            tags[i['Key']] = i['Value']
        
    return tags




def create_cpu_alarm(region, instance_id):
    #region = event['region']
    #instance_id = event['detail']['instance-id']
    #ec2 = boto3.client('ec2', region_name=region)
    cw = boto3.client('cloudwatch', region_name=region)
    ##We need to create an alarm with a name that uniquely identifies the alarm for the instance.if the alarm is already there, we will not create it. This might be the situation when an instance came back from stop state.
    alarm_name = "cpu-alarm01_"+region+"_"+instance_id
    if check_alarm_name(region,alarm_name):
        print("The alarm ",alarm_name," already exists. No need to create it")
    else:
        print("Need to create the alarm with the name ", alarm_name)
        ##get the sns topic ARN.This was brought to the environment while creating the lambda function
        sns_topic = os.environ['sns_topic']
        try:
            cw.put_metric_alarm(
    		AlarmName          = alarm_name,
    		ComparisonOperator = "GreaterThanOrEqualToThreshold",
    		EvaluationPeriods  = 2,
    		MetricName         = "CPUUtilization",
    		Namespace           = "AWS/EC2",
    		Period              = 60,
    		Statistic           = "Average",
    		Threshold           = 50,
                    TreatMissingData    = "missing",
    		Dimensions =[ {
                        "Name" : "InstanceId",
                        "Value" : instance_id
    		},
                    ],
    		AlarmDescription = "This metric monitors ec2 cpu utilization",
    		AlarmActions     = [sns_topic]  
    		#alarm_actions     = [will need to pass as an environmental variable]  
                ## does it need iam permission to trigger the sns? Here the alarm needs to trigger the sns and lambda is creating the alarm not the user who wrote this lambda. so if lambda has to pass the permission to the sns, it needs the IAM PassRole permission. This is different than when I am creating an alarm in terrafrom by myself. On the other hand we can attach a policy to the SNS topic so that this alarm can publish here. This will be the recommended approach.
            )
            print("The alarm was created with the name ",alarm_name)
        except ClientError:
            print("Could not create the alarm")

def create_disk_alarm(region, instance_id):
    #region = event['region']
    #instance_id = event['detail']['instance-id']
    #ec2 = boto3.client('ec2', region_name=region)
    cw = boto3.client('cloudwatch', region_name=region)
    ##We need to create an alarm with a name that uniquely identifies the alarm for the instance.if the alarm is already there, we will not create it. This might be the situation when an instance came back from stop state.
    alarm_name = "disk-alarm01_"+region+"_"+instance_id
    if check_alarm_name(region,alarm_name):
        print("The alarm ",alarm_name," already exists. No need to create it")
    else:
        print("Need to create the alarm with the name ", alarm_name)
        ##get the sns topic ARN.This was brought to the environment while creating the lambda function
        sns_topic = os.environ['sns_topic']
        try:
            cw.put_metric_alarm(
    		AlarmName          = alarm_name,
    		ComparisonOperator = "GreaterThanOrEqualToThreshold",
    		EvaluationPeriods  = 2,
    		MetricName         = "DiskWriteBytes",
    		Namespace           = "AWS/EC2",
    		Period              = 60,
    		Statistic           = "Maximum",
    		Threshold           = 500,
                    TreatMissingData    = "missing",
    		Dimensions =[ {
                        "Name" : "InstanceId",
                        "Value" : instance_id
    		},
                    ],
    		AlarmDescription = "This metric monitors disk write bytes",
    		AlarmActions     = [sns_topic]  
    		#alarm_actions     = [will need to pass as an environmental variable]  
                    ## does it need iam permission to trigger the sns. Here the alarm needs to trigger the sns and lambda is creating the alarm not the user who wrote this lambda. so if lambda has to pass the permission to the sns, it needs the IAM PassRole permission. This is different than when I am creating an alarm in terrafrom by myself. On the other hand we can attach a policy to the SNS topic so that this alarm can publish here. This will be the recommended approach.
            )
            print("The alarm was created with the name ",alarm_name)
        except ClientError:
            print("Could not create the alarm")




def delete_alarm(region, instance_id):
    for alarm in ["cpu-alarm", "disk-alarm"]:
        alarm_name = alarm+"01_"+region+"_"+instance_id
        print("Will try to delete the alarm ", alarm_name," if it exists")
        if not check_alarm_name(region,alarm_name):
            print("This alarm ",alarm_name," does not exist.No need to delete it")
        else:
            print("The alarm exists. Need to delete it")
            cw = boto3.client('cloudwatch', region_name=region)
            response = cw.delete_alarms(
            AlarmNames=[
            alarm_name
            ]
            )
            time.sleep(3)
            if check_alarm_name(region,alarm_name):
                print("Could not delete the alarm")
            else:
                print("This alarm was deleted successfully")



def check_alarm_name(region,alarm_name):
    cw = boto3.client('cloudwatch', region_name=region)
    #paginator = cloudwatch.get_paginator()
    response = cw.describe_alarms(
    AlarmNames=[
        alarm_name,
    ]
    )
    ##The MetricAlarms list inside the response will be empty if there is no alarm of that name
    if len(response['MetricAlarms']) != 0:
        return True
    else:
        return False

