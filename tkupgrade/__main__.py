from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

import black
import refactor


@dataclass
class State:
    tkinter_as: str | None = None
    tkinter_used: bool = False


state = State()


class ChangeImports(refactor.Rule):
    def match(self, node: ast.AST) -> refactor.Replace:
        assert isinstance(node, ast.Import)
        imports = node.names[:]
        for index, module in enumerate(imports):
            if module.name == "tkinter":
                state.tkinter_used = True
                state.tkinter_as = module.asname

                imports[index] = ast.alias("tukaan", "tk")

        return refactor.Replace(node, ast.Import(imports))


def blacken(string):
    return black.format_str(string, mode=black.FileMode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="tkupgrade", description="Upgrade tkinter apps to tukaan")
    parser.add_argument("filename")
    parser.add_argument("--skip-black", action="store_true")
    args = parser.parse_args()

    session = refactor.Session(rules=[ChangeImports])

    path = Path(args.filename)
    text = path.read_text()
    if not args.skip_black:
        text = blacken(text)
    path.write_text(session.run(text))
