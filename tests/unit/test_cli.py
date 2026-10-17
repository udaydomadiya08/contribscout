"""Unit tests for CLI parsing, subcommands, and exit codes."""

from pathlib import Path
import pytest

from contribscout.cli import main


def test_cli_version(capsys):
    ret = main(["--version"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ContribScout v0.1.0" in captured.out


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "ContribScout" in captured.out
    assert "Available subcommands" in captured.out


def test_cli_init_and_validate(tmp_path, capsys):
    target_profile = tmp_path / "test_profile.yaml"
    ret = main(["init", "--path", str(target_profile)])
    assert ret == 0
    assert target_profile.exists()

    # Re-running without --force should fail
    ret_fail = main(["init", "--path", str(target_profile)])
    assert ret_fail == 1

    # Re-running with --force should succeed
    ret_force = main(["init", "--path", str(target_profile), "--force"])
    assert ret_force == 0

    # Validate config
    ret_val = main(["config", "validate", "--profile", str(target_profile)])
    assert ret_val == 0


def test_cli_doctor(capsys):
    ret = main(["doctor"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Diagnostic Health Check" in captured.out


def test_cli_history_clear(capsys):
    ret = main(["history", "--clear"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "cleared" in captured.out.lower()


def test_cli_show_last_report(capsys):
    ret = main(["show", "--last-report"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Scan Summary" in captured.out or "No recent scan" in captured.out


def test_cli_explain_invalid_url(capsys):
    ret = main(["explain", "https://notgithub.com/invalid"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Invalid GitHub issue URL" in captured.err


def test_cli_no_args(capsys):
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Available subcommands" in captured.out
