#!/usr/bin/env python3
"""Drop-in replacement for `inspect` that registers the GovAI Bedrock provider.

Usage (from the project root with .venv active):
  python inspect_govai.py eval petri_bloom/bloom_audit -T behavior=./hiring_bias ...
  python inspect_govai.py view
"""

import sys
import govai_provider  # noqa: F401 — registers @modelapi(name="govai")
from inspect_ai._cli.main import main

sys.exit(main() or 0)
