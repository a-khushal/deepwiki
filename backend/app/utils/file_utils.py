from pathlib import Path

INCLUDE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".cpp", ".c", ".rb", ".php", ".md", ".txt", ".yaml", ".yml",
    ".json", ".toml",
}

EXCLUDE_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".next", "vendor", "target", ".venv", "venv", "env",
}

EXCLUDE_FILES = {
    "package-lock.json", "yarn.lock", "poetry.lock",
    "pnpm-lock.yaml", "Gemfile.lock",
}

MAX_FILE_SIZE = 100 * 1024

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".rb": "ruby",
    ".php": "php",
    ".md": "markdown",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
}


def should_include(file_path: Path) -> bool:
    if file_path.suffix.lower() not in INCLUDE_EXTENSIONS:
        return False
    if file_path.name in EXCLUDE_FILES:
        return False
    for part in file_path.parts:
        if part in EXCLUDE_DIRS:
            return False
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return False
    except OSError:
        return False
    return True


def detect_language(file_path: Path) -> str:
    return LANGUAGE_MAP.get(file_path.suffix.lower(), "unknown")
