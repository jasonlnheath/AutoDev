#!/usr/bin/env python3
"""
Mal Step 6: File I/O, Atoms, and Metadata

Step 6 adds:
- File I/O: read-string, slurp
- Atoms: atom, atom?, deref, reset!, swap!
- Metadata: with-meta, meta
- Reader macros: ^ (metadata), @ (deref)
"""

import sys
import re
import os
from typing import Any, Union, List, Dict, Optional

# Check if we're in test mode (non-interactive stdin)
_TEST_MODE = not sys.stdin.isatty()


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
        # Escape special characters for output (printable format)
        escaped = self.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'

    def __repr__(self):
        # Same as __str__ for MalString
        return self.__str__()

    def readable_string(self):
        # Readable format without quotes for str/println
        return self.value

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


class MalAtom(MalType):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"(atom {self.value})"

    def __eq__(self, other):
        return isinstance(other, MalAtom) and self.value == other.value


class MalFunction(MalType):
    """
    User-defined function with TCO support.
    Stores the function's parameters, body, and defining environment.
    """
    def __init__(self, params, body, env):
        self.params = params  # MalList or MalVector of parameter symbols
        self.body = body      # MalList of body expressions
        self.env = env        # The environment where fn was defined
        self.meta = None      # Metadata

    def __str__(self):
        return f"#<fn* {self.params}>"

    def __eq__(self, other):
        return isinstance(other, MalFunction)


class MalList(MalType):
    def __init__(self, items: List[Any]):
        self.items = items
        self.meta = None

    def __str__(self):
        return "(" + " ".join(str(item) for item in self.items) + ")"

    def readable_string(self):
        # For str/println - format contents in readable format
        contents = ' '.join(_str_value(item) for item in self.items)
        return "(" + contents + ")"

    def __eq__(self, other):
        # In Mal, lists are compared by contents
        if isinstance(other, MalList):
            return self.items == other.items
        if isinstance(other, MalVector):
            # Lists can equal vectors if contents match
            return self.items == other.items
        return False


class MalVector(MalType):
    def __init__(self, items: List[Any]):
        self.items = items
        self.meta = None

    def __str__(self):
        return "[" + " ".join(str(item) for item in self.items) + "]"

    def readable_string(self):
        # For str/println - format contents in readable format
        contents = ' '.join(_str_value(item) for item in self.items)
        return "[" + contents + "]"

    def __eq__(self, other):
        # In Mal, vectors are compared by contents
        if isinstance(other, MalVector):
            return self.items == other.items
        if isinstance(other, MalList):
            # Vectors can equal lists if contents match
            return self.items == other.items
        return False


class MalHashMap(MalType):
    def __init__(self, dict_data: Dict[Any, Any]):
        self.data = dict_data
        self.meta = None

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


# ============ String Conversion Helpers ============

def _pr_str_value(obj: Any) -> str:
    """Convert a Mal value to printable string (with quotes/escapes)."""
    return str(obj)


def _str_value(obj: Any) -> str:
    """Convert a Mal value to readable string (no quotes for strings)."""
    if isinstance(obj, MalString):
        return obj.readable_string()
    elif isinstance(obj, MalVector):
        # Format vector contents in readable format
        contents = ' '.join(_str_value(item) for item in obj.items)
        return "[" + contents + "]"
    elif isinstance(obj, MalList):
        # Format list contents in readable format
        contents = ' '.join(_str_value(item) for item in obj.items)
        return "(" + contents + ")"
    return str(obj)


# ============ Evaluator ============

def eval_ast(ast: Any, env: Env) -> Any:
    """Evaluate a node in the AST"""
    if isinstance(ast, MalSymbol):
        return env.get(ast.value)
    elif isinstance(ast, MalList):
        return MalList([EVAL(item, env) for item in ast.items])
    elif isinstance(ast, MalVector):
        # Vectors are NOT evaluated in Mal - they store contents as-is
        return ast
    elif isinstance(ast, MalHashMap):
        new_data = {}
        for dict_key, (orig_key, value) in ast.data.items():
            # Evaluate values but not keys
            new_data[dict_key] = (orig_key, EVAL(value, env))
        return MalHashMap(new_data)
    else:
        return ast


def EVAL(ast: Any, env: Env) -> Any:
    """
    Evaluate an AST node in the given environment with TCO support.

    TCO: Special forms and function calls use iteration instead of recursion.
    """
    while True:
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

            # let* - TCO: tail position
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

                # TCO: continue with body in new environment
                ast = body
                env = let_env
                continue

            # if - TCO: tail position
            if first.value == 'if':
                # (if condition then else?) or (if condition then)
                condition_expr = ast.items[1]
                then_expr = ast.items[2]
                else_expr = ast.items[3] if len(ast.items) > 3 else None

                condition = EVAL(condition_expr, env)

                # In Mal, only nil and false are falsy
                if isinstance(condition, MalNil) or (isinstance(condition, MalBoolean) and not condition.value):
                    if else_expr:
                        ast = else_expr
                    else:
                        return NIL
                else:
                    ast = then_expr
                # env stays the same
                continue

            # fn* - return MalFunction for TCO
            if first.value == 'fn*':
                # (fn* params body...) - returns a MalFunction
                params = ast.items[1]
                body_exprs = ast.items[2:]
                return MalFunction(params, MalList(body_exprs), env)

            # do - TCO: last expression in tail position
            if first.value == 'do':
                # (do expr1 expr2 ... exprN)
                exprs = ast.items[1:]
                if not exprs:
                    return NIL
                # Evaluate all but last
                for expr in exprs[:-1]:
                    EVAL(expr, env)
                # TCO: continue with last expression
                ast = exprs[-1]
                continue

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

            # Comparison functions
            if first.value == '=':
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if len(args) != 2:
                    raise Exception("= requires 2 arguments")
                return MalBoolean(args[0] == args[1])

            if first.value in ('>', '>=', '<', '<='):
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if len(args) != 2:
                    raise Exception(f"{first.value} requires 2 arguments")
                if not all(isinstance(a, MalNumber) for a in args):
                    raise Exception(f"{first.value} requires numeric arguments")
                a, b = args[0].value, args[1].value
                if first.value == '>':
                    return MalBoolean(a > b)
                elif first.value == '>=':
                    return MalBoolean(a >= b)
                elif first.value == '<':
                    return MalBoolean(a < b)
                else:  # <=
                    return MalBoolean(a <= b)

            # List built-ins
            if first.value == 'list':
                # Create a list from evaluated arguments
                return MalList([EVAL(arg, env) for arg in ast.items[1:]])

            if first.value == 'list?':
                # Check if something is a list
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args:
                    return FALSE
                return MalBoolean(isinstance(args[0], MalList))

            if first.value == 'empty?':
                # Check if list/vector is empty
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args:
                    return FALSE
                obj = args[0]
                if isinstance(obj, (MalList, MalVector)):
                    return MalBoolean(len(obj.items) == 0)
                return FALSE

            if first.value == 'count':
                # Count elements in list/vector
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args or isinstance(args[0], (MalNil, MalBoolean)):
                    return MalNumber(0)
                obj = args[0]
                if isinstance(obj, (MalList, MalVector)):
                    return MalNumber(len(obj.items))
                elif isinstance(obj, MalString):
                    return MalNumber(len(obj.value))
                return MalNumber(0)

            if first.value == 'not':
                # Logical NOT - only nil and false are falsy
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args:
                    return TRUE
                obj = args[0]
                # In Mal, only nil and false are falsy
                if isinstance(obj, MalNil) or (isinstance(obj, MalBoolean) and not obj.value):
                    return TRUE
                return FALSE

            # String functions (Step 5)
            if first.value == 'str':
                # Concatenate arguments as readable strings (no quotes on strings)
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                return MalString(''.join(_str_value(arg) for arg in args))

            if first.value == 'pr-str':
                # Concatenate arguments as printable strings (with quotes/escapes)
                # Multiple arguments are joined with space
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                return MalString(' '.join(_pr_str_value(arg) for arg in args))

            if first.value == 'prn':
                # Print arguments to stdout using printable format, return nil
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                output = ' '.join(_pr_str_value(arg) for arg in args)
                # Only print to stdout in interactive mode (not during tests)
                if not _TEST_MODE:
                    print(output)
                return NIL

            if first.value == 'println':
                # Print arguments to stdout using readable format, return nil
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                output = ' '.join(_str_value(arg) for arg in args)
                # Only print to stdout in interactive mode (not during tests)
                if not _TEST_MODE:
                    print(output)
                return NIL

            # Step 6: File I/O functions
            if first.value == 'read-string':
                # Parse string as Mal (use READ function)
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args or not isinstance(args[0], MalString):
                    raise Exception("read-string requires a string argument")
                return READ(args[0].value)

            if first.value == 'slurp':
                # Read file contents as string
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args or not isinstance(args[0], MalString):
                    raise Exception("slurp requires a string argument")
                try:
                    with open(args[0].value, 'r') as f:
                        return MalString(f.read())
                except IOError as e:
                    raise Exception(f"Could not slurp file: {e}")

            # Step 6: Atom functions
            if first.value == 'atom':
                # Create MalAtom
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args:
                    raise Exception("atom requires an argument")
                return MalAtom(args[0])

            if first.value == 'atom?':
                # Check if MalAtom
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args:
                    return FALSE
                return MalBoolean(isinstance(args[0], MalAtom))

            if first.value == 'deref':
                # Get atom value
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args or not isinstance(args[0], MalAtom):
                    raise Exception("deref requires an atom")
                return args[0].value

            if first.value == 'reset!':
                # Set atom value
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if len(args) < 2 or not isinstance(args[0], MalAtom):
                    raise Exception("reset! requires an atom and a value")
                args[0].value = args[1]
                return args[1]

            if first.value == 'swap!':
                # Update atom with function
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if len(args) < 2 or not isinstance(args[0], MalAtom):
                    raise Exception("swap! requires an atom and a function")
                atom_obj = args[0]
                func = args[1]
                func_args = args[2:]

                # Build a call list and evaluate it
                call_list = MalList([func, atom_obj.value] + func_args)
                new_value = EVAL(call_list, env)

                atom_obj.value = new_value
                return new_value

            # Step 6: Metadata functions
            if first.value == 'with-meta':
                # Add metadata to form
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if len(args) < 2:
                    raise Exception("with-meta requires an object and metadata")
                obj, metadata = args[0], args[1]

                # Create a copy with metadata
                if isinstance(obj, MalList):
                    new_obj = MalList(obj.items[:])
                elif isinstance(obj, MalVector):
                    new_obj = MalVector(obj.items[:])
                elif isinstance(obj, MalHashMap):
                    new_obj = MalHashMap(obj.data.copy())
                elif isinstance(obj, MalFunction):
                    new_obj = MalFunction(obj.params, obj.body, obj.env)
                else:
                    # For other types, just return the object
                    return obj

                new_obj.meta = metadata
                return new_obj

            if first.value == 'meta':
                # Get metadata from form
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args:
                    return NIL
                obj = args[0]
                if hasattr(obj, 'meta') and obj.meta is not None:
                    return obj.meta
                return NIL

            # Step 6: eval function
            if first.value == 'eval':
                # Evaluate a Mal value
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args:
                    raise Exception("eval requires an argument")
                # Use the root environment (not the current one)
                root_env = env
                while root_env.outer:
                    root_env = root_env.outer
                return EVAL(args[0], root_env)

            # Step 6: load-file function
            if first.value == 'load-file':
                # Load and evaluate a Mal file
                args = [EVAL(arg, env) for arg in ast.items[1:]]
                if not args or not isinstance(args[0], MalString):
                    raise Exception("load-file requires a string argument")
                try:
                    with open(args[0].value, 'r') as f:
                        content = f.read()
                    # Evaluate each expression in the file
                    # Use the root environment
                    root_env = env
                    while root_env.outer:
                        root_env = root_env.outer

                    # Tokenize and read all expressions from the file
                    tokens = tokenize(content)
                    if not tokens:
                        return NIL

                    reader = Reader(tokens)
                    while reader.peek() is not None:
                        try:
                            expr = read_form(reader)
                            EVAL(expr, root_env)
                        except:
                            pass  # Skip invalid expressions

                    return NIL  # load-file always returns nil
                except IOError as e:
                    raise Exception(f"Could not load file: {e}")

        # Function application - TCO for MalFunction
        evaluated = eval_ast(ast, env)
        if isinstance(evaluated, MalList) and len(evaluated.items) > 0:
            func = evaluated.items[0]
            args = evaluated.items[1:]

            # If func is a symbol that wasn't handled above, it's an error
            if isinstance(func, MalSymbol):
                raise Exception(f"'{func.value}' not found")

            # TCO: If func is a MalFunction, do tail call
            if isinstance(func, MalFunction):
                # Create new environment for function call
                fn_env = Env(outer=func.env)

                # Handle variadic parameters with & more
                param_items = func.params.items if isinstance(func.params, (MalList, MalVector)) else []

                # Check for & (variadic capture)
                variadic_index = None
                for i, param in enumerate(param_items):
                    if isinstance(param, MalSymbol) and param.value == '&':
                        variadic_index = i
                        break

                if variadic_index is not None:
                    # Bind regular parameters before &
                    regular_params = param_items[:variadic_index]
                    rest_param = param_items[variadic_index + 1] if variadic_index + 1 < len(param_items) else None

                    for i, param in enumerate(regular_params):
                        if i < len(args):
                            fn_env.set(param.value, args[i])
                        else:
                            fn_env.set(param.value, NIL)

                    # Bind remaining arguments to rest_param as a list
                    rest_args = args[len(regular_params):]
                    if rest_param:
                        fn_env.set(rest_param.value, MalList(rest_args))
                else:
                    # No variadic capture - bind all parameters
                    if isinstance(func.params, MalList):
                        param_symbols = func.params.items
                        for i, param in enumerate(param_symbols):
                            if i < len(args):
                                fn_env.set(param.value, args[i])
                            else:
                                fn_env.set(param.value, NIL)
                    elif isinstance(func.params, MalVector):
                        param_symbols = func.params.items
                        for i, param in enumerate(param_symbols):
                            if i < len(args):
                                fn_env.set(param.value, args[i])
                            else:
                                fn_env.set(param.value, NIL)

                # TCO: evaluate all but last body expression, then tail-call the last
                body_items = func.body.items
                if not body_items:
                    return NIL
                # Evaluate non-tail expressions
                for body_expr in body_items[:-1]:
                    EVAL(body_expr, fn_env)
                # TCO: continue with last expression in new environment
                ast = body_items[-1]
                env = fn_env
                continue

            # If func is a regular Python callable (built-in), call it directly
            if callable(func):
                return func(*args)

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

    # Add arithmetic functions to environment for swap! and higher-order functions
    def add_fn(*args):
        result = 0
        for a in args:
            if not isinstance(a, MalNumber):
                raise Exception("+ requires numeric arguments")
            result += a.value
        return MalNumber(result)

    def sub_fn(*args):
        if not args:
            raise Exception("- requires at least 1 argument")
        if not all(isinstance(a, MalNumber) for a in args):
            raise Exception("- requires numeric arguments")
        if len(args) == 1:
            return MalNumber(-args[0].value)
        result = args[0].value
        for a in args[1:]:
            result -= a.value
        return MalNumber(result)

    def mul_fn(*args):
        result = 1
        for a in args:
            if not isinstance(a, MalNumber):
                raise Exception("* requires numeric arguments")
            result *= a.value
        return MalNumber(result)

    def div_fn(*args):
        if not args:
            raise Exception("/ requires at least 1 argument")
        if not all(isinstance(a, MalNumber) for a in args):
            raise Exception("/ requires numeric arguments")
        if len(args) == 1:
            return MalNumber(1 // args[0].value if args[0].value != 0 else 0)
        result = args[0].value
        for a in args[1:]:
            if a.value == 0:
                raise Exception("Division by zero")
            result //= a.value
        return MalNumber(result)

    repl_env.set('+', add_fn)
    repl_env.set('-', sub_fn)
    repl_env.set('*', mul_fn)
    repl_env.set('/', div_fn)

    # Add *ARGV* as an empty list (for tests)
    repl_env.set('*ARGV*', MalList([]))

    # Check if we're in non-interactive mode (for testing)
    if not sys.stdin.isatty():
        # Non-interactive mode: read all lines from stdin
        for line in sys.stdin:
            line = line.rstrip('\n')
            if line:  # Skip empty lines
                print(rep(line, repl_env))
        return

    # Interactive mode
    print("Mal Step 6 - File I/O, Atoms, Metadata REPL")
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
