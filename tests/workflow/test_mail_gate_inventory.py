"""Prevent future production mail producers from bypassing the audited matrix."""
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def test_all_mail_builders_have_an_explicit_positive_and_negative_policy_case():
    report=json.loads((ROOT/"control-room/RFQ-016/TEST_REPORT.json").read_text(encoding="utf-8"))
    matrix=report["mail_gate_audit_20261105"]["producer_inventory"]
    found=set()
    for path in (ROOT/"src").rglob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"))
        aliases={"NotificationCommand"}
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                aliases.update(n.asname or n.name for n in node.names if n.name=="NotificationCommand")
        def visit(node,scope="",path=path,aliases=aliases):
            for child in ast.iter_child_nodes(node):
                if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    visit(child,scope+"."+child.name if scope else child.name)
                elif isinstance(child,ast.Call) and ((isinstance(child.func,ast.Name) and child.func.id in aliases) or (isinstance(child.func,ast.Attribute) and child.func.attr=="NotificationCommand")):
                    found.add((path.relative_to(ROOT).as_posix(),scope))
                else:visit(child,scope)
        visit(tree)
    assert found=={(row["file"],row["producer"]) for row in matrix}
    for row in matrix:
        assert row["positive"] and row["negative"] and row["policy"]
        for ref in row["positive"]+row["negative"]:
            if ref=="NOT_A_PRODUCER" or ref=="INTENTIONALLY_UNVERIFIED_MAINTENANCE":continue
            file,name=ref.split("::")
            tree=ast.parse((ROOT/file).read_text(encoding="utf-8"))
            assert any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name for n in ast.walk(tree)),ref
