"""Tests for the suggests.scripts CLI entry points."""

import pytest

from suggests.scripts.plot import build_parser, main


class TestPlotParser:
    def test_defaults(self):
        args = build_parser().parse_args(["--edges", "edges.csv", "--root", "dog"])
        assert args.edges == "edges.csv"
        assert args.root == "dog"
        assert args.save_to == ""
        assert args.label_col == "target_add"
        assert args.layout == "fr"
        assert args.label_quantile == 0.99
        assert args.seed == 42

    def test_missing_required_args_exits(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2
        assert "--edges" in capsys.readouterr().err

    def test_invalid_layout_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(
                ["--edges", "edges.csv", "--root", "dog", "--layout", "bogus"]
            )
