import os
import re
import subprocess
from pathlib import Path

import anthropic

ROOT = Path.cwd().resolve()
SOURCE_SUFFIXES = {".go", ".js", ".jsx", ".ts", ".tsx"}


def run_command(command, cwd=ROOT):
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def run_tests():
    results = []

    go_result = run_command(["go", "test", "./..."])
    results.append(
        ("Go", go_result.stdout + go_result.stderr, go_result.returncode)
    )

    for folder in ("folder1", "folder2"):
        folder_path = ROOT / folder

        if not (folder_path / "package.json").is_file():
            continue

        install_result = run_command(["npm", "install"], cwd=folder_path)
        results.append(
            (
                f"{folder} install",
                install_result.stdout + install_result.stderr,
                install_result.returncode,
            )
        )

        if install_result.returncode != 0:
            continue

        test_result = run_command(["npm", "test"], cwd=folder_path)
        results.append(
            (
                f"{folder} tests",
                test_result.stdout + test_result.stderr,
                test_result.returncode,
            )
        )

    errors = "\n".join(
        f"=== {name} ===\n{output}"
        for name, output, code in results
        if code != 0
    )

    passing = all(code == 0 for _, _, code in results)
    return errors, passing


def is_test_file(path):
    name = path.name
    return (
        name.endswith("_test.go")
        or ".test." in name
        or ".spec." in name
    )


def is_allowed_source_file(path_string):
    requested = Path(path_string)

    if requested.is_absolute():
        return False

    target = (ROOT / requested).resolve()

    try:
        relative = target.relative_to(ROOT)
    except ValueError:
        return False

    if any(part in {".git", ".github", "node_modules"} for part in relative.parts):
        return False

    if target.suffix not in SOURCE_SUFFIXES:
        return False

    if is_test_file(target):
        return False

    # Claude may edit existing application source only.
    return target.is_file()


def get_repo_files():
    files = {}

    for file_path in ROOT.rglob("*"):
        if not file_path.is_file():
            continue

        relative = file_path.relative_to(ROOT)

        if any(part in {".git", ".github", "node_modules"} for part in relative.parts):
            continue

        if file_path.suffix not in SOURCE_SUFFIXES:
            continue

        files[relative.as_posix()] = file_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    return files


def fix_with_claude(error_output, files):
    client = anthropic.Anthropic()

    all_files = "\n\n".join(
        f"=== {path} ===\n{content}"
        for path, content in files.items()
    )

    writable_files = [
        path for path in files
        if is_allowed_source_file(path)
    ]

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"""
You are fixing application code after a dependency update broke tests.

Test errors:
{error_output}

Repository source and test files:
{all_files}

Rules:
- Fix the application code so tests pass.
- Do not modify test files.
- Do not modify package.json, package-lock.json, go.mod, go.sum, or workflow files.
- Only modify an existing file from this allowed list:
{chr(10).join(writable_files)}
- Output ONLY changed files in this exact format:

=== relative/filepath ===
complete replacement file contents

Do not use Markdown code fences.
"""
        }],
    )

    return message.content[0].text


def apply_fixes(claude_output):
    matches = list(
        re.finditer(r"^=== ([^\n=]+) ===\s*$", claude_output, re.MULTILINE)
    )

    if not matches:
        raise ValueError("Claude did not return any correctly formatted files.")

    changed_files = []

    for index, match in enumerate(matches):
        filename = match.group(1).strip()

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(claude_output)
        code = claude_output[start:end].strip()

        if not is_allowed_source_file(filename):
            raise ValueError(f"Refusing to edit disallowed file: {filename}")

        target = ROOT / filename
        old_code = target.read_text(encoding="utf-8", errors="replace")
        new_code = code + "\n"

        if old_code != new_code:
            target.write_text(new_code, encoding="utf-8")
            changed_files.append(filename)
            print(f"Fixed {filename}")

    return changed_files


def git(*args):
    subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
    )


def commit_and_push(changed_files):
    git("add", "--", *changed_files)
    git("diff", "--cached", "--check")

    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=ROOT,
        check=False,
    )

    if staged.returncode == 0:
        print("No source-code changes to commit.")
        return

    git("commit", "-m", "fix: adapt code after dependency update")

    branch = os.environ.get("TARGET_BRANCH")

    if not branch:
        raise RuntimeError("TARGET_BRANCH was not provided by the workflow.")
            
    git("push", "origin", f"HEAD:refs/heads/{branch}")


def main():
    git("config", "user.email", "arduino-bot@noreply")
    git("config", "user.name", "arduino-bot")

    pat = os.environ.get("PAT_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if pat and repo:
        git(
            "remote",
            "set-url",
            "origin",
            f"https://x-access-token:{pat}@github.com/{repo}.git",
        )

    errors, passing = run_tests()

    if passing:
        print("All tests already pass. No AI fix needed.")
        return

    changed_total = []

    for attempt in range(1, 4):
        print(f"AI repair attempt {attempt}/3")
        print(errors)

        files = get_repo_files()
        claude_output = fix_with_claude(errors, files)
        changed_now = apply_fixes(claude_output)

        if not changed_now:
            raise RuntimeError("Claude returned no actual source-code changes.")

        changed_total.extend(changed_now)

        errors, passing = run_tests()

        if passing:
            print("Tests pass after AI repair.")
            commit_and_push(sorted(set(changed_total)))
            return

    print("Could not fix after 3 attempts. No changes were pushed.")


if __name__ == "__main__":
    main()