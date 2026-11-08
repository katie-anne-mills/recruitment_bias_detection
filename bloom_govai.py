#!/usr/bin/env python3
"""Drop-in replacement for `bloom` that registers the GovAI Bedrock provider.

Usage (from the project root with .venv active):
  python bloom_govai.py scenarios ./hiring_bias --model-role scenarios=govai/anthropic.claude-sonnet-4-6
  python bloom_govai.py ... (any bloom subcommand)
"""

import sys
import govai_provider  # noqa: F401 — registers @modelapi(name="govai")
from petri_bloom._cli.main import cli

sys.exit(cli() or 0)
