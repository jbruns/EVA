#!/usr/bin/env python
import os
import sys
from rich import print
from backends.llamacpp.backend import LlamaCppBackend as ircawp

prompt = " ".join(sys.argv[1:])

if not prompt:
    print("Huh?")
    os._exit(-1)


ircawp = ircawp(model="default")
# ircawp = ircawp(model="mamba-3b_80")

print(ircawp.query(prompt, raw=False))
