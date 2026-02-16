#!/usr/bin/env python3
import re

input_str = '(def! a (list 1 2))'
pattern = r'''[\s,]*(
    "(?:\\.|[^\\"])*"          |  # Strings
    ;[^\n]*                    |  # Comments
    ~@                         |  # Splice-unquote
    -?\d+                      |  # Numbers (including negative)
    :[^\s{}\[\]()"`,;]+        |  # Keywords
    [^\s{}\[\]()"`,;@~^]+     |  # Symbols (everything else not a delimiter)
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
print('Input:', input_str)
print('Tokens:', tokens)
