from vibecert.criticality import FanInCounter


class TestFanInCounter:
    def test_count_python_importers_returns_count(self) -> None:
        assert (
            FanInCounter(
                {
                    "foo.py": "x = 1",
                    "bar.py": "from vibecert.foo import x",
                    "baz.py": "import foo",
                    "qux.py": "nothing",
                }
            ).count("foo.py")
            == 2
        )

    def test_count_self_reference_excluded(self) -> None:
        assert FanInCounter({"foo.py": "import foo"}).count("foo.py") == 0

    def test_count_typescript_relative_import_counts(self) -> None:
        assert (
            FanInCounter({"foo.ts": "", "bar.ts": "import x from './foo'"}).count(
                "foo.ts"
            )
            == 1
        )

    def test_count_unknown_file_type_returns_zero(self) -> None:
        assert FanInCounter({"foo.md": "", "bar.md": "foo"}).count("foo.md") == 0
