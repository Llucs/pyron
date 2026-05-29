import re
from pathlib import Path
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
        rel, ext = str(p), p.suffix

        if ext == ".py":
            for m in re.finditer(r'^\s*(?:from\s+(\S+)\s+)?import\s+(\S+)', content, re.MULTILINE):
                module = m.group(1) or ""
                for t in m.group(2).split(","):
                    t = t.strip().split(" as ")[0].split(".")[0]
                    if t:
                        self.imports[rel].add(t)
                        self.exported_by[t].add(rel)
            for m in re.finditer(r'^\s*def\s+(\w+)\s*\(', content, re.MULTILINE):
                fn = m.group(1)
                if not fn.startswith("_"):
                    self.functions[rel].append({"name": fn, "type": "function"})
            for m in re.finditer(r'^\s*class\s+(\w+)', content, re.MULTILINE):
                self.classes[rel].append({"name": m.group(1), "type": "class"})
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            for m in re.finditer(r"(?:import\s+(?:\*\s+as\s+)?(\w+)|from\s+['\"]([^'\"]+)['\"])", content):
                if m.group(1):
                    self.imports[rel].add(m.group(1))
                if m.group(2):
                    self.imports[rel].add(m.group(2).split("/")[-1])
            for m in re.finditer(r"(?:export\s+)?(?:function|const|var|let)\s+(\w+)\s*(?:[=\(])", content):
                self.functions[rel].append({"name": m.group(1), "type": "function"})
            for m in re.finditer(r"(?:export\s+)?class\s+(\w+)", content):
                self.classes[rel].append({"name": m.group(1), "type": "class"})
        elif ext in (".go",):
            for m in re.finditer(r'^\s*func\s+(\w+)', content, re.MULTILINE):
                self.functions[rel].append({"name": m.group(1), "type": "function"})
        elif ext in (".rs",):
            for m in re.finditer(r'^\s*fn\s+(\w+)', content, re.MULTILINE):
                self.functions[rel].append({"name": m.group(1), "type": "function"})
            for m in re.finditer(r'^\s*struct\s+(\w+)', content, re.MULTILINE):
                self.classes[rel].append({"name": m.group(1), "type": "struct"})

    def analyze_project(self, root: str, extensions: tuple = (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs")):
        root_p = Path(root).resolve()
        if not root_p.exists():
            return
        for f in root_p.rglob("*"):
            if f.suffix in extensions and not any(p.startswith(".") for p in f.parts):
                self.add_file(str(f))

    def deps_of(self, filepath: str) -> set[str]:
        return self.imports.get(filepath, set())

    def dependents_of(self, filepath: str) -> set[str]:
        return self.exported_by.get(Path(filepath).stem, set())

    def find_references(self, symbol: str) -> list[str]:
        results = set()
        for fp, deps in self.imports.items():
            if symbol in deps:
                results.add(fp)
        for fp, fns in self.functions.items():
            if any(symbol in fn["name"] for fn in fns):
                results.add(fp)
        return sorted(results)

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


def analyze_directory(path: str) -> str:
    dg = DepGraph()
    dg.analyze_project(path)
    return dg.summary()
