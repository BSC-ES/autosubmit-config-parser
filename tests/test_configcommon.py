from autosubmitconfigparser.config.configcommon import AutosubmitConfig


class TestCCommon:

    def test_flatten_section_list(self):
        assert AutosubmitConfig._flatten_section(
            [[["A", "B"], "C"], ["D", "E"]]) == ["A", "B", "C", "D", "E"]
        assert AutosubmitConfig._flatten_section(
            ["A", "B", "C", "D", "E"]) == ["A", "B", "C", "D", "E"]
        assert AutosubmitConfig._flatten_section("AS4") == ["AS4"]
