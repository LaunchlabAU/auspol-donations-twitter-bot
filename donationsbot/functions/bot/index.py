from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths

from bot.twitter import reply_to_tweet

tracer = Tracer()
logger = Logger()


def get_tweets_from_event(event):
    # TODO
    return []


@tracer.capture_lambda_handler
def handler(event, context):
    for tweet in get_tweets_from_event(event=event):
        reply_to_tweet(tweet=tweet)
