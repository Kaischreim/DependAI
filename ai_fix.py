import subprocess
import anthropic
import os
from pathlib import Path

def run_tests():
    results = []
    
    # run Go tests
    go_result = subprocess.run(
        ["go", "test", "./..."],
        capture_output=True, text=True
    )
    results.append(("Go", go_result.stdout + go_result.stderr, go_result.returncode))
    
    # run JS tests folder1
    if Path("folder1").exists():
        npm_result = subprocess.run(
            ["npm", "test", "--if-present"],
            capture_output=True, text=True,
            cwd="folder1"
        )
        results.append(("JS folder1", npm_result.stdout + npm_result.stderr, npm_result.returncode))
    
    # run JS tests folder2
    if Path("folder2").exists():
        npm_result = subprocess.run(
            ["npm", "test", "--if-present"],
            capture_output=True, text=True,
            cwd="folder2"
        )
        results.append(("JS folder2", npm_result.stdout + npm_result.stderr, npm_result.returncode))
    
    # combine all errors
    all_errors = "\n".join(
        f"=== {name} ===\n{output}" 
        for name, output, code in results 
        if code != 0
    )
    overall_pass = all(code == 0 for _, _, code in results)
    return all_errors, overall_pass

def get_repo_files():
    files = {}
    extensions = [".go", ".js", ".jsx", ".ts", ".tsx"]
    for f in Path(".").rglob("*"):
        if any(str(f).endswith(ext) for ext in extensions):
            if ".github" not in str(f) and "node_modules" not in str(f):
                files[str(f)] = f.read_text()
    return files

def fix_with_claude(error_output, files):
    client = anthropic.Anthropic()
    
    files_str = "\n\n".join(
        f"=== {path} ===\n{content}"
        for path, content in files.items()
    )
    
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"""
You are fixing a web app after a dependency update broke the tests.

Here are the test errors:
{error_output}

Here are all the source files:
{files_str}

Rules:
- Fix the code so the tests pass.
- Only change what is necessary to fix the breaking changes.
- Do not change test files.
- Do not change go.mod, go.sum, or package.json.
- Output ONLY the fixed files in this exact format:
=== filepath ===
(fixed code here)

Only include files you actually changed.
"""
        }]
    )
    return message.content[0].text

def apply_fixes(claude_output):
    sections = claude_output.split("=== ")
    for section in sections[1:]:
        lines = section.split("\n")
        filename = lines[0].replace(" ===", "").strip()
        code = "\n".join(lines[1:]).strip()
        Path(filename).write_text(code)
        print(f"Fixed {filename}")

def git(cmd):
    subprocess.run(cmd, check=True)

def main():
    # bot identity
    git(["git", "config", "user.email", "arduino-bot@noreply"])
    git(["git", "config", "user.name", "arduino-bot"])
    
    # use PAT for push
    pat = os.environ.get("PAT_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if pat and repo:
        git(["git", "remote", "set-url", "origin",
             f"https://x-access-token:{pat}@github.com/{repo}.git"])

    max_attempts = 3

    for attempt in range(max_attempts):
        print(f"Attempt {attempt + 1}/{max_attempts}")
        
        error_output, passing = run_tests()
        
        if passing:
            print("All tests passing!")
            git(["git", "push"])
            return

        print(f"Tests failed:\n{error_output}")
        files = get_repo_files()
        fixes = fix_with_claude(error_output, files)
        apply_fixes(fixes)

    print("Could not fix after 3 attempts - human review needed")

if __name__ == "__main__":
    main()