from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

import black
import refactor
from refactor.actions import InsertAfter, Replace


@dataclass
class State:
    tkinter_as: str | None = None
    tkinter_used: bool = False
    tukaan_as: str | None = None


state = State()


class ChangeImports(refactor.Rule):
    def match(self, node: ast.AST) -> Replace:
        assert isinstance(node, ast.Import)
        imports = node.names[:]
        for index, module in enumerate(imports):
            if module.name == "tkinter":
                state.tkinter_used = True
                state.tkinter_as = module.asname or module.name
                state.tukaan_as = module.asname or "tukaan"

                imports[index] = ast.alias("tukaan", module.asname)

        return Replace(node, ast.Import(imports))


class AddAppContext(refactor.Rule):
    def match(self, node: ast.AST) -> Replace:
        assert state.tkinter_used
        assert isinstance(node, ast.Assign)
        assert isinstance(node.value, ast.Call)
        assert isinstance(node.value.func, ast.Attribute)
        assert node.value.func.value.id == state.tkinter_as
        assert node.value.func.attr == "Tk"

        app_ast = ast.Assign(
            targets=[ast.Name("app")],
            value=ast.Call(
                ast.Attribute(value=ast.Name(state.tukaan_as), attr="App"), args=(), keywords=()
            ),
        )

        window_ast = ast.Assign(
            targets=node.targets,
            value=ast.Call(
                ast.Attribute(value=ast.Name(state.tukaan_as), attr="MainWindow"),
                args=(),
                keywords=(),
            ),
        )
        ast.fix_missing_locations(app_ast)
        ast.fix_missing_locations(window_ast)

        for i in (Replace(node, app_ast), InsertAfter(node, window_ast)):
            yield i


class MainloopToRun(refactor.Rule):
    def match(self, node: ast.AST) -> Replace:
        assert state.tkinter_used
        assert isinstance(node, ast.Expr)
        assert isinstance(node.value, ast.Call)
        assert isinstance(node.value.func, ast.Attribute)
        assert node.value.func.attr == "mainloop"

        replacement = ast.Expr(
            value=ast.Call(ast.Attribute(value=ast.Name("app"), attr="run"), args=(), keywords=())
        )
        ast.fix_missing_locations(replacement)

        return Replace(node, replacement)


def blacken(string):
    return black.format_str(string, mode=black.FileMode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="tkupgrade", description="Upgrade tkinter apps to tukaan")
    parser.add_argument("filename")
    parser.add_argument("--skip-black", action="store_true")
    args = parser.parse_args()

    session = refactor.Session(rules=[ChangeImports, AddAppContext, MainloopToRun])

    path = Path(args.filename)
    text = path.read_text()
    if not args.skip_black:
        text = blacken(text)
    path.write_text(session.run(text))
