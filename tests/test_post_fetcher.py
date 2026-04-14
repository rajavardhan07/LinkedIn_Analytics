"""
Unit tests for the post fetcher pipeline.

Uses mock data — no real API calls needed.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.post import PostData, ReactionBreakdown, MediaItem

# Load mock data
MOCK_DIR = Path(__file__).parent / "mock_responses"


def _load_mock(filename: str) -> dict:
    with open(MOCK_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


class TestPostDataModel:
    """Test the Pydantic PostData model validation."""

    def test_valid_post(self):
        """A well-formed post should parse without errors."""
        post = PostData(
            company="Test Corp",
            text="Hello world! #testing #ai",
            post_type="text",
            timestamp=datetime.now(timezone.utc),
            likes=100,
            comments=10,
            shares=5,
            hashtags=["testing", "ai"],
        )
        assert post.company == "Test Corp"
        assert post.engagement_score == 115
        assert len(post.hashtags) == 2

    def test_null_safe_fields(self):
        """Null values should be handled gracefully."""
        post = PostData(
            company="Test Corp",
            text=None,
            post_type=None,
            timestamp=datetime.now(timezone.utc),
            likes=None,
            comments=None,
            shares=None,
            hashtags=None,
        )
        assert post.text == ""
        assert post.post_type == "text"
        assert post.likes == 0
        assert post.comments == 0
        assert post.shares == 0
        assert post.hashtags == []

    def test_hashtag_normalization(self):
        """Hashtags should be lowercase and deduplicated."""
        post = PostData(
            company="Test Corp",
            timestamp=datetime.now(timezone.utc),
            hashtags=["#AI", "#ai", "#Innovation", "#INNOVATION"],
        )
        assert post.hashtags == ["ai", "innovation"]

    def test_post_type_mapping(self):
        """Known post types should map correctly."""
        for raw, expected in [
            ("photo", "image"),
            ("VIDEO", "video"),
            ("article", "article"),
            ("native_document", "document"),
            ("repost", "repost"),
            ("unknown_type", "text"),
            (None, "text"),
        ]:
            post = PostData(
                company="Test Corp",
                timestamp=datetime.now(timezone.utc),
                post_type=raw,
            )
            assert post.post_type == expected, f"{raw} -> {post.post_type} (expected {expected})"

    def test_negative_metrics_clamped(self):
        """Negative engagement values should be clamped to 0."""
        post = PostData(
            company="Test Corp",
            timestamp=datetime.now(timezone.utc),
            likes=-5,
            comments=-10,
        )
        assert post.likes == 0
        assert post.comments == 0

    def test_extract_hashtags_from_text(self):
        """Should extract hashtags from post body text."""
        tags = PostData.extract_hashtags(
            "Excited about #AI and #MachineLearning! #ai is great"
        )
        assert "ai" in tags
        assert "machinelearning" in tags
        # Should be deduplicated
        assert tags.count("ai") == 1

    def test_to_dict_serialization(self):
        """to_dict should produce a JSON-safe dict with computed fields."""
        post = PostData(
            company="Test Corp",
            text="Hello",
            timestamp=datetime(2026, 4, 10, tzinfo=timezone.utc),
            likes=5,
            follower_count=1000,
        )
        d = post.to_dict()
        assert isinstance(d["timestamp"], str)
        assert d["company"] == "Test Corp"
        assert d["likes"] == 5
        assert d["engagement_score"] == 5
        assert d["engagement_rate"] == 0.5
        assert d["has_media"] is False
        assert d["media_count"] == 0


class TestNewFields:
    """Test the enhanced Phase 1 fields."""

    def test_reaction_breakdown(self):
        """Reaction breakdown should store per-type counts."""
        reactions = ReactionBreakdown(
            like=245, praise=35, empathy=21, interest=1
        )
        assert reactions.like == 245
        assert reactions.praise == 35
        assert reactions.empathy == 21
        assert reactions.interest == 1
        assert reactions.appreciation == 0
        assert reactions.entertainment == 0

    def test_reaction_breakdown_null_safety(self):
        """Null reaction values should default to 0."""
        reactions = ReactionBreakdown(like=None, praise=None)
        assert reactions.like == 0
        assert reactions.praise == 0

    def test_media_item(self):
        """MediaItem should store type and URL."""
        item = MediaItem(
            type="image",
            url="https://media.licdn.com/test.jpg",
            description="Office photo",
        )
        assert item.type == "image"
        assert "licdn.com" in item.url

    def test_post_with_all_new_fields(self):
        """Post with all enhanced fields should work."""
        post = PostData(
            company="Vanguard India",
            text="Welcome aboard!",
            timestamp=datetime.now(timezone.utc),
            likes=302,
            comments=15,
            shares=0,
            reactions=ReactionBreakdown(like=245, praise=35, empathy=21, interest=1),
            post_url="https://linkedin.com/feed/update/urn:li:activity:12345",
            post_urn="urn:li:activity:12345",
            media_urls=["https://media.licdn.com/img1.jpg"],
            media_items=[
                MediaItem(type="image", url="https://media.licdn.com/img1.jpg")
            ],
            follower_count=7014,
            is_repost=False,
            is_edited=False,
            author_name="Vanguard India",
            author_urn="urn:li:fsd_company:108291840",
        )

        assert post.engagement_score == 317
        assert post.engagement_rate == (317 / 7014) * 100
        assert post.has_media is True
        assert post.media_count == 1
        assert post.reactions.like == 245
        assert post.is_repost is False
        assert post.follower_count == 7014

    def test_engagement_rate_zero_followers(self):
        """Engagement rate should be 0 when follower count is 0."""
        post = PostData(
            company="Test",
            timestamp=datetime.now(timezone.utc),
            likes=100,
            follower_count=0,
        )
        assert post.engagement_rate == 0.0

    def test_is_repost_flag(self):
        """Repost detection flag."""
        post = PostData(
            company="Test",
            timestamp=datetime.now(timezone.utc),
            is_repost=True,
            post_type="repost",
        )
        assert post.is_repost is True
        assert post.post_type == "repost"


class TestMockDataNormalization:
    """Test normalization of realistic mock API responses."""

    def test_normalize_mock_posts(self):
        """All mock posts should normalize successfully."""
        mock = _load_mock("company_posts.json")
        raw_posts = mock["data"]

        normalized = []
        for raw in raw_posts:
            text = raw.get("text", "")
            timestamp_ms = raw.get("timestamp", 0)
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            metrics = raw.get("metrics", {})

            hashtags = raw.get("hashtags") or PostData.extract_hashtags(text)

            post = PostData(
                company="Vanguard India",
                text=text,
                post_type=raw.get("type", "text"),
                timestamp=timestamp,
                likes=metrics.get("likes", 0),
                comments=metrics.get("comments", 0),
                shares=metrics.get("shares", 0),
                hashtags=hashtags,
            )
            normalized.append(post)

        assert len(normalized) == 10
        # First post should have high engagement
        assert normalized[0].engagement_score > 1000
        # Check hashtags were extracted
        assert len(normalized[0].hashtags) > 0

    def test_engagement_scores(self):
        """Verify engagement scores compute correctly."""
        mock = _load_mock("company_posts.json")
        raw = mock["data"][0]
        m = raw["metrics"]

        expected_score = m["likes"] + m["comments"] + m["shares"]

        post = PostData(
            company="Test",
            text=raw["text"],
            timestamp=datetime.now(timezone.utc),
            likes=m["likes"],
            comments=m["comments"],
            shares=m["shares"],
        )
        assert post.engagement_score == expected_score
