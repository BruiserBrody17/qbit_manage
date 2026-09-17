"""Tests for modules.config.Config — pure validation logic.

Uses object.__new__ to bypass __init__ (which requires a real config file and
running qBittorrent instance) and exercises validate_required_sections() directly.
"""

from __future__ import annotations

import pytest

from modules.config import Config
from modules.util import Failed
from modules.util import check as ConfigCheck


def _make_config(data: dict) -> Config:
    """Construct a Config with minimal state, bypassing __init__."""
    cfg = object.__new__(Config)
    cfg.data = data
    cfg._notify_calls = []
    cfg.notify = lambda text, function=None, critical=True: cfg._notify_calls.append(text)
    return cfg


def _make_nohardlinks_config(nohardlinks) -> Config:
    cfg = _make_config({"nohardlinks": nohardlinks})
    cfg.commands = {"tag_nohardlinks": True}
    return cfg


class TestValidateRequiredSections:
    """validate_required_sections() requires at least one of cat or tracker."""

    def test_valid_cat_section_passes(self):
        """A non-empty 'cat' section satisfies the validator."""
        cfg = _make_config({"cat": {"Movies": "/data/movies"}})
        cfg.validate_required_sections()

    def test_valid_tracker_section_passes(self):
        """A non-empty 'tracker' section satisfies the validator."""
        cfg = _make_config({"tracker": {"tracker1.example": {"tag": ["t1"]}}})
        cfg.validate_required_sections()

    def test_both_sections_present_and_non_empty_passes(self):
        cfg = _make_config(
            {
                "cat": {"Movies": "/data/movies"},
                "tracker": {"tracker1.example": {"tag": ["t1"]}},
            }
        )
        cfg.validate_required_sections()

    def test_tracker_only_with_empty_cat_passes(self):
        """Tracker-only configs are valid when cat is empty (production default injection)."""
        cfg = _make_config(
            {
                "cat": {},
                "tracker": {"tracker1.example": {"tag": ["t1"]}},
            }
        )
        cfg.validate_required_sections()

    def test_cat_only_with_empty_tracker_passes(self):
        """Category-only configs are valid when tracker is empty (production default injection)."""
        cfg = _make_config(
            {
                "cat": {"Movies": "/data/movies"},
                "tracker": {},
            }
        )
        cfg.validate_required_sections()

    def test_both_sections_empty_raises(self):
        cfg = _make_config({"cat": {}, "tracker": {}})
        with pytest.raises(Failed, match="Both"):
            cfg.validate_required_sections()

    def test_both_sections_missing_raises(self):
        cfg = _make_config({})
        with pytest.raises(Failed, match="Both"):
            cfg.validate_required_sections()

    def test_notify_called_before_raise_when_both_empty(self):
        cfg = _make_config({"cat": {}, "tracker": {}})
        with pytest.raises(Failed):
            cfg.validate_required_sections()
        assert len(cfg._notify_calls) == 1
        assert "Both" in cfg._notify_calls[0]


class TestProcessConfigNohardlinks:
    def test_legacy_list_defaults_ignore_category_dir_to_false(self):
        cfg = _make_nohardlinks_config(["Movies"])

        cfg.process_config_nohardlinks()

        assert cfg.nohardlinks["Movies"]["ignore_category_dir"] is False

    @pytest.mark.parametrize("category_config", [None, {}])
    def test_empty_category_defaults_ignore_category_dir_to_false(self, category_config):
        cfg = _make_nohardlinks_config({"Movies": category_config})

        cfg.process_config_nohardlinks()

        assert cfg.nohardlinks["Movies"]["ignore_category_dir"] is False

    def test_explicit_ignore_category_dir_is_preserved(self):
        cfg = _make_nohardlinks_config({"Movies": {"ignore_category_dir": True}})

        cfg.process_config_nohardlinks()

        assert cfg.nohardlinks["Movies"]["ignore_category_dir"] is True

    def test_legacy_list_of_objects_preserves_ignore_category_dir(self):
        cfg = _make_nohardlinks_config([{"Movies": {"ignore_category_dir": True}}])

        cfg.process_config_nohardlinks()

        assert cfg.nohardlinks["Movies"]["ignore_category_dir"] is True

    def test_non_boolean_ignore_category_dir_is_rejected(self):
        cfg = _make_nohardlinks_config({"Movies": {"ignore_category_dir": "true"}})

        with pytest.raises(Failed, match="ignore_category_dir must be a boolean type"):
            cfg.process_config_nohardlinks()


class TestProcessConfigRateLimits:
    """process_config_rate_limits() announces the active limits at startup."""

    def _make_rate_limit_config(self, rate_limit: dict) -> Config:
        cfg = _make_config({"rate_limit": rate_limit})
        cfg.util = ConfigCheck(cfg)
        return cfg

    def test_disabled_by_default_is_a_noop(self):
        cfg = self._make_rate_limit_config({"enabled": False})

        cfg.process_config_rate_limits()

        assert cfg.qbt_rate_limiter.enabled is False
        assert cfg.webhook_rate_limiter.enabled is False

    def test_enabled_logs_configured_limits(self, monkeypatch):
        cfg = self._make_rate_limit_config(
            {
                "enabled": True,
                "qbt_requests_per_second": 15,
                "qbt_burst": 30,
                "webhook_requests_per_second": 3,
                "webhook_burst": 6,
            }
        )
        logged = []
        monkeypatch.setattr("modules.config.logger.info", lambda msg: logged.append(msg))

        cfg.process_config_rate_limits()

        assert cfg.qbt_rate_limiter.enabled is True
        assert cfg.webhook_rate_limiter.enabled is True
        assert any("15 req/s (burst 30)" in msg and "3 req/s (burst 6)" in msg for msg in logged)
