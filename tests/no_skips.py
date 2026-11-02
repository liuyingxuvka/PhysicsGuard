"""pytest plugin: a test that ends skipped fails, so a swallowed error cannot hide as a skip.

Two places can skip: a test while it runs (pytest.skip, a skip mark, unittest's skipTest, xfail),
and a whole file while it is collected (a module-level importorskip or pytest.skip(allow_module_level=True)).
Both reports are turned into failures here.
"""
from __future__ import annotations

import pytest


def _reason(longrepr) -> str:
    return longrepr[2] if isinstance(longrepr, tuple) else str(longrepr)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.skipped:
        report.outcome = "failed"
        report.longrepr = (f"{item.nodeid} ended skipped ({_reason(report.longrepr)}); this suite allows no skips: "
                           "a skip hides why the test could not run")


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    outcome = yield
    report = outcome.get_result()
    if report.skipped:
        report.outcome = "failed"
        report.longrepr = (f"{collector.nodeid} was skipped while it was collected ({_reason(report.longrepr)}); "
                           "this suite allows no skips: a skip hides why the tests could not run")
