#!/usr/bin/env python
"""
Mal Steps 1-3: READ, PRINT, EVAL with numbers, strings, and environment

Step 1: Reader - parse Lisp s-expressions
Step 2: Evaluator - arithmetic operations (+, -, *, /)
Step 3: Environment - def!, let*, variable lookup
"""

import sys
import re
from typing import Any, Union, List, Dict, Optional


# ============ Types ============

class MalType:
    """Base class for all Mal types"""
    pass


class MalNil(MalType):
    def __init__(self):
        pass

    def __str__(self):
        return "nil"

    def __eq__(self, other):
        return isinstance(other, MalNil)


class MalBoolean(MalType):
    def __init__(self, value: bool):
        self.value = value

    def __str__(self):
        return "true" if self.value else "false"

    def __eq__(self, other):
        return isinstance(other, MalBoolean) and self.value == other.value


class MalNumber(MalType):
    def __init__(self, value: int):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return isinstance(other, MalNumber) and self.value == other.value


class MalString(MalType):
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        # Escape special characters for output
        escaped = self.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'

    def __eq__(self, other):
        return isinstance(other, MalString) and self.value == other.value


class MalSymbol(MalType):
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value

    def __eq__(self, other):
        return isinstance(other, MalSymbol) and self.value == other.value


class MalKeyword(MalType):
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return f":{self.value}"

    def __eq__(self, other):
        return isinstance(other, MalKeyword) and self.value == other.value


class MalList(MalType):
    def __init__(self, items: List[Any]):
        self.items = items

    def __str__(self):
        return "(" + " ".join(str(item) for item in self.items) + ")"

    def __eq__(self, other):
        return isinstance(other, MalList) and self.items == other.items


class MalVector(MalType):
    def __init__(self, items: List[Any]):
        self.items = items

    def __str__(self):
        return "[" + " ".join(str(item) for item in self.items) + "]"

    def __eq__(self, other):
        return isinstance(other, MalVector) and self.items == other.items


class MalHashMap(MalType):
    def __init__(self, dict_data: Dict[Any, Any]):
        self.data = dict_data

    def __str__(self):
        items = []
        for dict_key, (orig_key, value) in self.data.items():
            # orig_key is the actual Mal object (MalString, MalKeyword, etc.)
            items.append(str(orig_key))
            items.append(str(value))
        return "{" + " ".join(items) + "}"

    def __eq__(self, other):
        if not isinstance(other, MalHashMap):
            return False
        if len(self.data) != len(other.data):
            return False
        for k, (key1, val1) in self.data.items():
            if k not in other.data:
                return False
            _, val2 = other.data[k]
            # Compare values
            if val1 != val2:
                return False
        return True


# Constants for convenience
NIL = MalNil()
TRUE = MalBoolean(True)
FALSE = MalBoolean(False)


# ============ Reader ============

class Reader:
    """Tokenizes and reads Mal expressions"""

    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[str]:
        """Return next token without consuming"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def next(self) -> Optional[str]:
        """Consume and return next token"""
        token = self.peek()
        if token is not None:
            self.pos += 1
        return token


def tokenize(input_str: str) -> List[str]:
    """Tokenize input string into Mal tokens"""
    # Order matters!
    pattern = r'''[\s,]*(
        "(?:\\.|[^\\"])*"          |  # Strings
        ;[^\n]*                    |  # Comments
        ~@                         |  # Splice-unquote
        -?\d+                      |  # Numbers (including negative)
        :[^\s{}\[\]()"`,;]+        |  # Keywords
        [^\s{}\[\]()"`,;@~^']+     |  # Symbols (everything else not a delimiter)
        \[                         |  # [
        \]                         |  # ]
        \{                         |  # {
        \}                         |  # }
        \(                         |  # (
        \)                         |  # )
        `                          |  # Backtick (quasiquote)
        @                          |  # At-sign (deref)
        ~                          |  # Tilde (unquote)
        \^                         |  # Caret (metadata)
        '                              # Quote
    )'''

    tokens = re.findall(pattern, input_str, re.VERBOSE)

    # Filter out comments, empty strings, and whitespace
    tokens = [t.strip() for t in tokens if not t.strip().startswith(';') and t.strip()]

    return tokens


def read_atom(reader: Reader) -> Any:
    """Read an atom (number, symbol, keyword, etc.)"""
    token = reader.next()

    # Number
    if re.match(r'^-?\d+$', token):
        return MalNumber(int(token))

    # Keyword
    if token.startswith(':') and len(token) > 1:
        return MalKeyword(token[1:])

    # String
    if token.startswith('"'):
        # Process escape sequences
        s = token[1:-1]  # Remove quotes
        s = s.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
        return MalString(s)

    # Special symbols
    if token == 'nil':
        return NIL
    if token == 'true':
        return TRUE
    if token == 'false':
        return FALSE

    # Regular symbol
    return MalSymbol(token)


def read_list(reader: Reader, start: str, end: str, cls) -> Any:
    """Read a list-like structure (list, vector, hash-map)"""
    ast = []

    while (token := reader.peek()) is not None:
        if token == end:
            break
        # Don't error on nested structures - read_form will handle them
        ast.append(read_form(reader))

    if reader.peek() is None:
        raise Exception(f"Unexpected end of input: expected '{end}'")

    reader.next()  # Consume closing bracket

    if cls == MalList:
        return MalList(ast)
    elif cls == MalVector:
        return MalVector(ast)
    elif cls == MalHashMap:
        if len(ast) % 2 != 0:
            raise Exception("Hash map must have even number of elements")
        # Use list of tuples to preserve key objects
        entries = []
        for i in range(0, len(ast), 2):
            entries.append((ast[i], ast[i + 1]))
        # Create wrapper for hash map that stores entries
        hm = {}
        for key, value in entries:
            # Create string key for dict lookup
            if isinstance(key, MalKeyword):
                dict_key = f"kw:{key.value}"
            elif isinstance(key, MalString):
                dict_key = f"str:{key.value}"
            else:
                dict_key = f"other:{key}"
            hm[dict_key] = (key, value)
        return MalHashMap(hm)


def read_form(reader: Reader) -> Any:
    """Read a single form from the reader"""
    token = reader.peek()

    if token is None:
        raise Exception("Unexpected end of input")

    if token == '(':
        reader.next()
        return read_list(reader, '(', ')', MalList)
    elif token == '[':
        reader.next()
        return read_list(reader, '[', ']', MalVector)
    elif token == '{':
        reader.next()
        return read_list(reader, '{', '}', MalHashMap)
    elif token == "'":
        reader.next()
        return MalList([MalSymbol('quote'), read_form(reader)])
    elif token == '`':
        reader.next()
        return MalList([MalSymbol('quasiquote'), read_form(reader)])
    elif token == '~':
        reader.next()
        return MalList([MalSymbol('unquote'), read_form(reader)])
    elif token == '~@':
        reader.next()
        return MalList([MalSymbol('splice-unquote'), read_form(reader)])
    elif token == '@':
        reader.next()
        return MalList([MalSymbol('deref'), read_form(reader)])
    elif token == '^':
        reader.next()
        meta = read_form(reader)
        obj = read_form(reader)
        return MalList([MalSymbol('with-meta'), obj, meta])
    else:
        return read_atom(reader)


def READ(input_str: str) -> Any:
    """Parse input string into Mal data structure"""
    tokens = tokenize(input_str)
    if not tokens:
        return NIL
    reader = Reader(tokens)
    return read_form(reader)


# ============ Evaluator ============

class Env:
    """Environment for storing variable bindings"""

    def __init__(self, outer: Optional['Env'] = None):
        self.data: Dict[str, Any] = {}
        self.outer = outer

    def set(self, key: str, value: Any) -> Any:
        """Set a key in the current environment"""
        self.data[key] = value
        return value

    def find(self, key: str) -> Optional['Env']:
        """Find the environment containing a key"""
        if key in self.data:
            return self
        elif self.outer:
            return self.outer.find(key)
        return None

    def get(self, key: str) -> Any:
        """Get a value from the environment"""
        env = self.find(key)
        if env:
            return env.data[key]
        else:
            raise Exception(f"'{key}' not found")


def eval_ast(ast: Any, env: Env) -> Any:
    """Evaluate a node in the AST"""
    if isinstance(ast, MalSymbol):
        return env.get(ast.value)
    elif isinstance(ast, MalList):
        return MalList([EVAL(item, env) for item in ast.items])
    elif isinstance(ast, MalVector):
        return MalVector([EVAL(item, env) for item in ast.items])
    elif isinstance(ast, MalHashMap):
        new_data = {}
        for dict_key, (orig_key, value) in ast.data.items():
            # Evaluate values but not keys
            new_data[dict_key] = (orig_key, EVAL(value, env))
        return MalHashMap(new_data)
    else:
        return ast


def EVAL(ast: Any, env: Env) -> Any:
    """Evaluate an AST node in the given environment"""
    # If not a list, return as-is
    if not isinstance(ast, MalList):
        return eval_ast(ast, env)

    # Empty list
    if len(ast.items) == 0:
        return ast

    # First element determines what to do
    first = ast.items[0]

    # Special forms (check before evaluating)
    if isinstance(first, MalSymbol):
        # def!
        if first.value == 'def!':
            _, key, value_expr = ast.items
            value = EVAL(value_expr, env)
            return env.set(key.value, value)

        # let*
        if first.value == 'let*':
            _, bindings, body = ast.items
            let_env = Env(outer=env)

            # Bindings can be a list or vector
            if isinstance(bindings, MalList):
                binding_items = bindings.items
            elif isinstance(bindings, MalVector):
                binding_items = bindings.items
            else:
                raise Exception("let* bindings must be a list or vector")

            for i in range(0, len(binding_items), 2):
                key = binding_items[i]
                value_expr = binding_items[i + 1]
                if isinstance(key, MalSymbol):
                    value = EVAL(value_expr, let_env)
                    let_env.set(key.value, value)

            return EVAL(body, let_env)

        # Built-in arithmetic functions (handle before eval_ast)
        if first.value in ('+', '-', '*', '/'):
            # Evaluate all arguments
            args = [EVAL(arg, env) for arg in ast.items[1:]]

            if first.value == '+':
                if all(isinstance(a, MalNumber) for a in args):
                    return MalNumber(sum(a.value for a in args))
            elif first.value == '-':
                if len(args) >= 1 and all(isinstance(a, MalNumber) for a in args):
                    if len(args) == 1:
                        return MalNumber(-args[0].value)
                    return MalNumber(args[0].value - sum(a.value for a in args[1:]))
            elif first.value == '*':
                if all(isinstance(a, MalNumber) for a in args):
                    result = 1
                    for a in args:
                        result *= a.value
                    return MalNumber(result)
            elif first.value == '/':
                if len(args) >= 1 and all(isinstance(a, MalNumber) for a in args):
                    if len(args) == 1:
                        return MalNumber(1 // args[0].value if args[0].value != 0 else 0)
                    result = args[0].value
                    for a in args[1:]:
                        if a.value == 0:
                            raise Exception("Division by zero")
                        result //= a.value
                    return MalNumber(result)

            raise Exception(f"Arithmetic operation requires numeric arguments")

    # Function application
    evaluated = eval_ast(ast, env)
    if isinstance(evaluated, MalList) and len(evaluated.items) > 0:
        func = evaluated.items[0]
        args = evaluated.items[1:]

        # If func is a symbol that wasn't handled above, it's an error
        if isinstance(func, MalSymbol):
            raise Exception(f"'{func.value}' not found")

        raise Exception(f"Cannot apply {func}")

    return evaluated


# ============ Printer ============

def PRINT(exp: Any) -> str:
    """Convert Mal data structure to string"""
    return str(exp)


# ============ REPL ============

def rep(input_str: str, env: Env) -> str:
    """Read-Eval-Print"""
    try:
        ast = READ(input_str)
        result = EVAL(ast, env)
        return PRINT(result)
    except Exception as e:
        return str(e)


def main():
    """Main REPL loop"""
    # Create repl environment with arithmetic functions
    repl_env = Env()

    # Note: Arithmetic functions are built-in in EVAL, not stored in env
    # They're handled directly in the function application code

    # Check if we're in non-interactive mode (for testing)
    if not sys.stdin.isatty():
        # Non-interactive mode: read all lines from stdin
        for line in sys.stdin:
            line = line.rstrip('\n')
            if line:  # Skip empty lines
                print(rep(line, repl_env))
        return

    # Interactive mode
    print("Mal Step 3 - REPL with EVAL")
    print("Type 'exit' or Ctrl+C to quit\n")

    while True:
        try:
            # Read input from user
            line = input("user> ")

            # Exit on empty input or 'exit'
            if not line or line.strip() == "exit":
                continue

            # Process and print result
            result = rep(line, repl_env)
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
