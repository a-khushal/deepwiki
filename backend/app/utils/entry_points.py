import json
import tomllib
from pathlib import Path
from typing import Optional

from app.models.schemas import EntryPoint


class EntryPointDetector:
    def detect(self, repo_path: str) -> list[EntryPoint]:
        root = Path(repo_path)
        if not root.exists():
            raise FileNotFoundError(f"Repo path not found: {repo_path}")

        candidates: list[EntryPoint] = []
        candidates.extend(self._detect_python(root))
        candidates.extend(self._detect_javascript_typescript(root))
        candidates.extend(self._detect_go(root))
        candidates.extend(self._detect_rust(root))
        candidates.extend(self._detect_java(root))

        candidates.sort(key=lambda e: e.rank, reverse=True)
        return candidates

    def _detect_python(self, root: Path) -> list[EntryPoint]:
        entries = []
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                data = tomllib.loads(pyproject.read_text())
                scripts = data.get("project", {}).get("scripts", {})
                if scripts:
                    for name in list(scripts.keys())[:3]:
                        entries.append(EntryPoint(
                            file_path=str(pyproject.relative_to(root)),
                            language="python",
                            rank=10,
                            description=f"CLI entry point: {name}",
                        ))
            except Exception:
                pass

        for name in ("main.py", "app.py", "manage.py", "cli.py", "__main__.py"):
            for f in root.rglob(name):
                if ".venv" not in f.parts and "site-packages" not in f.parts:
                    rank = 9 if name == "main.py" else 8
                    entries.append(EntryPoint(
                        file_path=str(f.relative_to(root)),
                        language="python",
                        rank=rank,
                    ))

        setup = root / "setup.py"
        if setup.exists():
            entries.insert(0, EntryPoint(
                file_path="setup.py",
                language="python",
                rank=7,
                description="Package setup script",
            ))

        return entries

    def _detect_javascript_typescript(self, root: Path) -> list[EntryPoint]:
        entries = []
        pkg = root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text())
                main = data.get("main")
                bin_entry = data.get("bin", {})
                if isinstance(bin_entry, str):
                    entries.append(EntryPoint(
                        file_path=bin_entry,
                        language="javascript",
                        rank=9,
                        description="Binary entry point (package.json bin)",
                    ))
                elif isinstance(bin_entry, dict):
                    for path in list(bin_entry.values())[:3]:
                        entries.append(EntryPoint(
                            file_path=path,
                            language="javascript",
                            rank=9,
                            description=f"Binary entry point ({list(bin_entry.keys())[0]})",
                        ))
                if main:
                    entries.append(EntryPoint(
                        file_path=main,
                        language="javascript",
                        rank=8,
                        description="Main entry point (package.json main)",
                    ))
            except Exception:
                pass

        for name in ("index.js", "index.ts", "src/index.ts", "src/index.js",
                     "src/main.ts", "src/main.js", "app.tsx", "App.tsx",
                     "next.config.js", "next.config.ts"):
            f = root / name
            if f.exists():
                entries.append(EntryPoint(
                    file_path=name,
                    language="typescript" if name.endswith(".ts") or name.endswith(".tsx") else "javascript",
                    rank=8,
                ))

        return entries

    def _detect_go(self, root: Path) -> list[EntryPoint]:
        entries = []
        cmd_dir = root / "cmd"
        if cmd_dir.exists() and cmd_dir.is_dir():
            for main_file in cmd_dir.rglob("main.go"):
                entries.append(EntryPoint(
                    file_path=str(main_file.relative_to(root)),
                    language="go",
                    rank=10,
                    description="Go application entry point",
                ))

        main_go = root / "main.go"
        if main_go.exists():
            entries.append(EntryPoint(
                file_path="main.go",
                language="go",
                rank=9,
            ))

        return entries

    def _detect_rust(self, root: Path) -> list[EntryPoint]:
        entries = []
        cargo = root / "Cargo.toml"
        if cargo.exists():
            try:
                data = tomllib.loads(cargo.read_text())
                bins = data.get("bin", [])
                if isinstance(bins, list):
                    for b in bins:
                        path = b.get("path", f"src/{b['name']}.rs")
                        entries.append(EntryPoint(
                            file_path=path,
                            language="rust",
                            rank=10,
                            description=f"Binary: {b.get('name')}",
                        ))
            except Exception:
                pass

        for name in ("src/main.rs", "src/lib.rs"):
            f = root / name
            if f.exists():
                entries.append(EntryPoint(
                    file_path=name,
                    language="rust",
                    rank=9 if "main" in name else 7,
                ))

        return entries

    def _detect_java(self, root: Path) -> list[EntryPoint]:
        entries = []
        for f in root.rglob("*.java"):
            if ".venv" in f.parts or "node_modules" in f.parts:
                continue
            content = f.read_text("utf-8", errors="replace")
            if "public static void main" in content:
                entries.append(EntryPoint(
                    file_path=str(f.relative_to(root)),
                    language="java",
                    rank=10,
                    description="Main class",
                ))

        for name in ("pom.xml", "build.gradle", "build.gradle.kts"):
            f = root / name
            if f.exists():
                entries.append(EntryPoint(
                    file_path=name,
                    language="java",
                    rank=6,
                    description=f"Build file: {name}",
                ))

        return entries
