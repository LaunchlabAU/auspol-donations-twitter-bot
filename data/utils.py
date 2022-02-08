import csv


SOURCE_DONOR_NAME = "Donor Name"
SOURCE_VALUE = "Value"
SOURCE_DONATION_MADE_TO = "Donation Made To"
SOURCE_FINANCIAL_YEAR = "Financial Year"

TARGET_TWITTER = "Twitter"
TARGET_DONOR = "Donor"
TARGET_TOTAL_DONATIONS = "Total Donations"

TARGET_PARTY = "Party"
TARGET_DONATION_MADE_TO = "Donation Made To"


class WhitespaceStrippingDictReader(csv.DictReader):
    # csv reader can remove leading whitespace but not trailing. We want to
    # remove both
    def __next__(self):
        next_ = super().__next__()
        return dict(map(lambda item: (item[0].strip(), item[1].strip()), next_.items()))
