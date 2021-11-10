###archive the lambda function
data "archive_file" "lambda_function" {
  type        = "zip"
  source_file = "lambda_to_add_alarm.py"
  output_path = "lambda_to_add_alarm.zip"
}



###lambda definition

resource "aws_lambda_function" "lambda_to_add_alarm" {
  filename      = "lambda_to_add_alarm.zip"
  function_name = "lambda_to_add_alarm"
  role          = aws_iam_role.lambda_role01.arn
  handler       = "lambda_to_add_alarm.lambda_handler"

  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  source_code_hash = "${data.archive_file.lambda_function.output_base64sha256}"

  runtime = "python3.6"
  timeout = 30

  environment {
    variables = {
      sns_topic = "${aws_sns_topic.topic01.arn}"
    }
  }
}







### IAM role of the lambda function
resource "aws_iam_role" "lambda_role01" {
  name = "lambda_role01"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })

  tags = {
    Purpose = "create_alarm"
  }
}

resource "aws_iam_policy" "lambda_policy01" {
  name        = "lambda_policy01"
  path        = "/"
  description = "My test policy"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents",
          "logs:DescribeAlarms", 
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*"
      },
      {
        Action = [
          "ec2:StopInstances",
          "ec2:DescribeInstances"
		]
        Effect  = "Allow"
        Resource = "*"

      },
      {
        Action = [
          "cloudwatch:PutMetricAlarm", ### We need this so that we can create alarm
          "cloudwatch:DescribeAlarms",
          "cloudwatch:DeleteAlarms"
		]
        Effect  = "Allow"
        Resource = "*"

      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "test-attach" {
  role       = aws_iam_role.lambda_role01.name
  policy_arn = aws_iam_policy.lambda_policy01.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_to_add_alarm.arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ec2_start_event.arn
}


resource "aws_cloudwatch_event_rule" "ec2_start_event" {
  name        = "capture-ec2-start"
  description = "Capture each ec2 start"

  event_pattern = <<EOF
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 Instance State-change Notification"],
  "detail": {
    "state": ["running", "terminated"]
  }
}
EOF
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.ec2_start_event.name
  target_id = "invoke_lmbda"
  arn       = aws_lambda_function.lambda_to_add_alarm.arn
}

###Create an SNS topic and subscription for the alarm.This sns will in turn trigger the lambda function that will process the alarm(stop,terminate the instance etc). It would be great to just trigger the lambda directly from the alarm but I found no way to trigger a lambda from alarm. So I am forced to use SNS here.Having said that, using SNS gives me some other benefits that might be helpful in future.

###This SNS topic will be triggered by the cloudwatch alarm. cloudwtch alarm will need to have permission to do that.

resource "aws_sns_topic" "topic01" {
  name = "topic_for_cpu_alarm_lambda01"
}

resource "aws_sns_topic_subscription" "email_target01" {
  topic_arn = aws_sns_topic.topic01.arn
  protocol  = "email"
  endpoint  = "safwanlmu@gmail.com"
}


resource "aws_sns_topic_subscription" "lambda_target01" {
  topic_arn = aws_sns_topic.topic01.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.lambda_to_collect_stats.arn
}




### Second lambda definition



###archive the lambda function
data "archive_file" "lambda_function02" {
  type        = "zip"
  source_file = "lambda_to_collect_stats.py"
  output_path = "lambda_to_collect_stats.zip"
}




resource "aws_lambda_function" "lambda_to_collect_stats" {
  filename      = "lambda_to_collect_stats.zip"
  function_name = "lambda_to_collect_stats"
  role          = aws_iam_role.lambda_role02.arn
  handler       = "lambda_to_collect_stats.collect_stats"

  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  source_code_hash = "${data.archive_file.lambda_function02.output_base64sha256}"

  runtime = "python3.6"
  timeout = 30


  environment {
    variables = {
      document_name = "${aws_ssm_document.collect_stats.name}"
    }
  }

}

### IAM role of the lambda function
resource "aws_iam_role" "lambda_role02" {
  name = "lambda_role02"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })

  tags = {
    Purpose = "collect_stats"
  }
}

resource "aws_iam_policy" "lambda_policy02" {
  name        = "lambda_policy02"
  path        = "/"
  description = "policy for lambda02"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents",
          "logs:DescribeAlarms", 
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*"
      },
      {
        Action = [
          "ec2:StopInstances",
          "ec2:DescribeInstances"
		]
        Effect  = "Allow"
        Resource = "*"

      },
      {
        Action = [
          "ssm:SendCommand",
		]
        Effect  = "Allow"
        Resource = [  
		"arn:aws:ec2:*",
		"arn:aws:ssm:*"
		]
      },
    ]
  })
}

### the "arn:aws:ec2:*" and "arn:aws:ssm:*" resource on the "ssm:SendCommand" action is a bit interesting. usually when I say a action "servicename:action", the resource is usually "arm:aws:servicename". But here I had to define both ssm and ec2 as the resource for the "ssm:SendCommand" action. specifying just one gave me access denied error




resource "aws_iam_role_policy_attachment" "attach_lambda02" {
  role       = aws_iam_role.lambda_role02.name
  policy_arn = aws_iam_policy.lambda_policy02.arn
}

resource "aws_lambda_permission" "allow_sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_to_collect_stats.arn
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.topic01.arn
}



##Policy to allow alarm to publish on sns and lambda to subscribe

resource "aws_sns_topic_policy" "sns_policy01" {
  arn = aws_sns_topic.topic01.arn
  policy = data.aws_iam_policy_document.sns_topic_policy01.json
}


data "aws_iam_policy_document" "sns_topic_policy01" {
  policy_id = "sns_topic_policy01"

  statement {
    actions = [
      "SNS:Subscribe",
      "SNS:Publish",
    ]

    effect = "Allow"

    principals {
        type	= "Service"
        identifiers	= [ "cloudwatch.amazonaws.com" ]
    }

    resources = [
      aws_sns_topic.topic01.arn,
    ]

    sid = "sns_topic_policy01"
  }
}



#############################  SSM document to run a command in ec2
resource "aws_ssm_document" "collect_stats" {
  name          = "stat_collect_document"
  document_type = "Command"

  content = <<DOC
  {
    "schemaVersion": "1.2",
    "description": "Check ip configuration of a Linux instance.",
    "parameters": {

    },
    "runtimeConfig": {
      "aws:runShellScript": {
        "properties": [
          {
            "id": "0.aws:runShellScript",
            "runCommand": [
		"date",
		"echo 'interface info:'",
		"ifconfig",
		"echo 'process info:'",
		"ps -ef",
		"echo 'load average:'",
		"uptime",
		"echo 'vmstat -a output:'",
		"vmstat -a"
			]
          }
        ]
      }
    }
  }
DOC
}





