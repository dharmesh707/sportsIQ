"""
Shared enums and small types used across schemas.

CONTRACT RULE #2: sport_type is an exact, closed enum. This is the ONLY place
it is defined. Every router, service, and ml/sports/<sport>/ module imports
SportType from here — never retype the string literals elsewhere.
"""

from enum import Enum


class SportType(str, Enum):
    BADMINTON = "badminton"
    TENNIS = "tennis"
    TABLE_TENNIS = "table_tennis"
    CRICKET_BOWLING = "cricket_bowling"
    ARCHERY = "archery"


class FaultType(str, Enum):
    HARD = "hard"
    SOFT = "soft"
