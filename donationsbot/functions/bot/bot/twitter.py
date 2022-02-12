import json
from pathlib import Path
from typing import List
import jinja2

import boto3
from aws_lambda_powertools import Logger
import tweepy

ssm_client = boto3.client("ssm")

logger = Logger(child=True)


twitter_param_strings = ssm_client.get_parameters(
    Names=[
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
        "TWITTER_CONSUMER_KEY",
        "TWITTER_CONSUMER_SECRET",
    ],
    WithDecryption=True,
)

twitter_credentials = dict(
    (param["Name"].removeprefix("TWITTER_").lower(), param["Value"])
    for param in twitter_param_strings.get("Parameters", [])
)

tweepy_client = tweepy.Client(**twitter_credentials)

CURRENT_PATH = Path(__file__).parent

TWITTER_MAX_CHARS = 280

TEMPLATE = jinja2.Template(
    source="""{{recipients}}{% for donor in donors %}

{{ donor.name }}

FY 20-21: {% if donor.donations.fy_20_21 %}
{% for donation in donor.donations.fy_20_21 %}
{{ donation.0 }} {{ donation.1}}{% endfor %}
{% else %}Nothing{% endif %}

Before 2020: {% if donor.donations.fy_earlier %}
{% for donation in donor.donations.fy_earlier %}
{{ donation.0 }} {{ donation.1}}{% endfor %}
{% else %}Nothing{% endif %}{% endfor %}"""
)

# TODO: show total amount for earlier years.
# how else to fit into a tweet.

SHORT_TEMPLATE = jinja2.Template(
    source="""{{recipients}}{% for donor in donors %}

{{ donor.name }}

FY 20-21: {% if donor.donations.fy_20_21 %}
{% for donation in donor.donations.fy_20_21 %}
{{ donation.0 }} {{ donation.1}}{% endfor %}
{% else %}Nothing{% endif %}{% endfor %}"""
)


with open(CURRENT_PATH / "data" / "twitter.json") as f:
    TWITTER_HANDLES = json.load(f)

with open(CURRENT_PATH / "data" / "donors.json") as f:
    DONORS = json.load(f)

EXCLUDE_HANDLES = [h.lower() for h in ["@AusPolDonations"]]


def tweet_is_too_long(tweet: str) -> bool:
    # TODO: follow rules here
    # https://developer.twitter.com/en/docs/counting-characters
    return len(tweet) > TWITTER_MAX_CHARS


def format_money(amount: int) -> str:
    return "${:,}".format(amount)


def get_handles_from_tweet(tweet: str) -> List[str]:
    handles = [word.lower() for word in tweet.split() if word.startswith(("@", "#"))]
    return [handle for handle in handles if handle not in EXCLUDE_HANDLES]


def reply_to_tweet(id: int, text: str) -> None:
    handles = get_handles_from_tweet(tweet=text)
    donors_sets_from_handles = [
        donor for handle in handles if (donor := TWITTER_HANDLES.get(handle))
    ]
    if not donors_sets_from_handles:
        return

    # get the donors related to the first handle in the tweet
    donor_set = donors_sets_from_handles[0]

    # combine donor names and donations for the template context
    recipients = " ".join(handles)
    donor_data = [{"name": donor, "donations": DONORS[donor]} for donor in donor_set]
    tweet_text = TEMPLATE.render(donors=donor_data, recipients=recipients)

    if tweet_is_too_long(tweet_text):
        # TODO:
        #  - better short template, include total donations for previous FY
        #  - full tweet may be too long due to either FY 20/21 or earlier, we
        #    should figure out which one.
        tweet_text = SHORT_TEMPLATE.render(donors=donor_data, recipients=recipients)

    # send tweet
    try:
        tweepy_client.create_tweet(in_reply_to_tweet_id=id, text=tweet_text)
    except tweepy.BadRequest as e:
        logger.info(msg=str(e))
        logger.info(tweet_text)
