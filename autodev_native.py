#!/usr/bin/env python3
"""
AutoDev Native - Claude-Native OODA Loop with Code-First Memory.

This version abandons the context tree in favor of:
1. Direct code analysis (read working implementations)
2. MEMORY.md for human-readable patterns
3. Git history for long-term memory

Run: python autodev_native.py -f step4.py
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ooda.observe import Observer


def print_header(title: str):
    print(f"\n{'=' * 50}")
    print(f"{title:^50}")
    print(f"{'=' * 50}")


def print_section(name: str):
    print(f"\n[{name}]")


def get_git_history(project_root: Path, file_path: str, limit: int = 5) -> list:
    """Get recent git commits for context."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--oneline", "--", file_path],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')
    except Exception:
        pass
    return []


def extract_working_patterns(file_path: Path) -> dict:
    """
    Extract working patterns from the current codebase.
    This is the "context" for Claude-native mode.
    """
    code = file_path.read_text()

    patterns = {
        "special_forms": [],
        "builtins": [],
        "key_implementations": {}
    }

    lines = code.split('\n')

    # Find special forms in EVAL
    in_eval = False
    eval_start = 0
    for i, line in enumerate(lines):
        if 'def EVAL(' in line:
            in_eval = True
            eval_start = i
        if in_eval and line.strip().startswith('if first.value =='):
            # Extract special form name
            form = line.split("'")[1] if "'" in line else ""
            if form:
                patterns["special_forms"].append(form)

        # Find key implementations
        if in_eval:
            if 'def READ(' in line:
                patterns["key_implementations"]["reader"] = i
            elif 'def PRINT(' in line:
                patterns["key_implementations"]["printer"] = i
            elif 'return evaluated' in line:
                break

    return patterns


def run_native_loop(
    target_file: str = "step4.py",
    max_iterations: int = 20
):
    """
    Run Claude-native OODA loop with code-first memory.
    """
    project_root = Path(__file__).parent
    target_path = project_root / "mal" / target_file

    print_header("AutoDev Native - Code-First Memory")
    print(f"Target: {target_file}")
    print(f"Max iterations: {max_iterations}")
    print(f"Memory: Code analysis + MEMORY.md + Git history")

    observer = Observer(project_root)

    iteration = 0
    for iteration in range(1, max_iterations + 1):
        print_header(f"Iteration {iteration}/{max_iterations}")

        # === OBSERVE ===
        print_section("OBSERVE")
        success, output = observer.run_tests()

        if success:
            print(f"\n[SUCCESS] All tests passing!")
            # Update MEMORY.md with success
            memory_path = project_root / "MEMORY.md"
            existing = memory_path.read_text() if memory_path.exists() else ""
            if f"## {target_file}" not in existing:
                with open(memory_path, 'a') as f:
                    f.write(f"\n## {target_file}\n")
                    f.write(f"**Status**: Complete ({datetime.now().strftime('%Y-%m-%d')})\n")
                    f.write"All tests passing.\n"
            break

        parsed = observer.parse_mal_test_output(output)
        current_code = target_path.read_text()
        missing = parsed.get("missing_functions", [])

        print(f"  Tests: {parsed.get('passed', 0)} passed, {parsed.get('failed', 0)} failed")
        print(f"  Missing functions: {', '.join(missing[:10])}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")

        # === ORIENT (Code Analysis) ===
        print_section("ORIENT")
        patterns = extract_working_patterns(target_path)
        git_history = get_git_history(project_root, f"mal/{target_file}")

        print(f"  Working special forms: {len(patterns['special_forms'])}")
        print(f"  Recent commits: {len(git_history)}")

        # Show git history for context
        if git_history:
            print("\n  Recent changes:")
            for commit in git_history[:3]:
                print(f"    {commit}")

        # Check MEMORY.md for relevant patterns
        memory_path = project_root / "MEMORY.md"
        if memory_path.exists():
            memory_content = memory_path.read_text()
            print(f"\n  Memory patterns available: {memory_content.count('##')} sections")

        # === DECIDE (Claude) ===
        print_section("DECIDE")
        print("\n  >>> CLAUDE: Please analyze and implement missing functions.\n")

        # Show working examples from current code
        print("  " + "=" * 46)
        print("  WORKING PATTERNS IN CURRENT CODE")
        print("  " + "=" * 46)

        # Show a similar working implementation as example
        lines = current_code.split('\n')
        if patterns["special_forms"]:
            example_form = patterns["special_forms"][0]
            print(f"\n  Example: '{example_form}' implementation:")
            in_example = False
            for i, line in enumerate(lines):
                if f"if first.value == '{example_form}'" in line:
                    in_example = True
                if in_example:
                    print(f"  {i+1:4}: {line}")
                    if 'return' in line and 'EVAL' in line:
                        break

        print("\n  " + "=" * 46)
        print("\n  >>> CLAUDE: Use the Edit tool to add missing functions.")
        print("  >>> Follow the patterns shown above.")
        print("  >>> Type 'CONTINUE' when done.\n")

        # Wait for Claude to make changes
        input("\n  [Press Enter after Claude has applied changes, or 'SKIP' to skip] ")

        # === ACT ===
        print_section("ACT")

        new_code = target_path.read_text()

        if new_code == current_code:
            print("  [WARN] No changes detected")
            continue

        # Verify by running tests
        print("  Running tests...")
        verify_success, verify_output = observer.run_tests()

        if verify_success:
            print("  [SUCCESS] Tests pass!")
            # Commit the change
            try:
                subprocess.run(
                    ["git", "add", f"mal/{target_file}"],
                    cwd=project_root,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "commit", "-m", f"AutoDev: Fix {target_file} - iteration {iteration}"],
                    cwd=project_root,
                    capture_output=True
                )
                print("  [GIT] Changes committed")
            except Exception as e:
                print(f"  [GIT] Commit failed: {e}")
        else:
            verify_parsed = observer.parse_mal_test_output(verify_output)
            still_missing = verify_parsed.get("missing_functions", [])
            print(f"  [FAIL] Tests still failing")
            print(f"  Progress: {len(missing) - len(still_missing)} functions added")

    # Final report
    print_header("Final Report")
    print(f"\nTotal iterations: {iteration}")
    print(f"Tests passing: {'YES' if success else 'NO'}")

    if not success:
        print(f"\nRemaining work: {len(missing)} functions")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AutoDev Native")
    parser.add_argument("--file", "-f", default="step4.py", help="Target file")
    parser.add_argument("--max-iterations", "-n", type=int, default=20, help="Max iterations")
    args = parser.parse_args()

    try:
        run_native_loop(args.file, args.max_iterations)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
