#!/usr/bin/env python3
"""
AutoDev Autonomous Agent Runner

Launches the autonomous development agent with full OODA loop capability.

Usage:
    python run_autonomous.py -f step6.py --max-iterations 20

The agent will:
1. Run tests to find failures
2. Analyze code and reference implementations
3. Generate and apply patches
4. Verify and commit changes
5. Loop until tests pass
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_autonomous_agent(target_file: str = "step6.py", max_iterations: int = 20):
    """
    Run the autonomous agent using Claude Code's agent system.

    This function activates the autodev-autonomous agent which will:
    - Observe: Run tests and capture failures
    - Orient: Analyze codebase for patterns
    - Decide: Generate minimal patches
    - Act: Apply patches and verify
    - Loop: Repeat until success or max iterations
    """
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                            ║
║  AutoDev Autonomous Agent                                  ║
║                                                            ║
║  Target: {target_file:<40} ║
║  Max Iterations: {max_iterations:<40} ║
║                                                            ║
║  Agent: .claude/agents/autodev-autonomous/SKILL.md        ║
║                                                            ║
╚══════════════════════════════════════════════════════════════╝

Initializing autonomous development loop...
The agent will:
  ✓ Run tests to identify missing features
  ✓ Analyze existing code patterns
  ✓ Reference similar implementations
  ✓ Generate minimal, targeted patches
  ✓ Verify changes and run tests again
  ✓ Commit successful iterations
  ✓ Update MEMORY.md with learnings
  ✓ Loop until all tests pass

Starting now...
""")

    # The agent execution happens through Claude Code's agent system
    # when this script is run with the agent context loaded

    print("\n[AGENT CONTEXT]")
    print("Loading agent skill: .claude/agents/autodev-autonomous/SKILL.md")
    print("Project root:", project_root)
    print("Target path:", project_root / "mal" / target_file)

    print("\n[AUTONOMOUS LOOP]")
    print("The agent will now run iterations autonomously.")
    print("Progress will be reported after each iteration.")

    # Create the agent prompt
    agent_prompt = f"""You are the AutoDev autonomous development agent.

Your task: Implement missing features in {target_file} to make all tests pass.

Current state:
- Project: {project_root}
- Target: mal/{target_file}
- Max iterations: {max_iterations}

Follow the OODA loop:
1. OBSERVE: Run tests (cd mal && python test.py tests/step*_*.mal python {target_file})
2. ORIENT: Read current code, find patterns, check reference impl
3. DECIDE: Generate minimal patches using Edit tool
4. ACT: Verify changes, run tests again
5. LOOP: Repeat until tests pass or {max_iterations} iterations

After each iteration:
- Report progress (tests passing/missing functions)
- If successful: commit changes
- Update MEMORY.md with what you learned

Start now by running the first test iteration."""

    print("\n" + "="*60)
    print("AGENT PROMPT:")
    print("="*60)
    print(agent_prompt)
    print("="*60)

    print("\n[Note]: In full autonomous mode, Claude Code will execute the OODA loop")
    print("using the autodev-autonomous agent context. No manual intervention needed.")

    return agent_prompt


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Run AutoDev autonomous agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_autonomous.py -f step6.py
  python run_autonomous.py -f step7.py --max-iterations 30
  python run_autonomous.py --file stepA.mal
        """
    )
    parser.add_argument(
        "--file", "-f",
        default="step6.py",
        help="Target step file (default: step6.py)"
    )
    parser.add_argument(
        "--max-iterations", "-n",
        type=int,
        default=20,
        help="Maximum OODA iterations (default: 20)"
    )

    args = parser.parse_args()

    try:
        prompt = run_autonomous_agent(args.file, args.max_iterations)

        # In autonomous mode, this prompt would be passed to the agent
        print("\n" + "="*60)
        print("READY FOR AUTONOMOUS EXECUTION")
        print("="*60)
        print("\nThe agent context is loaded with:")
        print("  - Project structure and patterns")
        print("  - OODA loop workflow")
        print("  - Tool access (Read, Edit, Bash, Grep, Glob, Write)")
        print("  - Decision guidelines and success criteria")
        print("\nWhen ready, launch the agent with this prompt.")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
