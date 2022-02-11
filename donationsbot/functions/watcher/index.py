import json
import os
from typing import Any, Dict, Generator, List, Union

import arrow
import boto3
import tweepy
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

BUCKET_NAME = os.environ["BUCKET_NAME"]
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", 60))

tracer = Tracer()
logger = Logger()

s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")

# get twitter credentials

ssm_client = boto3.client("ssm")


twitter_params_response = ssm_client.get_parameters(
    Names=[
        "TWITTER_ID",
        "TWITTER_BEARER_TOKEN",
    ],
    WithDecryption=True,
)

twitter_params = dict(
    (param["Name"], param["Value"])
    for param in twitter_params_response.get("Parameters", [])
)

TWITTER_ID = twitter_params["TWITTER_ID"]

# set up twitter client.

tweepy_client = tweepy.Client(twitter_params["TWITTER_BEARER_TOKEN"])


LATEST_TWEET_ID_KEY = "latest_id.txt"
MAX_RESULTS_TWITTER = 100
# limit of 10 in send_message_batch
SQS_BATCH_SIZE = 10


def chunks(data: List[Any], chunk_size: int) -> Generator[Any, None, None]:
    # Yield successive chunks from list_.
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


def get_starting_point_kwargs() -> Union[Dict[str, str], Dict[str, int]]:
    # If we have a latest tweet stored in S3, then use that as the starting point.
    # If anything should happen to the tweet id in S3, we wouldn't want to go
    # though the history of all tweets and start responding again! So in that case
    # we fall back to an approximate timestamp of the last polling interval (in that
    # case there's a possibility of missing or duplicating only a small number of
    # tweets)
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=LATEST_TWEET_ID_KEY)
    except s3_client.exceptions.NoSuchKey:
        return {
            "start_time": arrow.utcnow()
            .shift(seconds=-1 * POLL_INTERVAL_SECONDS)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    return {"since_id": int(response["Body"].read())}


def store_latest_id(latest_id: int) -> None:
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=LATEST_TWEET_ID_KEY,
        ContentType="text/plain",
        Body=str(latest_id).encode(),
    )


def queue_tweets(tweets: List[tweepy.Tweet]) -> None:
    messages = [
        {
            "Id": str(tweet.id),
            "MessageBody": json.dumps(tweet.data),
        }
        for tweet in tweets
    ]
    for message_batch in chunks(data=messages, chunk_size=SQS_BATCH_SIZE):
        sqs_client.send_message_batch(QueueUrl=SQS_QUEUE_URL, Entries=message_batch)


@logger.inject_lambda_context()
@tracer.capture_lambda_handler
def hander(event: Dict[str, Any], context: LambdaContext) -> None:
    starting_point_kwargs = get_starting_point_kwargs()
    response = tweepy_client.get_users_mentions(
        id=TWITTER_ID, max_results=MAX_RESULTS_TWITTER, **starting_point_kwargs
    )
    if newest_id := response.meta.get("newest_id"):
        store_latest_id(latest_id=int(newest_id))
    queue_tweets(response.data)
    while next_token := response.meta.get("next_token"):
        response = tweepy_client.get_users_mentions(
            id=TWITTER_ID,
            max_results=MAX_RESULTS_TWITTER,
            pagination_token=next_token,
            **starting_point_kwargs,
        )
        queue_tweets(response.data)
