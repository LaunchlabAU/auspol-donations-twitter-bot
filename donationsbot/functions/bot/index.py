from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.data_classes import SQSEvent, event_source
from aws_lambda_powertools.utilities.typing import LambdaContext
import json

from bot.twitter import reply_to_tweet

tracer = Tracer()
logger = Logger()


@logger.inject_lambda_context()
@tracer.capture_lambda_handler
@event_source(data_class=SQSEvent)
def handler(event: SQSEvent, context: LambdaContext):
    for record in event.records:
        reply_to_tweet(**json.loads(record.body))
