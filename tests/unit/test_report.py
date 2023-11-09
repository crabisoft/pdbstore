import pytest

from pdbstore.report import ReportGenerator


def test_supported_list(tmp_store):
    """test the list of supported report types"""
    report = ReportGenerator(tmp_store)
    assert sorted(report.supported_list()) == [
        ReportGenerator.FILES,
        ReportGenerator.PRODUCTS,
        ReportGenerator.TRANSACTIONS,
    ]


@pytest.mark.parametrize(
    "report_type",
    [
        ReportGenerator.FILES,
        ReportGenerator.PRODUCTS,
        ReportGenerator.TRANSACTIONS,
    ],
)
def test_valid_report(tmp_store, report_type):
    """test report generation with success"""
    report = ReportGenerator(tmp_store)
    assert report.generate(report_type) is not None


def test_invalid_report(tmp_store, capsys):
    """test report generation with failure"""
    report = ReportGenerator(tmp_store)
    assert report.generate("invalid") is None
    assert capsys.readouterr().err == "ERROR: invalid : unsupported report type\n"
