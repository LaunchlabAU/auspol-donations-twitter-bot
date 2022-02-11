"""
TODO: 
 - twitter credentials during deployment
"""

from aws_cdk import (
    Stack,
    Duration,
    aws_lambda_python_alpha as lambda_python,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_logs as logs,
    aws_sns as sns,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_sns_subscriptions as sns_subscriptions,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_cloudwatch as cloudwatch,
    aws_events_targets as events_targets,
    aws_events as events,
    aws_iam as iam,
)

BOT_LOG_RETENTION = logs.RetentionDays.TWO_MONTHS
ADMIN_NOTIFICATION_EMAILS = ["david+donationsbot@launchlab.com.au"]
# See https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-extension-versions.html  # noqa: E501
LAMBDA_INSIGHTS_LAYER_ARN = (
    "arn:aws:lambda:ap-southeast-2:580247275435:layer:LambdaInsightsExtension-Arm64:1"
)

POLL_TWITTER_INTERVAL_SECONDS = 60


class DeploymentStack(Stack):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #
        # Monitoring
        #

        sns_topic = sns.Topic(self, "MonitoringAlarm")
        for email_address in ADMIN_NOTIFICATION_EMAILS:
            sns_topic.add_subscription(
                sns_subscriptions.EmailSubscription(email_address=email_address)
            )

        sns_action = cloudwatch_actions.SnsAction(topic=sns_topic)

        all_lambda_errors = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Errors",
            period=Duration.minutes(1),
            statistic="Maximum",
        )

        all_lambda_errors_alarm = cloudwatch.Alarm(
            scope=self,
            id="AllLambdaErrors",
            metric=all_lambda_errors,
            evaluation_periods=1,
            threshold=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )
        all_lambda_errors_alarm.add_alarm_action(sns_action)

        lambda_insights_layer = lambda_.LayerVersion.from_layer_version_arn(
            scope=self, id="InsightsLayer", layer_version_arn=LAMBDA_INSIGHTS_LAYER_ARN
        )

        lambda_insights_policy = iam.ManagedPolicy.from_aws_managed_policy_name(
            "CloudWatchLambdaInsightsExecutionRolePolicy"
        )

        #
        # Scheduled lambda function to poll for new mentions & populate queue.
        #

        # We need to keep track of the last read tweet so we can request only tweets we haven't seen yet.
        # We don't need anything fancy here - just add an S3 bucket so we can store the latest tweet id.

        tweet_watcher_bucket = s3.Bucket(self, "TweetReader")

        # We also want a queue for the tweet reader to popluate with new tweets, to be handled
        # by a separate lambda functon

        access_param_store_policy = iam.Policy(
            self,
            "access-param-store",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "ssm:GetParametersByPath",
                        "ssm:GetParameters",
                        "ssm:GetParameter",
                        "ssm:DescribeParameters",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=["*"],
                )
            ],
        )

        tweet_queue = sqs.Queue(
            self,
            "TweetQueue",
            # make visibility timeout longer than timeout of handler lamber function
            visibility_timeout=Duration.minutes(2),
        )

        tweet_watcher_lambda = lambda_python.PythonFunction(
            self,
            "TweetWatcher",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="donationsbot/functions/watcher",
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.minutes(1),
            log_retention=BOT_LOG_RETENTION,
            architecture=lambda_.Architecture.ARM_64,
            layers=[lambda_insights_layer],
            environment={
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_LOGGER_SAMPLE_RATE": "0.1",
                "POWERTOOLS_LOGGER_LOG_EVENT": "true",
                "POWERTOOLS_SERVICE_NAME": "tweet_reader",
                "BUCKET_NAME": tweet_watcher_bucket.bucket_name,
                "SQS_QUEUE_URL": tweet_queue.queue_url,
                "POLL_INTERVAL_SECONDS": str(POLL_TWITTER_INTERVAL_SECONDS),
            },
        )
        tweet_watcher_lambda.role.add_managed_policy(policy=lambda_insights_policy)
        tweet_watcher_lambda.role.attach_inline_policy(policy=access_param_store_policy)

        tweet_watcher_bucket.grant_read_write(identity=tweet_watcher_lambda)
        tweet_queue.grant_send_messages(grantee=tweet_watcher_lambda)

        rule = events.Rule(
            self,
            "BotScheduler",
            schedule=events.Schedule.rate(
                duration=Duration.seconds(POLL_TWITTER_INTERVAL_SECONDS)
            ),
        )
        rule.add_target(events_targets.LambdaFunction(tweet_watcher_lambda))

        #
        # Lambda function to reply to queued tweets.
        #

        bot_lambda = lambda_python.PythonFunction(
            self,
            "BotLambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="donationsbot/functions/bot",
            tracing=lambda_.Tracing.ACTIVE,
            timeout=Duration.minutes(1),
            log_retention=BOT_LOG_RETENTION,
            architecture=lambda_.Architecture.ARM_64,
            layers=[lambda_insights_layer],
            environment={
                "LOG_LEVEL": "INFO",
                "POWERTOOLS_LOGGER_SAMPLE_RATE": "0.1",
                "POWERTOOLS_LOGGER_LOG_EVENT": "true",
                "POWERTOOLS_SERVICE_NAME": "donations_bot",
            },
        )

        bot_lambda.role.add_managed_policy(lambda_insights_policy)
        bot_lambda.role.attach_inline_policy(policy=access_param_store_policy)

        bot_lambda.add_event_source(
            source=lambda_event_sources.SqsEventSource(queue=tweet_queue)
        )
