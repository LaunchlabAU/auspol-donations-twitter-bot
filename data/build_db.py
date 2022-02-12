"""
Create 2 json files from the markdown tables, which act as the database.

- one to map each twitter handle to a set of donors
- another to map donors to aggregated donation data
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from utils import (
    SOURCE_DONATION_MADE_TO,
    SOURCE_DONOR_NAME,
    SOURCE_FINANCIAL_YEAR,
    SOURCE_VALUE,
    TARGET_DONATION_MADE_TO,
    TARGET_DONOR,
    TARGET_PARTY,
    TARGET_TWITTER,
    WhitespaceStrippingDictReader,
)


def format_money(amount: int) -> str:
    return "${:,}".format(amount)


ROOT_DIR = Path(__file__).parent.parent
LAMBDA_DATA_PATH = ROOT_DIR / "donationsbot" / "functions" / "bot" / "bot" / "data"

TABLES_PATH = Path(__file__).parent / "tables"

TABLE_TWITTER_DONORS_PAGE_1 = TABLES_PATH / "twitter_donors_page_1.md"
TABLE_TWITTER_DONORS_PAGE_2 = TABLES_PATH / "twitter_donors_page_2.md"
TABLE_PARTIES = TABLES_PATH / "parties.md"

DONATIONS_CSV_FILE = Path(__file__).parent / "src" / "2022" / "Donations Made.csv"


DB_TWITTER_HANDLES = LAMBDA_DATA_PATH / "twitter.json"
DB_DONOR = LAMBDA_DATA_PATH / "donors.json"


def create_db_twitter_to_donors():
    data = defaultdict(list)
    for filename in [TABLE_TWITTER_DONORS_PAGE_1, TABLE_TWITTER_DONORS_PAGE_2]:
        with open(filename) as f:
            reader = WhitespaceStrippingDictReader(f=f, delimiter="|")
            for row in reader:
                if "---" in row[TARGET_DONOR]:
                    continue
                for handle in row[TARGET_TWITTER].split():
                    data[handle.lower()].append(row[TARGET_DONOR])
    with open(DB_TWITTER_HANDLES, "w") as f:
        json.dump(data, fp=f)


def get_donations_made_to_party_mapping():
    data = dict()
    with open(TABLE_PARTIES) as f:
        reader = WhitespaceStrippingDictReader(f=f, delimiter="|")
        for row in reader:
            if "---" in row[TARGET_DONATION_MADE_TO]:
                continue
            data[row[TARGET_DONATION_MADE_TO]] = row[TARGET_PARTY]
    return data


def format_donation(donation, max_donor_len, max_donation_len):
    return [
        donation[0],
        format_money(donation[1]).ljust(max_donation_len),
    ]


class DonationStats:
    fy_2020_21: Counter
    fy_earlier: Counter

    def __init__(self) -> None:
        self.fy_2020_21 = Counter()
        self.fy_earlier = Counter()

    def get_max_len(self, values):
        if not values:
            return 0
        return max([len(value) for value in values])

    @property
    def fy_2020_21_max_donor_len(self) -> int:
        return self.get_max_len(self.fy_2020_21.keys())

    def to_json(self):
        # fy_20_21_donor_max_len = self.get_max_len(self.fy_2020_21.keys())
        fy_20_21_max_donation_length = self.get_max_len(
            [format_money(value) for value in self.fy_2020_21.values()]
        )
        # fy_earlier_donor_max_len = self.get_max_len(self.fy_earlier.keys())
        fy_earlier_max_donation_length = self.get_max_len(
            [format_money(value) for value in self.fy_earlier.values()]
        )

        # try not padding donor names to reduce chars, we'll put $ to the left

        return {
            "fy_20_21": [
                format_donation(
                    d,
                    max_donor_len=0,
                    max_donation_len=fy_20_21_max_donation_length,
                )
                for d in self.fy_2020_21.most_common()
            ],
            "fy_earlier": [
                format_donation(
                    d,
                    max_donor_len=0,
                    max_donation_len=fy_earlier_max_donation_length,
                )
                for d in self.fy_earlier.most_common()
            ],
        }


def create_db_donor_stats():
    data = defaultdict(DonationStats)
    # first, map "donations made to" to party
    donations_made_to_party_mapping = get_donations_made_to_party_mapping()
    # now maps donations to political partes.
    with open(DONATIONS_CSV_FILE) as donations_csv_file:
        reader = csv.DictReader(f=donations_csv_file)
        for row in reader:
            # we mapped "|" to "/" in other files to avoid breaking markdown tables
            # so do the same here
            donation_made_to = row[SOURCE_DONATION_MADE_TO].replace("|", "/")
            if not (party := donations_made_to_party_mapping.get(donation_made_to)):
                # our "donations made to" to party mapping isn't ready yet, just
                # put a placeholder in until we're done.
                party = "[unsorted data]"
            donor = row[SOURCE_DONOR_NAME].replace("|", "/")
            donation = {party: int(row[SOURCE_VALUE])}
            if row[SOURCE_FINANCIAL_YEAR] == "2020-21":
                data[donor].fy_2020_21.update(donation)
            else:
                data[donor].fy_earlier.update(donation)

    with open(DB_DONOR, "w") as donor_db_file:
        json.dump(dict(((k, v.to_json()) for k, v in data.items())), donor_db_file)


if __name__ == "__main__":
    create_db_twitter_to_donors()
    create_db_donor_stats()
