"""Billie's seasonal awareness — because even platypuses observe holidays.

Defines themed seasons with date ranges and words, plus auto-detection
of the current season based on today's date.
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

    Checks calendar seasons first (everything except billing). First match
    wins. Then checks billing last (day-of-month). Returns None if no
    season matches.
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
