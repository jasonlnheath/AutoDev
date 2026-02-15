#!/usr/bin/env python
"""
Step 0: Basic REPL for Mal

This is the simplest step - just a Read-Eval-Print Loop that echoes input back.
The EVAL and PRINT functions don't do anything yet, they just pass through.
"""

import sys


def READ(input_str: str) -> str:
    """
    READ: Parse the input (for now, just return as-is)
    """
    return input_str


def EVAL(input_str: str) -> str:
    """
    EVAL: Evaluate the input (for now, just return as-is)
    """
    return input_str


def PRINT(input_str: str) -> str:
    """
    PRINT: Format the output (for now, just return as-is)
    """
    return input_str


def rep(input_str: str) -> str:
    """
    REP: Read-Eval-Print
    """
    return PRINT(EVAL(READ(input_str)))


def main():
    """Main REPL loop"""
    # Check if we're in non-interactive mode (for testing)
    if not sys.stdin.isatty():
        # Non-interactive mode: read all lines from stdin
        for line in sys.stdin:
            line = line.rstrip('\n')
            if line:  # Skip empty lines
                print(rep(line))
        return

    # Interactive mode
    print("Mal Step 0 - Basic REPL")
    print("Type 'exit' or Ctrl+C to quit\n")

    while True:
        try:
            # Read input from user
            line = input("user> ")

            # Exit on empty input or 'exit'
            if not line or line.strip() == "exit":
                continue

            # Process and print result
            result = rep(line)
            print(result)

        except EOFError:
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
