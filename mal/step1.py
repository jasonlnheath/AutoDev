#!/usr/bin/env python
"""
Mal Step 1: READ and PRINT

This step implements the reader (parse Lisp expressions) and printer
(format them back), but does not evaluate.
"""

import sys
import re
from typing import Any, Union, List, Optional


# ============ Types ============

class MalType:
    """Base class for all Mal types"""
    pass


class MalNil(MalType):
    def __init__(self):
        pass

    def __str__(self):
        return "nil"


class MalBoolean(MalType):
    def __init__(self, value: bool):
        self.value = value

    def __str__(self):
        return "true" if self.value else "false"


class MalNumber(MalType):
    def __init__(self, value: int):
        self.value = value

    def __str__(self):
        return str(self.value)


class MalString(MalType):
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        # Escape special characters for output
        escaped = self.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'


class MalSymbol(MalType):
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


class MalKeyword(MalType):
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return f":{self.value}"


class MalList(MalType):
    def __init__(self, items: List[Any]):
        self.items = items

    def __str__(self):
        return "(" + " ".join(str(item) for item in self.items) + ")"


class MalVector(MalType):
    def __init__(self, items: List[Any]):
        self.items = items

    def __str__(self):
        return "[" + " ".join(str(item) for item in self.items) + "]"


class MalHashMap(MalType):
    def __init__(self, entries: List[tuple]):
        self.entries = entries  # List of (key, value) tuples

    def __str__(self):
        items = []
        for key, value in self.entries:
            items.append(str(key))
            items.append(str(value))
        return "{" + " ".join(items) + "}"


# Constants
NIL = MalNil()
TRUE = MalBoolean(True)
FALSE = MalBoolean(False)


# ============ Reader ============

class Reader:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[str]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def next(self) -> Optional[str]:
        token = self.peek()
        if token is not None:
            self.pos += 1
        return token


def tokenize(input_str: str) -> List[str]:
    """Tokenize input string into Mal tokens"""
    # Order matters! Earlier patterns match first.
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
    tokens = [t.strip() for t in tokens if not t.strip().startswith(';') and t.strip()]
    return tokens


def read_atom(reader: Reader) -> Any:
    token = reader.next()

    if re.match(r'^-?\d+$', token):
        return MalNumber(int(token))

    if token.startswith(':') and len(token) > 1:
        return MalKeyword(token[1:])

    if token.startswith('"'):
        s = token[1:-1]
        s = s.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
        return MalString(s)

    if token == 'nil':
        return NIL
    if token == 'true':
        return TRUE
    if token == 'false':
        return FALSE

    return MalSymbol(token)


def read_list(reader: Reader, end: str) -> Any:
    ast = []

    while (token := reader.peek()) is not None:
        if token == end:
            break
        ast.append(read_form(reader))

    if reader.peek() is None:
        raise Exception(f"Unexpected end of input: expected '{end}'")

    reader.next()  # Consume closing bracket
    return ast


def read_form(reader: Reader) -> Any:
    token = reader.peek()

    if token is None:
        raise Exception("Unexpected end of input")

    if token == '(':
        reader.next()
        return MalList(read_list(reader, ')'))
    elif token == '[':
        reader.next()
        return MalVector(read_list(reader, ']'))
    elif token == '{':
        reader.next()
        items = read_list(reader, '}')
        if len(items) % 2 != 0:
            raise Exception("Hash map must have even number of elements")
        entries = [(items[i], items[i + 1]) for i in range(0, len(items), 2)]
        return MalHashMap(entries)
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


# ============ Printer ============

def PRINT(exp: Any) -> str:
    """Convert Mal data structure to string"""
    return str(exp)


# ============ REPL ============

def rep(input_str: str) -> str:
    """Read-Eval-Print (no eval for Step 1)"""
    try:
        ast = READ(input_str)
        return PRINT(ast)
    except Exception as e:
        return str(e)


def main():
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.rstrip('\n')
            if line:
                print(rep(line))
        return

    print("Mal Step 1 - READ and PRINT")
    print("Type 'exit' or Ctrl+C to quit\n")

    while True:
        try:
            line = input("user> ")
            if not line or line.strip() == "exit":
                continue
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
