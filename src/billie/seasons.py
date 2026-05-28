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
    "leap_day": {
        "dates": "dynamic",
        "pic": "billie-leap-day.txt",
        "words": (
            "the bug that hid since 2024",
            "cron that fires every four years",
            "one bonus day of data transfer charges",
            "february has opinions",
            "the 29th that shouldn't exist",
            "reserved instance math says nope",
            "off-by-one-day in your scheduler",
            "happy quadrennial outage",
            "timestamp math is fake and you know it",
            "surprise bill on a date that barely exists",
        ),
    },
    "pi_day": {
        "dates": ((3, 14), (3, 14)),
        "pic": "billie-pi-day.txt",
        "words": (
            "happy birthday S3 you leaky bucket",
            "3.14% uptime SLA",
            "infinite loops taste like pi",
            "raspberry pi vs EC2: both overhyped",
            "circular dependency in your architecture",
            "serving 3.14159 nines of availability",
            "eating pi while the bill compounds",
            "tau would've been cheaper",
            "S3 turns another year older you turn poorer",
            "irrational costs for rational workloads",
        ),
    },
    "dst": {
        "dates": "dynamic",
        "pic": "billie-dst.txt",
        "words": (
            "cron job fired twice this morning",
            "scheduled lambda skipped an hour",
            "timezone bug in your audit logs",
            "daylight saving your cloud bill (it won't)",
            "it is simultaneously 2am and 3am",
            "calendar invite apocalypse",
            "UTC users are laughing at us",
            "your TTL just got weird",
            "dst bug: filed, won't fix",
            "the hour that wasn't and the hour that was twice",
        ),
    },
    "april_fools": {
        "dates": ((4, 1), (4, 1)),
        "pic": "billie-april-fools.txt",
        "words": (
            "no this is a real service announcement",
            "AWS joking about deprecation again",
            "the prank is the invoice",
            "surprise us-east-1 incident, not a bit",
            "gpt-but-for-egg-hunts",
            "this outage is not a drill and not a joke",
            "april first feature release terrifies me",
            "every day is april fools in the console",
            "region launch or fake? you decide",
            "the real prank was the data transfer line item",
        ),
    },
    "tax_day": {
        "dates": ((4, 10), (4, 15)),
        "pic": "billie-tax-day.txt",
        "words": (
            "write off that data transfer",
            "the audit trail is literally CloudTrail",
            "deductible reserved instances",
            "1099 from your EC2 side hustle",
            "capital gains on stale snapshots",
            "amortization of technical debt",
            "schedule C for shadow IT",
            "the IRS doesn't care about your k8s bill",
            "accrual basis meets billing alerts",
            "tax shelter of spot instances",
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
    "heat_wave": {
        "dates": ((7, 20), (8, 10)),
        "pic": "billie-heat-wave.txt",
        "words": (
            "us-east-1 is literally sweating",
            "thermal throttling in the data center",
            "cooling costs eclipsing compute costs",
            "the A/C is the real infra",
            "liquid cooling won't save this team",
            "sustainability report: on fire",
            "fan noise meditation",
            "your laptop is a space heater now",
            "ambient rack temp says no",
            "swamp coolers for the cloud",
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
        "dates": ((11, 23), (12, 6)),
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
            "thankful for idempotency this year",
            "cornucopia of service announcements",
            "gravy on the keynote",
            "stuffing booth giveaways into my carry-on",
            "black friday doorbusters on savings plans",
            "cyber monday load testing in prod",
            "pass the cranberry sauce and the SLA",
            "wishbone of not getting paged",
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
    "friday13": {
        "dates": "dynamic",
        "pic": "billie-friday13.txt",
        "words": (
            "cursed friday deploy",
            "production pushes at 4:45pm",
            "the migration that dare not speak its name",
            "thirteenth commit breaks everything",
            "untested rollback plan",
            "unlucky sharding key",
            "skip-standup-for-this-deploy energy",
            "friday freeze ignored",
            "the one who pushes on friday the 13th",
            "what could possibly go wrong",
        ),
    },
    "billing": {
        "days": (1, 2, 3),
        "pic": "billie-billing.txt",
        "words": (
            "invoice PDF arrived with teeth",
            "NAT gateway egress: the unkillable",
            "cross-AZ traffic whispered your name",
            "data transfer compounds like interest in hell",
            "the eldritch geometry of Cost Explorer",
            "untagged resources multiplied in the night",
            "an Elastic IP you orphaned in 2019 still pings",
            "phantom EBS volumes draining the region",
            "the $0.00 line item that billed anyway",
            "an S3 bucket in a region you cannot access",
            "the CFO has printed the bill and laminated it",
            "a support case opened itself while you slept",
            "CloudWatch Logs ingestion that eats light",
            "your savings plan coverage dropped again, unprompted",
            "a closed account still generating charges, somehow",
        ),
    },
}


def _easter_range(year: int) -> tuple[date, date]:
    """Return the (start, end) inclusive date range for Easter season.

    Spans from 7 days before Easter Sunday through 1 day after.
    """
    sunday = easter(year)
    return (sunday - timedelta(days=7), sunday + timedelta(days=1))


def _is_friday_13th(today: date) -> bool:
    """Check whether today is Friday the 13th — weekday 4 is Friday."""
    return today.day == 13 and today.weekday() == 4  # noqa: PLR2004


def _dst_transition_dates(year: int) -> tuple[date, date, date, date]:
    """Return US DST transition Sundays and their following Mondays.

    Spring forward: second Sunday of March.
    Fall back: first Sunday of November.
    """
    march_first = date(year, 3, 1)
    spring = march_first + timedelta(days=(6 - march_first.weekday()) % 7 + 7)
    nov_first = date(year, 11, 1)
    fall = nov_first + timedelta(days=(6 - nov_first.weekday()) % 7)
    return (spring, spring + timedelta(days=1), fall, fall + timedelta(days=1))


def _is_dst_transition(today: date) -> bool:
    """Check whether today is the Sunday or Monday of a US DST transition."""
    return today in _dst_transition_dates(today.year)


def _is_leap_day(today: date) -> bool:
    """Check whether today is Feb 29 (only exists in leap years)."""
    return today.month == 2 and today.day == 29  # noqa: PLR2004


_DYNAMIC_CHECKS = {
    "easter": lambda d: _easter_range(d.year)[0] <= d <= _easter_range(d.year)[1],
    "friday13": _is_friday_13th,
    "dst": _is_dst_transition,
    "leap_day": _is_leap_day,
}


def _check_fixed_dates(today: date, season: dict) -> bool:
    """Check whether today falls within a fixed-date season range."""
    (start_month, start_day), (end_month, end_day) = season["dates"]
    start = date(today.year, start_month, start_day)
    end = date(today.year, end_month, end_day)
    return start <= today <= end


def get_current_season(today: date | None = None) -> str | None:
    """Detect the current season based on a date.

    Checks calendar seasons first (everything except billing), in dict
    order — first match wins. Then checks billing last (day-of-month).
    Returns None if no season matches.
    """
    if today is None:
        today = datetime.datetime.now(tz=datetime.timezone.utc).date()

    for name, season in SEASONS.items():
        if name == "billing":
            continue

        if season["dates"] == "dynamic":
            check = _DYNAMIC_CHECKS.get(name)
            if check and check(today):
                return name
        elif _check_fixed_dates(today, season):
            return name

    billing = SEASONS["billing"]
    if today.day in billing["days"]:
        return "billing"

    return None
