# AusPol Donations Twitter Bot

A Twitter bot which replies with political donations made by donor mentioned in tweet.

Example tweet the bot will respond to:

`Hey @AusPolDonationsBot tell me what political donations @SomeCompany has made please.`

The bot will reply with the donations of the first twitter handle mentioned in the tweet which is in the database (see below).

## Dataset

The bot requires two datasets on top of the data available from the AEC, one to map twitter handles to donors, and the other to map donation recipients back to political parties. We appreciate any help in completing & checking these datasets, which can be done with a pull request.

### Mapping twitter handles to donors:

[Twitter donors table: page 1](data/tables/twitter_donors_page_1.md)

[Twitter donors table: page 2](data/tables/twitter_donors_page_2.md)

### Mapping donation recipeints to political parties.

[Parties table](data/tables/parties.md)

## Source data (AEC)

AEC data is available at https://transparency.aec.gov.au/

A copy of the 2022 dataset is [here](data/src/2022)

## Contributing.

To contribute, please submit changes to the tables as a pull request.
