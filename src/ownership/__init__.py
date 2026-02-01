"""
Ownership inference module.

Analyzes Jira, GitHub, and Slack data to determine:
- Who owns specific code/features
- Who has expertise in certain areas
- Who to contact for specific tasks
"""

from src.ownership.analyzer import OwnershipAnalyzer, ownership_analyzer
from src.ownership.ranker import ExpertiseRanker, RankedCandidate
from src.ownership.recommender import OwnershipRecommender, ContactRecommendation

__all__ = [
    "OwnershipAnalyzer",
    "ownership_analyzer",
    "ExpertiseRanker",
    "RankedCandidate",
    "OwnershipRecommender",
    "ContactRecommendation",
]
