"""How the S3 client is built out of the environment.

Credentials come from boto3's own resolution chain, which is verified by boto3
itself. What is verified here is the part pdbstore adds on top: the variables
that decide *which* endpoint is talked to. Pointing the tool at MinIO or Ceph
rather than at AWS goes through nothing else, so an unread variable would send
a store to the wrong place with no visible sign of it.

The session is replaced by a recorder: no request is made, and no shared AWS
configuration file is read.
"""

import pytest

from pdbstore import const

boto3 = pytest.importorskip("boto3")

# pylint: disable=wrong-import-position
from pdbstore.drivers.blob.s3 import _build_client  # noqa: E402


class SessionRecorder:
    """Stand in for ``boto3.session.Session`` and remember how it was called."""

    def __init__(self):
        self.session_args = None
        self.client_args = None
        self.service = None

    def __call__(self, **kwargs):
        self.session_args = kwargs
        return self

    def client(self, service, **kwargs):
        """Record the client request, and hand back something recognisable."""
        self.service = service
        self.client_args = kwargs
        return self


@pytest.fixture(name="session")
def fixture_session(monkeypatch):
    """Yield the recorder standing in for a boto3 session."""
    recorder = SessionRecorder()
    monkeypatch.setattr(boto3.session, "Session", recorder)
    for variable in [
        const.ENV_PDBSTORE_S3_PROFILE,
        const.ENV_PDBSTORE_S3_REGION,
        const.ENV_PDBSTORE_S3_ENDPOINT_URL,
    ]:
        monkeypatch.delenv(variable, raising=False)
    return recorder


def test_a_bare_environment_leaves_boto3_alone(session):
    """With nothing set, boto3 resolves everything on its own."""
    assert _build_client() is session

    assert session.service == "s3"
    assert session.session_args == {}
    assert session.client_args == {}


def test_an_endpoint_url_is_honoured(session, monkeypatch):
    """The endpoint variable is what sends the store to MinIO or Ceph."""
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_ENDPOINT_URL, "https://minio.local:9000")

    _build_client()

    assert session.client_args == {"endpoint_url": "https://minio.local:9000"}
    # The endpoint belongs to the client, not to the session that credentials
    # are resolved from.
    assert session.session_args == {}


def test_a_profile_is_honoured(session, monkeypatch):
    """The profile variable selects a section of the shared AWS config."""
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_PROFILE, "release")

    _build_client()

    assert session.session_args == {"profile_name": "release"}


def test_a_region_is_honoured(session, monkeypatch):
    """The region variable reaches the session as well."""
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_REGION, "eu-west-3")

    _build_client()

    assert session.session_args == {"region_name": "eu-west-3"}


def test_the_three_variables_combine(session, monkeypatch):
    """A self-hosted store usually needs all three at once."""
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_PROFILE, "onprem")
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_REGION, "us-east-1")
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_ENDPOINT_URL, "http://127.0.0.1:9000")

    _build_client()

    assert session.session_args == {"profile_name": "onprem", "region_name": "us-east-1"}
    assert session.client_args == {"endpoint_url": "http://127.0.0.1:9000"}


def test_an_empty_variable_is_ignored(session, monkeypatch):
    """An exported but empty variable means "unset", not "the empty endpoint".

    Shell scripts export variables unconditionally; passing an empty endpoint
    down to boto3 would fail far from the cause.
    """
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_PROFILE, "")
    monkeypatch.setenv(const.ENV_PDBSTORE_S3_ENDPOINT_URL, "")

    _build_client()

    assert session.session_args == {}
    assert session.client_args == {}
