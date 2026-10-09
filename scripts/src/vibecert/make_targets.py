import re


class MakeTargets:
    """The recipes of a Makefile, so a make invocation can be read as what it runs.

    Args:
        lines (list[str]): The Makefile's lines, empty where there is none.

    """

    TARGET: re.Pattern[str] = re.compile(r"^([^\s.#:=][^#:=]*):(?!=)")

    INVOCATION: re.Pattern[str] = re.compile(r"(?<![\w-])make\b([^;&|\n]*)")

    def __init__(self, lines: list[str]) -> None:
        self.__recipes: dict[str, list[str]] = MakeTargets._parse(lines)

    def expand(self, command: str) -> list[str]:
        """Return the recipe lines of every target a shell command makes.

        Args:
            command (str): A shell command, possibly invoking make.

        Returns:
            list[str]: The recipe lines, in order, or nothing where the command
                does not invoke make or names no known target. A make with no
                target runs the first one.

        """
        return [
            line
            for invocation in MakeTargets.INVOCATION.findall(command)
            for target in self._targets(invocation)
            for line in self.__recipes.get(target, [])
        ]

    def _targets(self, invocation: str) -> list[str]:
        named: list[str] = [
            word
            for word in invocation.split()
            if not word.startswith("-") and "=" not in word
        ]
        return named or list(self.__recipes)[:1]

    @staticmethod
    def _parse(lines: list[str]) -> dict[str, list[str]]:
        recipes: dict[str, list[str]] = {}
        current: list[str] = []
        for line in lines:
            match: re.Match[str] | None = MakeTargets.TARGET.match(line)
            if match:
                current = []
                for target in match.group(1).split():
                    recipes[target] = current
            elif line.startswith("\t"):
                current.append(line.strip())
            elif line.strip():
                current = []
        return recipes
