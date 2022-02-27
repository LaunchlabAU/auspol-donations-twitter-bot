import json
from pathlib import Path
from collections import Counter
from typing import List, Tuple
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

REMOVE_FROM_DONOR_NAME = ["pty", "ltd"]

TEMPLATE = jinja2.Template(
    source="""{{recipients}}{% for donor in donors %}

{{ donor.name }}

FY 20-21: {% if donor.donations.fy_20_21 %}
{% for donation in donor.donations.fy_20_21 %}
{{ donation.0 }} {{ donation.1}}{% endfor %}
{% else %}Nothing reported to AEC{% endif %}

Before 2020: {% if donor.donations.fy_earlier %}
{% for donation in donor.donations.fy_earlier %}
{{ donation.0 }} {{ donation.1}}{% endfor %}
{% else %}Nothing reported to AEC{% endif %}{% endfor %}"""
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

NOT_FOUND_TEMPLATE = jinja2.Template(
    source="""Could not find any donation data for {{ donors }}.
    
    If you think we're missing something, please help us with the dataset at https://github.com/LaunchlabAU/auspol-donations-twitter-bot"""
)


with open(CURRENT_PATH / "data" / "twitter.json") as f:
    TWITTER_HANDLES = json.load(f)

with open(CURRENT_PATH / "data" / "donors.json") as f:
    DONORS = json.load(f)

EXCLUDE_HANDLES = [
    h.lower()
    for h in ["@AusPolDonations", "#auspol", "#DonationsReform", "@SomeCompany"]
]


def tweet_is_too_long(tweet: str) -> bool:
    # TODO: follow rules here
    # https://developer.twitter.com/en/docs/counting-characters
    return len(tweet) > TWITTER_MAX_CHARS


def format_money(amount: int) -> str:
    return "${:,}".format(amount)


def unformat_money(amount: str) -> int:
    # TODO: we should delay formatting money rather than format and unformat!
    return int(amount.replace("$", "").replace(",", ""))


def get_handles_from_tweet(tweet: str) -> Tuple[List[str], List[str]]:
    handles = [word.lower() for word in tweet.split() if word.startswith(("@", "#"))]
    filtered_handles = [handle for handle in handles if handle not in EXCLUDE_HANDLES]
    # hash tags to add back into response, but not use in lookup
    add_hashtags = [
        handle
        for handle in handles
        if handle in EXCLUDE_HANDLES and handle.startswith("#")
    ]
    return filtered_handles, add_hashtags


def clean_donor_name(name: str) -> str:
    new_name = " ".join(
        part for part in name.split() if part.lower() not in REMOVE_FROM_DONOR_NAME
    )
    return new_name.strip()


def combine_donor_data(donor_data):
    name = " / ".join([d["name"] for d in donor_data])
    fy_20_21 = Counter()
    fy_earlier = Counter()
    for donor in donor_data:
        for donation in donor["donations"]["fy_20_21"]:
            fy_20_21.update({donation[0]: unformat_money(donation[1])})
        for donation in donor["donations"]["fy_earlier"]:
            fy_earlier.update({donation[0]: unformat_money(donation[1])})
    donations = {"fy_20_21": [], "fy_earlier": []}
    for donor, amount in fy_20_21.most_common():
        donations["fy_20_21"].append([donor, format_money(amount=amount)])
    for donor, amount in fy_earlier.most_common():
        donations["fy_earlier"].append([donor, format_money(amount=amount)])
    return [{"name": name, "donations": donations}]


def reply_to_tweet(id: int, text: str, testing: bool = False) -> None:
    handles, hashtags_to_add_to_response = get_handles_from_tweet(tweet=text)
    if not handles:
        return
    donors_sets_from_handles = [
        donor for handle in handles if (donor := TWITTER_HANDLES.get(handle))
    ]
    recipients = " ".join(handles)
    if not donors_sets_from_handles:
        tweet_text = NOT_FOUND_TEMPLATE.render(donors=recipients)
        tweepy_client.create_tweet(in_reply_to_tweet_id=id, text=tweet_text)
        return

    # get the donors related to the first handle in the tweet
    donor_set = donors_sets_from_handles[0]

    # combine donor names and donations for the template context
    donor_data = [
        {"name": clean_donor_name(name=donor), "donations": DONORS[donor]}
        for donor in donor_set
    ]

    # Testing: try combining donor data to reduce tweet size for e.g. #nine with multiple
    # entities
    # TODO: clean this up if it looks like combining entities will allow us to fit most
    # cases within a tweet without having to drop contributions before FY 20-21
    combined_donor_data = combine_donor_data(donor_data)
    # add #auspol hashtag to recipients - which has been stripped out to avoid trying
    # to match
    for hashtag in hashtags_to_add_to_response:
        recipients += f" {hashtag}"
    tweet_text = TEMPLATE.render(donors=combined_donor_data, recipients=recipients)
    if testing:
        print(tweet_text)
        return
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
