import json
import locale
from pathlib import Path
from typing import List
import jinja2

locale.setlocale(locale.LC_ALL, "en_AU")

CURRENT_PATH = Path(__file__).parent

TEMPLATE = jinja2.Template(
    source="""{{recipients}}

{% for donor in donors %}
{{ donor.name }}

FY 2020-21
{% if donor.donations.fy_20_21 %}{% for donation in donor.donations.fy_20_21 %}
{{ donation.0 }} {{ donation.1}}{% endfor %}
{% else %}
None
{% endif %}
Earlier
{% if donor.donations.fy_earlier %}{% for donation in donor.donations.fy_earlier %}
{{ donation.0 }} {{ donation.1}}{% endfor %}
{% else %}
None
{% endif %}
{% endfor %}
"""
)

with open(CURRENT_PATH / "data" / "twitter.json") as f:
    TWITTER_HANDLES = json.load(f)

with open(CURRENT_PATH / "data" / "donors.json") as f:
    DONORS = json.load(f)


def get_handles_from_tweet(tweet: str) -> List[str]:
    return [word.lower() for word in tweet.split() if word.startswith(("@", "#"))]


def reply_to_tweet(tweet: str):
    handles = get_handles_from_tweet(tweet=tweet)
    donors_sets_from_handles = [
        donor for handle in handles if (donor := TWITTER_HANDLES.get(handle))
    ]
    if not donors_sets_from_handles:
        return

    # get the donors related to the first handle in the tweet
    donor_set = donors_sets_from_handles[0]

    # combine donor names and donations for the template context
    donor_data = [{"name": donor, "donations": DONORS[donor]} for donor in donor_set]
    print(donor_data)
    print(TEMPLATE.render(donors=donor_data))
