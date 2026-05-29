import re
import os
from pathlib import Path
from typing import Optional
from collections import defaultdict


class DepGraph:
    def __init__(self):
        self.imports: dict[str, set[str]] = defaultdict(set)
        self.exported_by: dict[str, set[str]] = defaultdict(set)
        self.functions: dict[str, list[dict]] = defaultdict(list)
        self.classes: dict[str, list[dict]] = defaultdict(list)

    def add_file(self, filepath: str):
        p = Path(filepath)
        if not p.exists() or not p.is_file():
            return
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        rel = str(p)
        ext = p.suffix

        if ext == ".py":
            for m in re.finditer(r'^(?:from\s+(\S+)\s+)?import\s+(\S+)', content, re.MULTILINE):
                module = m.group(1) or ""
                targets = m.group(2).split(",")
                for t in targets:
                    t = t.strip().split(" as ")[0].split(".")[0]
                    if t:
                        self.imports[rel].add(t)
                        self.exported_by[t].add(rel)

            for m in re.finditer(r'^def\s+(\w+)\s*\(', content, re.MULTILINE):
                func_name = m.group(1)
                if not func_name.startswith("_"):
                    self.functions[rel].append({"name": func_name, "type": "function"})

            for m in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                cls_name = m.group(1)
                self.classes[rel].append({"name": cls_name, "type": "class"})

        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for m in re.finditer(r'(?:import\s+(?:\*\s+as\s+)?(\w+)|from\s+[\'"]([^\'"]+)[\'"])', content):
                if m.group(1):
                    self.imports[rel].add(m.group(1))
                if m.group(2):
                    self.imports[rel].add(m.group(2).split("/")[-1])

            for m in re.finditer(r'(?:export\s+)?(?:function|const)\s+(\w+)\s*(?:[=\(])', content):
                self.functions[rel].append({"name": m.group(1), "type": "function"})

            for m in re.finditer(r'(?:export\s+)?class\s+(\w+)', content):
                self.classes[rel].append({"name": m.group(1), "type": "class"})

    def analyze_project(self, root: str, extensions: tuple = (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java")):
        root_p = Path(root).resolve()
        if not root_p.exists():
            return
        for f in root_p.rglob("*"):
            if f.suffix in extensions and not any(p.startswith(".") for p in f.parts):
                self.add_file(str(f))

    def deps_of(self, filepath: str) -> set[str]:
        return self.imports.get(filepath, set())

    def dependents_of(self, filepath: str) -> set[str]:
        p = Path(filepath)
        name = p.stem
        return self.exported_by.get(name, set())

    def summary(self) -> str:
        lines = []
        for fp in sorted(set(list(self.functions.keys()) + list(self.classes.keys()) + list(self.imports.keys()))):
            lines.append(f"\n  {fp}:")
            for fn in self.functions.get(fp, []):
                lines.append(f"    def {fn['name']}()")
            for cls in self.classes.get(fp, []):
                lines.append(f"    class {cls['name']}")
            for imp in self.imports.get(fp, set()):
                lines.append(f"    imports: {imp}")
        return "\n".join(lines)

    def find_references(self, symbol: str) -> list[str]:
        results = []
        for fp in self.imports:
            if symbol in self.imports[fp]:
                results.append(fp)
        for fp in self.functions:
            for fn in self.functions[fp]:
                if symbol in fn["name"]:
                    results.append(fp)
        return sorted(set(results))


def analyze_directory(path: str) -> str:
    dg = DepGraph()
    dg.analyze_project(path)
    return dg.summary()
