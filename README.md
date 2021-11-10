This terraform module will create two lambda functions to add/remove alarm to any new instance that comes up and when that alarm triggers, will collect some stats of the current situation of that instance.


First Lambda function: This will get invoked when an instance reaches either "running" or "terminated" state. When in running state, the function will add some alarms based on the existance of tags (i.e cpu-alarm=yes). When in "terminated" state, it will delete all the alarms that it might have created for this instance.


Second lambda function: This will get invoked by the alarm(via sns) and collect some stats like (running processes, load avg) and put the data in cloudwatch.


Since it use tags, it can be used to select a set of intances to add alarms. This can be extended to add more alarms and the stat collection can be tailored for individual's requirement
