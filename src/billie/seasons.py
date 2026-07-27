"""Billie's seasonal awareness — because even platypuses observe holidays.

Defines themed seasons with date ranges and words, plus auto-detection
of the current season based on today's date.

Ordering matters: the first calendar season whose range contains today wins.
Precise single-day holidays are listed before the wider/movable seasons (most
notably the dynamic Easter window) so a specific day beats a broad one; billing
is day-of-month and is always checked last.
"""

from __future__ import annotations

import datetime
from datetime import date, timedelta

from dateutil.easter import easter

SEASONS: dict[str, dict] = {
    "valentine": {
        "dates": ((2, 12), (2, 15)),
        "pic": "billie-valentine.txt",
        "words": (
            "commitment issues",
            "reserved instances you never committed to",
            "on-demand relationship",
            "savings plan proposal",
            "your love language is yaml",
            "emotional availability SLA",
            "it's not you it's your architecture",
            "swipe left on that EC2 instance",
            "long-term commitment discount",
            "no I will not be your plus-one to the vendor dinner",
        ),
    },
    "newyear": {
        "dates": ((1, 1), (1, 1)),
        "pic": "billie-newyear.txt",
        "words": (
            "new year, same legacy stack",
            "resolution: right-size exactly zero instances",
            "the ball dropped and so did prod",
            "auld lang syne, auld lang bill",
            "this year we migrate off us-east-1 (we won't)",
            "midnight countdown, same cadence as the outage timer",
            "new year's resolution: read the AWS bill (never happens)",
            "another trip around the sun, still billed hourly",
            "happy new year, the reserved instances renewed themselves",
        ),
    },
    "groundhog": {
        "dates": ((2, 2), (2, 2)),
        "pic": "billie-groundhog.txt",
        "words": (
            "six more weeks of this outage",
            "the platypus saw its shadow: prod stays down",
            "waking up to the same incident every single morning",
            "Punxsutawney Phil doesn't do on-call, lucky him",
            "it's the same deploy again. and again. and again",
            "predicting winter with the accuracy of a cost forecast",
            "the alert fired yesterday, fires today, will fire tomorrow",
            "groundhog day, but the pager is the rodent",
            "shadow detected, rollback initiated",
        ),
    },
    "pizza": {
        "dates": ((2, 9), (2, 9)),
        "pic": "billie-pizza.txt",
        "words": (
            "another slice of the bill",
            "pineapple on pizza, EBS in the wrong AZ: both crimes",
            "deep dish, deep technical debt",
            "the whole pie is data transfer charges",
            "delivery in 30 minutes or the SLA is free",
            "eight slices, twelve microservices, one regret",
            "extra cheese, extra egress",
            "who ordered the anchovies and the reserved instances",
            "cold pizza, colder standby replica",
        ),
    },
    "piday": {
        "dates": ((3, 14), (3, 14)),
        "pic": "billie-piday.txt",
        "words": (
            "3.14159 and your bill keeps going too",
            "irrational number, irrational spend",
            "the circumference of your blast radius",
            "pi never ends, neither does the data transfer line item",
            "a slice of pi, a slice of the budget",
            "3.14: also the number of nines you didn't hit",
            "circular dependencies, circular logic, circular pie",
            "happy pi day, your latency is still transcendental",
        ),
    },
    "backup": {
        "dates": ((3, 31), (3, 31)),
        "pic": "billie-backup.txt",
        "words": (
            "you did test the restore, right?",
            "the 3-2-1 backup rule, zero of which you followed",
            "the backup ran; the restore is a rumor",
            "snapshot everything, trust nothing",
            "the day before you find out it wasn't backed up",
            "S3 versioning you swore you enabled",
            "cross-region replication or crossed fingers",
            "your backup is one ransomware away from mattering",
            "RPO, RTO, and RIP",
        ),
    },
    "aprilfools": {
        "dates": ((4, 1), (4, 1)),
        "pic": "billie-aprilfools.txt",
        "words": (
            "the free tier was the joke all along",
            "surprise! it's a data transfer charge",
            "this is not a drill (it's an outage)",
            "gotcha: the reserved instance was on-demand",
            "the prank is the bill and it isn't funny",
            "no, this pricing page is not satire",
            "whoopee cushion energy, production impact",
            "the only fool here approved the spend",
            "april fools, the region really is down",
        ),
    },
    "starwars": {
        "dates": ((5, 4), (5, 4)),
        "pic": "billie-starwars.txt",
        "words": (
            "may the fourth be with your budget",
            "these aren't the instances you're looking for",
            "the dark side has better margins",
            "your data center is no moon",
            "the bill strikes back",
            "help me Cost Explorer, you're my only hope",
            "a long time ago in a region far, far away (us-east-1)",
            "the force is strong, the egress stronger",
            "do or do not right-size, there is no try",
        ),
    },
    "towel": {
        "dates": ((5, 25), (5, 25)),
        "pic": "billie-towel.txt",
        "words": (
            "don't panic (the bill is only mostly harmless)",
            "42 is the answer, the question was the AWS invoice",
            "always know where your towel and your root creds are",
            "the infinite improbability of a lower bill",
            "so long, and thanks for all the egress",
            "mostly harmless, unlike your NAT gateway",
            "hitchhiking across three availability zones",
            "the Guide says the cloud is someone else's computer",
        ),
    },
    "cheese": {
        "dates": ((6, 4), (6, 4)),
        "pic": "billie-cheese.txt",
        "words": (
            "say cheese, then say the bill out loud",
            "aged like cheddar, priced like saffron",
            "the moon is made of it, the invoice of surprises",
            "extra gouda, extra spend",
            "the swiss cheese security model",
            "this architecture is a little too cheesy",
            "brie-lliant, another data transfer charge",
            "holes in the cheese, holes in the budget",
            "nacho average outage",
        ),
    },
    "birthday": {
        "dates": ((7, 28), (7, 28)),
        "pic": "billie-birthday.txt",
        "words": (
            "another year closer to your reserved instances expiring",
            "happy birthday, the bill is still your problem",
            "blow out the candles, on-call is still lit",
            "you depreciate faster than a reserved instance",
            "make a wish (it will not fix us-east-1)",
            "one year older, same untagged resources",
            "the candles cost more than a t2.micro",
            "surprise party, surprise egress charges",
            "your gift is another service you didn't ask for",
            "congratulations on surviving another billing cycle",
        ),
    },
    "programmers": {
        "dates": ((9, 13), (9, 13)),
        "pic": "billie-programmers.txt",
        "words": (
            "the 256th day, because of course it's 256",
            "off by one and over by a million dollars",
            "works on my machine, bills on yours",
            "it's not a bug, it's an unbudgeted feature",
            "semicolons are free, the Lambda invocations are not",
            "zero-indexed days, one-indexed regrets",
            "commit, push, deploy, panic",
            "the 256th day: overflow into the next billing tier",
            "hello world, goodbye budget",
        ),
    },
    "pirate": {
        "dates": ((9, 19), (9, 19)),
        "pic": "billie-pirate.txt",
        "words": (
            "arrr, yer S3 bucket be public",
            "shiver me timbers, the bill be cursed",
            "walk the plank of technical debt",
            "yo ho ho and a bottle of egress",
            "there be treasure in them thar untagged resources",
            "dead men tell no tales, dead instances still bill",
            "X marks the spot where the budget went down",
            "avast, the CFO be boarding",
        ),
    },
    "coffee": {
        "dates": ((10, 1), (10, 1)),
        "pic": "billie-coffee.txt",
        "words": (
            "the on-call fuel",
            "but first, coffee; then, the bill",
            "cold brew, colder billing forecast",
            "espresso yourself, the budget won't",
            "another cup, another incident",
            "runs on caffeine and reserved instances",
            "the coffee is free, the data transfer is not",
            "decaf is for people whose prod is stable",
            "that's a latte spend this month",
        ),
    },
    "easter": {
        "dates": "dynamic",
        "pic": "billie-easter.txt",
        "words": (
            "orphaned resources",
            "egg hunt in the billing console",
            "zombie instances",
            "risen from deprecated",
            "rolling back the stone on prod",
            "resurrection of that dead project",
            "he is risen and so is your bill",
            "miracle of uptime",
            "three days to recover from that deploy",
            "hiding costs in nested accounts",
        ),
    },
    "earth": {
        "dates": ((4, 16), (4, 22)),
        "pic": "billie-earth.txt",
        "words": (
            "carbon footprint of us-east-1",
            "sustainable architecture",
            "green computing",
            "reduce reuse re:Invent",
            "your region's emissions",
            "planet-scale waste",
            "the cloud is someone else's coal plant",
            "eco-friendly instance right-sizing",
            "mother earth didn't ask for your Lambda functions",
            "compost your deprecated services",
        ),
    },
    "halloween": {
        "dates": ((10, 17), (10, 31)),
        "pic": "billie-halloween.txt",
        "words": (
            "haunted legacy code",
            "skeleton crew on-call",
            "ghost instances",
            "the horror of untagged resources",
            "trick or treat yourself to monitoring",
            "jump scare from the billing alert",
            "zombie processes",
            "crypt keeper of the monolith",
            "something wicked in the deploy pipeline",
            "the call is coming from inside the VPC",
        ),
    },
    "reinvent": {
        "dates": ((11, 25), (12, 6)),
        "pic": "billie-reinvent.txt",
        "words": (
            "keynote bingo",
            "expo hall lanyard rash",
            "another AI service",
            "swag bag regrets",
            "the party circuit",
            "Matt Garman's slide deck",
            "day 3 voice loss",
            "surprise service announcement",
            "that hallway track conversation",
            "booth duty despair",
        ),
    },
    "xmas": {
        "dates": ((12, 14), (12, 26)),
        "pic": "billie-xmas.txt",
        "words": (
            "gift of another AWS service",
            "twelve days of deprecation notices",
            "all I want is uptime",
            "secret santa budget overrun",
            "naughty list of unpatched instances",
            "silent night in the on-call channel",
            "jingle bills jingle bills",
            "partridge in a CloudFormation stack",
            "deck the halls with monitoring",
            "ho ho holy outage",
        ),
    },
    "billing": {
        "days": (1, 2, 3),
        "pic": "billie-billing.txt",
        "words": (
            "the bill just dropped",
            "invoice attachment anxiety",
            "cost explorer doom scroll",
            "month-over-month dread",
            "surprise data transfer charges",
            "who approved this spend",
            "budget alert notification",
            "the CFO wants to talk",
            "line item horror",
            "forecast vs actual: a tragedy",
        ),
    },
}


def _easter_range(year: int) -> tuple[date, date]:
    """Return the (start, end) inclusive date range for Easter season.

    Spans from 7 days before Easter Sunday through 1 day after.
    """
    sunday = easter(year)
    return (sunday - timedelta(days=7), sunday + timedelta(days=1))


def _check_fixed_dates(today: date, season: dict) -> bool:
    """Check whether today falls within a fixed-date season range."""
    (start_month, start_day), (end_month, end_day) = season["dates"]
    start = date(today.year, start_month, start_day)
    end = date(today.year, end_month, end_day)
    return start <= today <= end


def get_current_season(today: date | None = None) -> str | None:
    """Detect the current season based on a date.

    Checks calendar seasons first (everything except billing) in definition
    order; the first match wins. Then checks billing last (day-of-month).
    Returns None if no season matches.
    """
    if today is None:
        today = datetime.datetime.now(tz=datetime.timezone.utc).date()

    for name, season in SEASONS.items():
        if name == "billing":
            continue

        if season["dates"] == "dynamic":
            start, end = _easter_range(today.year)
            if start <= today <= end:
                return name
        elif _check_fixed_dates(today, season):
            return name

    billing = SEASONS["billing"]
    if today.day in billing["days"]:
        return "billing"

    return None
