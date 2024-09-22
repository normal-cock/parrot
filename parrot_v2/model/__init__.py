from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .core import (
    Word, Meaning, ReviewPlan, AddCounter, ReviewPlanType, ReviewStatus, ReviewStage, ERLookupRecord,
    ER_REVIEW_RANGE_DAY)
from .player import Item