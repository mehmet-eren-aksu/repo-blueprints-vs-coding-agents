#!/usr/bin/env python3
"""A do-nothing implementation: copies stdin to stdout and exits 0.

Cases this dummy passes are weak; they do not tell a real
implementation apart from one that does nothing.
"""
import sys

sys.stdout.write(sys.stdin.read())
