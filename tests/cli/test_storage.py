import json
from unittest import mock

import pytest

from pdbstore import cli
from pdbstore.cli.exit_codes import (
    ERROR_ENCOUNTERED,
    ERROR_GENERAL,
    ERROR_SUBCOMMAND_NAME,
    ERROR_UNEXPECTED,
    SUCCESS,
)


@pytest.fixture(name="stores")
def fixture_stores(tmp_path, test_data_native_dir):
    """Yield a populated source store and an empty destination location."""
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    assert (
        cli.cli.main(
            [
                "add",
                "-Vquiet",
                "--store-dir",
                str(source),
                "--product-name",
                "myproduct",
                "--product-version",
                "1.0.0",
                str(test_data_native_dir / "dummyapp.pdb"),
            ]
        )
        == SUCCESS
    )
    return source, destination


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--store-dir", "/some/destination"],
        ["--input-store-dir", "/some/source"],
    ],
)
def test_incomplete(argv):
    """test command-line missing one of the two stores"""
    with mock.patch("sys.argv", ["pdbstore", "storage", "migrate"] + argv):
        assert cli.cli.main() == ERROR_UNEXPECTED

    assert cli.cli.main(["storage", "verify"] + argv) == ERROR_UNEXPECTED


def test_no_subcommand():
    """test storage command without a sub-command name"""
    with mock.patch("sys.argv", ["pdbstore", "storage", "junk"]):
        assert cli.cli.main() == ERROR_SUBCOMMAND_NAME


def test_same_store_is_refused(stores):
    """test migrating a store onto itself"""
    source, _ = stores

    assert (
        cli.cli.main(["storage", "migrate", "-i", str(source), "-s", str(source)])
        == ERROR_UNEXPECTED
    )


def test_unsupported_scheme(stores, capsys):
    """test a location naming a backend that does not exist"""
    _, destination = stores

    assert (
        cli.cli.main(["storage", "migrate", "-i", "ftp://host/store", "-s", str(destination)])
        == ERROR_GENERAL
    )
    assert "unsupported symbol store scheme" in capsys.readouterr().err


def test_dry_run_writes_nothing(stores, capsys):
    """test that a dry run reports the work without doing it"""
    source, destination = stores

    with mock.patch(
        "sys.argv",
        ["pdbstore", "storage", "migrate", "-i", str(source), "-s", str(destination), "--dry-run"],
    ):
        assert cli.cli.main() == SUCCESS

    assert "Number of files transferred = 6" in capsys.readouterr().out
    assert not destination.exists()


def test_complete(stores, capsys, test_data_native_dir):
    """test a full migration, its verification and its resumption"""
    source, destination = stores

    assert (
        cli.cli.main(["storage", "migrate", "-i", str(source), "-s", str(destination)]) == SUCCESS
    )
    captured = capsys.readouterr()
    assert "Number of files transferred = 6" in captured.out
    assert "Number of errors = 0" in captured.out

    assert (
        cli.cli.main(["storage", "verify", "-i", str(source), "-s", str(destination), "--deep"])
        == SUCCESS
    )
    captured = capsys.readouterr()
    assert "Number of files checked = 6" in captured.out
    assert "Number of files missing or different = 0" in captured.out

    # Running it again transfers nothing, which is what makes an interrupted
    # migration safe to simply restart.
    assert (
        cli.cli.main(["storage", "migrate", "-i", str(source), "-s", str(destination)]) == SUCCESS
    )
    captured = capsys.readouterr()
    assert "Number of files transferred = 0" in captured.out
    assert "Number of files already present = 6" in captured.out

    # The destination is a working symbol store, not just a pile of files.
    assert (
        cli.cli.main(
            [
                "query",
                "--store-dir",
                str(destination),
                str(test_data_native_dir / "dummyapp.pdb"),
            ]
        )
        == SUCCESS
    )


def test_verify_reports_a_gap(stores, capsys):
    """test verification against an incomplete destination"""
    source, destination = stores
    assert (
        cli.cli.main(["storage", "migrate", "-i", str(source), "-s", str(destination)]) == SUCCESS
    )
    (destination / "pingme.txt").unlink()

    assert (
        cli.cli.main(["storage", "verify", "-i", str(source), "-s", str(destination)])
        == ERROR_ENCOUNTERED
    )
    captured = capsys.readouterr()
    assert "pingme.txt: Missing from target" in captured.out
    assert "Number of files missing or different = 1" in captured.out


@pytest.mark.parametrize("subcommand", ["migrate", "verify"])
def test_json_formatter(stores, capsys, subcommand):
    """test the json output of both sub-commands"""
    source, destination = stores
    if subcommand == "verify":
        assert (
            cli.cli.main(["storage", "migrate", "-i", str(source), "-s", str(destination)])
            == SUCCESS
        )
        capsys.readouterr()

    assert (
        cli.cli.main(
            [
                "storage",
                subcommand,
                "-i",
                str(source),
                "-s",
                str(destination),
                "--format",
                "json",
            ]
        )
        == SUCCESS
    )

    reported = json.loads(capsys.readouterr().out)
    assert reported[0]["status"] == "success"
    assert len(reported[0]["files"]) == 6


def test_prefix_restricts_the_scope(stores, capsys):
    """test restricting a migration to part of the store"""
    source, destination = stores

    assert (
        cli.cli.main(
            [
                "storage",
                "migrate",
                "-i",
                str(source),
                "-s",
                str(destination),
                "--prefix",
                "000Admin",
            ]
        )
        == SUCCESS
    )

    assert "Number of files transferred = 4" in capsys.readouterr().out
    assert (destination / "000Admin").is_dir()
    assert not (destination / "dummyapp.pdb").exists()


def test_migrate_to_s3(stores, capsys, monkeypatch, test_data_native_dir):
    """test migrating to a bucket, end to end through the command line

    Exercises the whole path a user takes: a location that is a URI, a client
    built from the environment, and a destination that answers queries like any
    other store.
    """
    boto3 = pytest.importorskip("boto3")
    moto = pytest.importorskip("moto")

    source, _ = stores
    monkeypatch.setenv("PDBSTORE_S3_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")

    with moto.mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="symbols")
        destination = "s3://symbols/team"

        assert cli.cli.main(["storage", "migrate", "-i", str(source), "-s", destination]) == SUCCESS
        assert "Number of files transferred = 6" in capsys.readouterr().out

        assert (
            cli.cli.main(["storage", "verify", "-i", str(source), "-s", destination, "--deep"])
            == SUCCESS
        )
        assert "Number of files missing or different = 0" in capsys.readouterr().out

        assert (
            cli.cli.main(
                [
                    "query",
                    "--store-dir",
                    destination,
                    str(test_data_native_dir / "dummyapp.pdb"),
                ]
            )
            == SUCCESS
        )
