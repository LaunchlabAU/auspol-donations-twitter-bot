"""
Map twitter handles to donors in markdown to make it easy to collaborate
"""

import csv
from collections import Counter, defaultdict
from io import StringIO
from typing import DefaultDict

from csv2md.table import Table

from utils import (
    WhitespaceStrippingDictReader,
    SOURCE_VALUE,
    SOURCE_DONATION_MADE_TO,
    SOURCE_DONOR_NAME,
    TARGET_DONATION_MADE_TO,
    TARGET_DONOR,
    TARGET_PARTY,
    TARGET_TOTAL_DONATIONS,
    TARGET_TWITTER,
)


def format_money(amount: int) -> str:
    return "${:,}".format(amount)


DONATIONS_FILE = "src/2022/Donations Made.csv"
TWITTER_MAPPING_MARKDOWN_FILE_PAGE_1 = "tables/twitter_donors_page_1.md"
TWITTER_MAPPING_MARKDOWN_FILE_PAGE_2 = "tables/twitter_donors_page_2.md"
PARTY_GROUPS_MARKDOWN_FILE = "tables/parties.md"


#
# Twitter handles
#


def get_existing_twitter_handles() -> DefaultDict:
    twitter_handles = defaultdict(str)
    try:
        for filename in [
            TWITTER_MAPPING_MARKDOWN_FILE_PAGE_1,
            TWITTER_MAPPING_MARKDOWN_FILE_PAGE_2,
        ]:
            with open(filename) as markdown_file:
                reader = WhitespaceStrippingDictReader(f=markdown_file, delimiter="|")
                for row in reader:
                    if "---" in row[TARGET_DONOR]:
                        continue
                    twitter_handles[row[TARGET_DONOR]] = row[TARGET_TWITTER]
    except FileNotFoundError:
        pass
    return twitter_handles


def build_twitter_donor_table() -> None:

    # load any existing twitter handles
    twitter_handles = get_existing_twitter_handles()

    # use Counter() to add all donations from same donor
    counter = Counter()
    with open(DONATIONS_FILE) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            counter.update({row[SOURCE_DONOR_NAME]: int(row[SOURCE_VALUE])})

    # create a new temporary csv file to render as markdown
    with StringIO() as temp_csv_file_page_1:
        with StringIO() as temp_csv_file_page_2:
            writer_page_1 = csv.DictWriter(
                f=temp_csv_file_page_1,
                fieldnames=[TARGET_TWITTER, TARGET_DONOR, TARGET_TOTAL_DONATIONS],
            )
            writer_page_2 = csv.DictWriter(
                f=temp_csv_file_page_2,
                fieldnames=[TARGET_TWITTER, TARGET_DONOR, TARGET_TOTAL_DONATIONS],
            )
            writer_page_1.writeheader()
            writer_page_2.writeheader()
            for donor, value in counter.most_common():
                writer = writer_page_1 if value > 50000 else writer_page_2
                writer.writerow(
                    {
                        TARGET_TWITTER: twitter_handles[donor],
                        # replace "|" characters to avoid messing with markdown tables
                        TARGET_DONOR: donor.replace("|", "/"),
                        TARGET_TOTAL_DONATIONS: format_money(value),
                    }
                )

            # seek to 0 so we can read back the file.
            temp_csv_file_page_1.seek(0)
            temp_csv_file_page_2.seek(0)

            markdown_table_page_1 = Table.parse_csv(file=temp_csv_file_page_1)
            markdown_table_page_2 = Table.parse_csv(file=temp_csv_file_page_2)

            with open(TWITTER_MAPPING_MARKDOWN_FILE_PAGE_1, "w") as markdown_file:
                markdown_file.write(markdown_table_page_1.markdown())
            with open(TWITTER_MAPPING_MARKDOWN_FILE_PAGE_2, "w") as markdown_file:
                markdown_file.write(markdown_table_page_2.markdown())


#
# parties
#


def get_existing_parties() -> DefaultDict:
    parties = defaultdict(str)
    try:
        with open(PARTY_GROUPS_MARKDOWN_FILE) as markdown_file:
            reader = WhitespaceStrippingDictReader(f=markdown_file, delimiter="|")
            for row in reader:
                if "---" in row[TARGET_DONATION_MADE_TO]:
                    continue
                parties[row[TARGET_DONATION_MADE_TO]] = row[TARGET_PARTY]
    except FileNotFoundError:
        pass
    return parties


def build_party_groups_table():
    existing_parties = get_existing_parties()
    counter = Counter()
    with open(DONATIONS_FILE) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            counter.update({row[SOURCE_DONATION_MADE_TO]: int(row[SOURCE_VALUE])})

    with StringIO() as temp_csv_file:
        writer = csv.DictWriter(
            f=temp_csv_file,
            fieldnames=[TARGET_PARTY, TARGET_DONATION_MADE_TO, TARGET_TOTAL_DONATIONS],
        )
        writer.writeheader()
        for donation_made_to, value in counter.most_common():
            writer.writerow(
                {
                    TARGET_PARTY: existing_parties[donation_made_to],
                    # replace "|" characters to avoid messing with markdown tables
                    TARGET_DONATION_MADE_TO: donation_made_to.replace("|", "/"),
                    TARGET_TOTAL_DONATIONS: format_money(value),
                }
            )

        temp_csv_file.seek(0)

        markdown_table = Table.parse_csv(file=temp_csv_file)

        with open(PARTY_GROUPS_MARKDOWN_FILE, "w") as markdown_file:
            markdown_file.write(markdown_table.markdown())


if __name__ == "__main__":
    build_twitter_donor_table()
    build_party_groups_table()
