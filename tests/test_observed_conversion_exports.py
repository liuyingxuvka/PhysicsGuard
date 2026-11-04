"""The conversion module's advertised exports can be imported by consumers."""


def test_observed_conversion_star_import_is_usable():
    namespace = {}
    exec("from physicsguard.schema.observed_conversion import *", namespace)
    assert callable(namespace["convert_observed_rows"])
    assert isinstance(namespace["SIGNAL_DELIMITERS"], str)
