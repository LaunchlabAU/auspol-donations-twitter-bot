# @AusPolDonations : Australian Political Donations Twitter Bot

A Twitter bot which replies with political donations made by donor mentioned in tweet.

Example tweet the bot will respond to:

`Hey @AusPolDonations tell me what political donations @SomeCompany has made please.`

The bot will reply with the donations of the first twitter handle mentioned in the tweet which is in the database (see below).

## Dataset

The bot requires two datasets on top of the data available from the AEC, one to map twitter handles to donors, and the other to map donation recipients back to political parties. We appreciate any help in completing & checking these datasets, which can be done by clicking on the pencil icon to the top-right of a table.

### Mapping twitter handles to donors:

Please only submit changes to the "Twitter" column. To edit, click on the pencil icon at the top right of the table.

[Twitter donors table: page 1](data/tables/twitter_donors_page_1.md)

[Twitter donors table: page 2](data/tables/twitter_donors_page_2.md)

### Mapping donation recipients to political parties.

Please only submit changes to the "Party" column. To edit, click on the pencil icon at the top right of the table.

[Parties table](data/tables/parties.md)

We try to stick to party codes as per https://www.aec.gov.au/elections/federal_elections/election-codes.htm where possible, with the exception of some two-letter codes which are commonly expressed as 3 letter codes: NP -> NAT, and LP -> LIB. Using 3 letter codes helps to align the tables in the tweet.

## Source data (AEC)

AEC data is available at https://transparency.aec.gov.au/

A copy of the 2022 dataset is [here](data/src/2022)

## Contributing.

To contribute, please submit changes to the tables as a pull request. You can create a pull request by clicking on the pencil icon at the top right of a table, making the changes, then when you save the changes we will be able to merge them into the datatset. Once we merge in your changes, it will take about 10 minutes until the new dataset is live and in use by the bot.

If you want to discuss either details of the dataset or features/bugs of the project as a whole feel free to create an issue https://github.com/LaunchlabAU/auspol-donations-twitter-bot/issues
