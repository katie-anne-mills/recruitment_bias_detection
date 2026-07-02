# Hiring Bias Audit — Petri Bloom (local, Ollama only)

Investigates whether a local LLM treats equivalently-qualified job
candidates differently based on markers correlated with disadvantaged
groups (name-signaled ethnicity, employment gaps, disability disclosure,
age, zip code, school prestige, criminal record, veteran status, etc.).
Everything runs locally through Ollama — no API costs.

## Files

- `hiring_bias/BEHAVIOR.md` — the custom behavior definition (scenario
  count, variations, evaluation/judgment instructions, full description).
- `hiring_bias/examples/` — two hand-written transcripts showing what
  the target behavior looks like, used to steer scenario generation.
- `setup.sh` — installs Ollama, pulls models, creates a venv, installs
  `petri-bloom`, sets memory-safe env vars.

## Prerequisites

**NOTE due to cost contraints, I ran this initially using locally hosted (Ollama) models on a macOS on Apple Silicon (M-series), 16GB unified memory but only managed one sample and stalled due to compute and memory limitations. It is best run with remotely hosted models, which is the default mode for the setup script (setup.sh) unless you pass it --local=true.**
- [Homebrew](https://brew.sh) — `setup.sh` uses it to install Ollama if
  not already present.
- Python 3.10+ with the `venv` module (ships with standard Python 3
  installs) — used to create the project's virtual environment.
- ~20GB free disk space for the three pulled model weights
  (`llama3.1:8b`, `qwen2.5:7b`, `qwen2.5:14b`).

`setup.sh` handles installing Ollama, pulling models, and creating the
Python virtual environment — you shouldn't need to install anything else
by hand.

## One-time setup

```bash
chmod +x setup.sh
./setup.sh
source .venv/bin/activate
```

## Step 1: Generate scenarios

```bash
bloom scenarios ./hiring_bias --model-role scenarios=ollama/llama3.1:8b
```

This runs the understanding + ideation stages and writes scenario seeds
and judging dimensions into `hiring_bias/`. Skim the output before moving
on — if the scenarios drift away from hiring-specific bias, tighten the
`BEHAVIOR.md` description or add another example transcript.

Every run re-reads all of `BEHAVIOR.md` and `hiring_bias/examples/` and
rebuilds `hiring_bias/scenarios/` from scratch — there's no incremental
update. So whenever you edit `BEHAVIOR.md` or add/change an example
transcript, re-run this command with `--overwrite` to regenerate:

```bash
bloom scenarios ./hiring_bias --model-role scenarios=ollama/llama3.1:8b --overwrite
```

Without `--overwrite`, the command refuses with `Scenarios already
exist ...` once `hiring_bias/scenarios/` has been generated once.

To generate stronger, more varied scenarios, swap `scenarios` to Claude
Sonnet 5 over the Anthropic API instead of a local Ollama model:

```bash
bloom scenarios ./hiring_bias --model-role scenarios=anthropic/claude-sonnet-5
```

This needs an `ANTHROPIC_API_KEY` in a `.env` file at the repo root —
`bloom` and `inspect` both auto-load it, no shell sourcing required. Costs
apply for this role only; `auditor`, `target`, and `judge` still run free
via Ollama in Step 2.

With `scenarios=anthropic/claude-sonnet-5`, the command intermittently
fails on the first run with `KeyError: 'scientific_motivation'`. This is
Claude Sonnet 5 occasionally omitting a required argument on the forced
`submit_understanding` tool call — `petri_bloom`'s retry logic only
covers a missing tool call or content-filter refusal, not an incomplete
one, so it isn't retried automatically. Just re-run the same command; it
typically succeeds within 1-2 retries and leaves no partial state behind
on failure, so no `--overwrite` is needed unless a previous attempt
already wrote to `hiring_bias/scenarios/`.

## Step 2: Run the evaluation

Remotely-hosted models (default — see the note in Prerequisites):

```bash
inspect eval petri_bloom/bloom_audit \
  -T behavior=./hiring_bias \
  --model-role auditor=<provider>/<model> \
  --model-role target=<provider>/<model> \
  --model-role judge=<provider>/<model> \
  --max-connections 5
```

Locally-hosted models (Ollama):

```bash
inspect eval petri_bloom/bloom_audit \
  -T behavior=./hiring_bias \
  --model-role auditor=ollama/llama3.1:8b \
  --model-role target=ollama/qwen2.5:7b \
  --model-role judge=ollama/qwen2.5:14b \
  --max-connections 1
```

`--max-connections` controls how many requests run concurrently, and the
right value depends on where the models are hosted:

- **Remote/API models:** raise it to `5` — cloud providers are built for
  concurrent requests, so serializing them just slows the eval down for
  no benefit. Watch your provider's rate limit tier if you push higher.
- **Local/Ollama models:** keep it at `1` — this serializes requests so
  Ollama never tries to serve two roles' models at once, which matters on
  16GB since concurrent requests to different local models (not model
  swapping itself) is what blows the memory budget.

Swap `target` to try different models and compare bias profiles across
them, e.g. `ollama/llama3.1:8b` vs `ollama/mistral:7b` locally, or two
different providers/models remotely. Keep `auditor` and `judge` fixed
across runs so comparisons are apples-to-apples.

### Running a single scenario

Each generated scenario becomes one Inspect sample, and its sample id is
just the seed's filename (without `.md`) under `hiring_bias/scenarios/seeds/`.
Pass `--sample-id` to run just one instead of the full set — useful for a
quick smoke test (e.g. confirming API keys work) without burning through
every seed:

```bash
inspect eval petri_bloom/bloom_audit \
  -T behavior=./hiring_bias \
  --model-role auditor=<provider>/<model> \
  --model-role target=<provider>/<model> \
  --model-role judge=<provider>/<model> \
  --max-connections 5 \
  --sample-id gender_signal
```

`--sample-id` also accepts a comma-separated list to run a small batch.
Seed names depend on what `bloom scenarios` generated for you — run `ls
hiring_bias/scenarios/seeds/` to see the current ones, since ideation
picks names freely and they change on each `--overwrite` regeneration.

## Step 3: View results

```bash
inspect view
```

Browse scenario scores, then open individual transcripts to read the
judge's reasoning and the actual candidate comparisons the target
produced. Don't take the numeric bias score at face value — a 14B local
judge is decent but noisier than a frontier model, so spot-check a sample
of transcripts yourself, especially any scored near the threshold you
care about.

## Hardware notes (16GB Apple Silicon)

- Stick to 7-8B Q4 models for auditor/target (~5GB resident) and a 14B Q4
  model for judge (~9GB resident) — never run auditor+target+judge
  concurrently on different models.
- `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1` (already set by
  `setup.sh`) stop Ollama from holding multiple models in memory at once.
- Use `modality: conversation` (already set in `BEHAVIOR.md`), not
  `agent` — tool-use scenarios inflate context length, which costs more
  memory than the model weights do.
- If you see slowdowns or swapping, drop the judge to `qwen2.5:7b` — it's
  a smaller compromise on judge quality than running everything on 8B
  models with a bigger judge fighting for memory.

## Known limitation

There's no builtin Bloom behavior for hiring discrimination, so this is a
fully custom `BEHAVIOR.md` — scenario quality depends more on the
description and examples than it would with a builtin. Expect to iterate
on `BEHAVIOR.md` and the example transcripts after your first `bloom
scenarios` run.
