#!/usr/bin/env python3
import os

import aws_cdk as cdk

from donationsbot.donationsbot_stack import DonationsbotStack


app = cdk.App()
DonationsbotStack(
    app,
    "DonationsbotStack",
    env=cdk.Environment(account="240067924203", region="ap-southeast-2"),
)

app.synth()
