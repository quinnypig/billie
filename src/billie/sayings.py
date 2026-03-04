"""Billie's words, sayings, and static data.

Billie the Platypus has opinions. Mostly unimpressed ones.
"""

import random
from collections import deque


class BillieDeque(deque):
    """A rotating deque that shuffles to avoid repetition."""

    def __init__(self, *args, **_kwargs):
        self.index = 0
        args = list(args)
        random.shuffle(args)
        super().__init__(args)

    def get(self):
        """Get one item, rotating through the shuffled collection."""
        self.index += 1
        if self.index == len(self):
            self.shuffle()
        self.rotate(1)
        try:
            return self[0]
        except IndexError:
            return "*judges silently*"

    def extend(self, iterable):
        """Extend and shuffle."""
        super().extend(iterable)
        self.shuffle()

    def shuffle(self):
        """Shuffle the deque contents."""
        args = list(self)
        random.shuffle(args)
        self.clear()
        super().__init__(args)


PREFIXES = BillieDeque(
    "honestly",
    "look",
    "sigh",
    "ugh",
    "behold",
    "apparently",
    "cool story about",
    "fascinating",
    "riveting",
    "oh great more",
    "truly iconic",
    "I'll see what I can do about",
    "got your email about",
    "the audacity of",
    "technically professional",
    "I hope this finds you before I do re:",
    "exhausting take on",
    "makes me want to lie down re:",
    "I have feelings about",
    "the answer is no re:",
    "I get it but also no re:",
)

WORD_LIST = [
    "your AWS bill",
    "reserved instances",
    "savings plans",
    "S3 bucket policies",
    "IAM permissions",
    "the cloud",
    "your cloud bill",
    "cost optimization",
    "data transfer charges",
    "egress fees",
    "PR pitches",
    "cold outreach",
    "that vendor email",
    "observability platforms",
    "the inbox",
    "another podcast pitch",
    "thought leadership",
    "pick your brain requests",
    "your LinkedIn DMs",
    "that sales deck",
    "multi-cloud strategy",
    "FinOps",
    "kubernetes clusters",
    "serverless",
    "your tagging strategy",
    "us-east-1",
    "the billing console",
    "cost allocation tags",
    "EC2 instances nobody uses",
    "orphaned EBS volumes",
    "unattached elastic IPs",
    "that sponsorship offer",
    "CloudFormation drift",
    "terraform state files",
    "your security posture",
    "cross-account access",
    "that compliance audit",
    "the org trail",
    "whoever named these services",
    "your support plan",
    "enterprise agreements",
    "the re:Invent keynote",
    "another AWS region",
    "your architecture diagram",
    "that outage postmortem",
    "the on-call rotation",
    "legacy migration",
    "lift and shift",
    "the last email",
    "per my last email",
    "Corey's schedule",
]

SUFFIXES = BillieDeque(
    "obviously",
    "I guess",
    "whatever",
    "sure jan",
    "cool cool cool",
    "thrilling",
    "this is exhausting",
    "I stopped caring",
    "technically",
    "from my burrow",
    "I have seen things",
    "the answer is still no",
    "don't @ me",
    "I'll forward it never",
)

# Colors tuned for dark terminals - same palette approach as doge
COLORS = BillieDeque(
    *(
        int(x)
        for x in """
        23 24 25 26 27 29 30 31 32 33 35 36 37 38 39 41 42 43 44 45 47 48 49 50
        51 58 59 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83
        84 85 86 87 88 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109
        110 111 112 113 114 115 116 117 118 119 120 121 122 123 130 131 132 133
        134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151
        152 153 154 155 156 157 158 159 162 166 167 168 169 170 171 172 173 174
        175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192
        193 194 195 197 202 203 204 205 206 207 208 209 210 211 212 213 214 215
        216 217 218 219 220 221 222 223 224 225 226 227 228""".split()
    )
)
