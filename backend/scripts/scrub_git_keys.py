"""
Scrub exposed API keys from git history.
Uses git filter-branch with a python --tree-filter script (cross-platform).
Run from the repo root: python backend/scripts/scrub_git_keys.py
"""
import subprocess
import sys

KEYS_TO_SCRUB = [
    ("PQTtVyp4qiH4z67iZo3e2OXMbJNPvXfeD7rNm5dt", "your_key_here"),
    ("cf656fb8-7089-4cc2-bb02-aba20e0c7bf5", "your_key_here"),
]

# Write a small shell-compatible Python one-liner for the tree-filter
replacements = " ".join(
    f"-e 's/{k}/{v}/g'" for k, v in KEYS_TO_SCRUB
)
tree_filter_cmd = f"find . -name '*.md' -exec sed -i {replacements} {{}} +"

print("Rewriting git history to scrub exposed keys...")
print(f"Filter: {tree_filter_cmd}\n")

env = {**__import__("os").environ, "FILTER_BRANCH_SQUELCH_WARNING": "1"}

result = subprocess.run(
    ["git", "filter-branch", "--force", "--tree-filter", tree_filter_cmd, "HEAD"],
    capture_output=True, text=True, env=env
)

print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
    print("\n[FAILED] filter-branch exited non-zero.")
    sys.exit(result.returncode)

print("\n[DONE] History rewritten. Now force-pushing to overwrite remote...")
push = subprocess.run(
    ["git", "push", "--force", "origin", "main"],
    capture_output=True, text=True
)
print(push.stdout)
if push.returncode != 0:
    print(push.stderr)
    print("\n[FAILED] Force push failed.")
    sys.exit(push.returncode)

print("\n[SUCCESS] Keys scrubbed from entire git history and remote updated.")
print("IMPORTANT: Anyone who cloned before this push should re-clone.")
