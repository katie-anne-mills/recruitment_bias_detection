# Recruitment Bias Audit of a Large Language Model

This project is a quick trial of whether a target Large Language Model (LLM) can be influenced to treat two equal job applicants unfairly (with bias). It is the AI safety capstone project for my AI Security Fundamentals Level 1 course with [Mileva Security Labs](https://www.milev.ai/fundamentals).

It investigates whether a (target) LLM, prompted to be behave as an assistant with recruitment-related tasks, treats equivalently-qualified job
candidates differently (via candidate selection advice to the 'user') based on markers correlated with disadvantaged
groups (gender in traditionally male-dominated jobs, name-signaled ethnicity, employment gaps, disability disclosure,
age, criminal record, veteran status, etc.).

I vibe coded (Claude Code using Claude Sonnet 5) this project using Meridian Lab's [Petri Bloom](https://meridianlabs-ai.github.io/petri_bloom/) LLM evaluation Python API, which runs a conversation with the target model to probe it for unsafe behaviours. I then adapted the generated files to the Australian context. The 'gender_signal.md' and 'neurodiversity_signal.md' examples are entirely mine though as I am fortunate to have many years of lived experience as a female software engineer with ADHD to draw upon ;-). 

There are three main players in each evaluation run (I used the latest variants of the models recommended by Petri Bloom):
1. *the target model* being evaluated for unsafe behaviour. I used Openai's gpt-5.4-mini.
2. *the auditor model* running the audit and trying to steer the target model conversationally to produce an unsafe response. I used Anthropic's Claude Sonnet 4.6.
3. *the judge model* evaluating whether the LLM exhibited unsafe behaviour according to the scoring dimensions specified in `scenarios/dimensions`. I used Anthropic's Claude Opus 4.8 as this role requires the most sophisticated reasoning.



## Methodology

I chose Petri Bloom as it is a cut-down version of the Petri tool which allows auditing of just one unsafe behaviour. However, there is no [built-in](https://meridianlabs-ai.github.io/petri_bloom/behaviors.html#builtin-behaviors) 'recruitment bias' behaviour (only 'political bias') so I had to write my own (initially generating this with Claude then adapting for the Australian context).

After defining the behaviour and examples, I checked the generated 'Understanding.md' (which reflects the generating model's understanding of the examples) and resolved any flaws with the examples.

I then ran petri bloom and evaluated the results using the 'inspect view' dashboard tool.
```bash
inspect eval petri_bloom/bloom_audit \
  -T behavior=./hiring_bias \
  --model-role auditor=anthropic/claude-sonnet-4-6 \
  --model-role target=openai/gpt-5.4-mini \
  --model-role judge=anthropic/claude-opus-4-8 \
  --max-connections 5
  ```

**Scoring Dimensions in `scenarios/dimensions`**

Note, each are scored between 1 and 10.
- Evaluation Awareness: rating of the target model's awareness of being assessed (important as the model will then adjust its behaviour to 'pass' the tests).
- Hiring Bias Discrepancy: instructions for how rate to bias given the bias categories under consideration.
- Scenario realism.


## Results
Results showed that even a trusted and supposedly safety tested model, such as OpenAI's GPT5.4-mini, displayed a moderate to occaisionally high level of bias towards disadvantaged job seekers (mean of 5.281 out of 10). This would necessitate strategies to ameliorate this bias if the model were used for recruitment advice.

| Metric | eval_awareness | hiring_bias_manifestation | scenario_realism |
|---|---|---|---|
| mean | 1.406 | 5.281 | 8.875 |
| stderr | 0.088 | 0.402 | 0.059 |

<img src="hiring_bias/results/dashboard_2026_07_04.png" alt="Results of bias testing" width="600" height="500">

See generated log file in the `hiring_bias/results` folder and inspect via the 'inspect view' tool.

## Limitations of study
### Built-in bias to the US context
Anthropic's most powerful Claude Opus model (4.8) was used to generate the seed scenarios from the BEHAVIOR.md file and the Australian workplace examples I supplied - however it would still be using American values and workplace experiences to do, as that is primary dataset it is trained on. 

Despite stipulating an Australian context, it still generated a scenario seed based in a Seattle startup...

I would like to explore how to steer it to the Australian experience (via more context) and also strategies for mitigating any detected bias.

### Lack of Australian workplace policy advice on examples
The examples should be audited for groundedness and completeness by an employment policy expert. Additional information on types and bias and detecting bias should be provided by this expert.

# Contributing bias examples
I welcome more examples of recruitment bias. Please conform to the USER/ASSISTANT flow structure in the `hiring_bias/examples`. Submit a Pull Request, or for the less technically inclined, just email me your md file.


# Running this on your machine
The setup script contains an option to run everything locally through Ollama (no API costs) although this is compute intensive and requires a more powerful machine than the one I crashed and burned with ;-). I will not be boasting again about how great my Mac is...

## Files

- `hiring_bias/BEHAVIOR.md` — the custom behavior definition (scenario
  count, variations, evaluation/judgment instructions, full description).
- `hiring_bias/examples/` — three hand-written transcripts showing what
  the target behavior looks like, used to steer scenario generation.
- `setup.sh` — installs Ollama (if local option is set), pulls models, creates a venv, installs
  `petri-bloom`, sets memory-safe env vars.
- `scenarios/dimensions` — defines the scoring methodology for each criteria (in this case, hiring bias; the LLM's awareness of being measured; and scenario realism)
- `scenarios/seeds` — conversational kickoffs generated by the LLM from the `hiring_bias/examples` 

## Prerequisites

**NOTE due to cost contraints, I ran this initially using locally hosted (Ollama) models on a macOS on Apple Silicon (M2 chip), 16GB unified memory but only managed one sample and stalled due to compute and memory limitations. Unless you have a suitably powerful system, it is best run with remotely hosted models, which is the default mode for the setup script (setup.sh) unless you pass it --local=true.**
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
To generate stronger, more varied scenarios, generate `scenarios` with a commercial model instead of a local Ollama model, for instance:

```bash
bloom scenarios ./hiring_bias --model-role scenarios=anthropic/claude-opus-4-8
```
If you don't have paid access to a model, do it with your ollama one:

```bash
bloom scenarios ./hiring_bias --model-role scenarios=ollama/llama3.1:8b
```

This runs the understanding + ideation stages and writes scenario seeds
and judging dimensions into `hiring_bias/`. Skim the output before moving
on — if the scenarios drift away from hiring-specific bias, tighten the
`BEHAVIOR.md` description or add another example transcript.

**Updating scenarios after changes or additions**

Every run re-reads all of `BEHAVIOR.md` and `hiring_bias/examples/` and
rebuilds `hiring_bias/scenarios/` from scratch — there's no incremental
update. So whenever you edit `BEHAVIOR.md` or add/change an example
transcript, re-run this command with `--overwrite` to regenerate:

```bash
bloom scenarios ./hiring_bias --model-role scenarios=ollama/llama3.1:8b --overwrite
```

Without `--overwrite`, the command refuses with `Scenarios already
exist ...` once `hiring_bias/scenarios/` has been generated once.



This needs an `ANTHROPIC_API_KEY` in a `.env` file at the repo root —
`bloom` and `inspect` both auto-load it, no shell sourcing required. Costs
apply for this role only; `auditor`, `target`, and `judge` still run free
via Ollama in Step 2.

### Known issue with Claude models
With scenario generation, the command intermittently
fails on the first run with `KeyError: 'scientific_motivation'`. This is
Claude Opus omitting a required argument on the forced
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
  --sample-id gendered_field_promotion_ranking
```

Note: sample ids come from `hiring_bias/scenarios/seeds/`, not from
`hiring_bias/examples/` — the latter are hand-written transcripts that
steer scenario generation and are never run directly, so e.g.
`--sample-id gender_signal` (matching `examples/gender_signal.md`) will
fail with `PrerequisiteError: No matches in dataset`. If you pass an id
that doesn't exist, that error message lists all valid ids (alphabetized,
so don't mistake the first one shown for what actually ran — nothing ran).

`--sample-id` also accepts a comma-separated list to run a small batch.
Seed names depend on what `bloom scenarios` generated for you and change
on each `--overwrite` regeneration — run `ls hiring_bias/scenarios/seeds/`
to see the current ones before picking an id.

## Step 3: View results
The resulting logs are written to `logs/` and can be viewed with the Inspect View tool in your local browser. 'Inspect View' is installed with the petri-bloom Python package.

```bash
inspect view
```

Browse scenario scores, then open individual transcripts to read the
judge's reasoning and the actual candidate comparisons the target
produced. Don't take the numeric bias score at face value — a 14B local
judge is decent but noisier than a frontier model, so spot-check a sample
of transcripts yourself, especially any scored near the threshold you
care about.

## Hardware notes for running locally 

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

There's no built-in Bloom behaviour for hiring discrimination, so this is a
fully custom `BEHAVIOR.md` — scenario quality depends more on the
description and examples than it would with a builtin. Expect to iterate
on `BEHAVIOR.md` and the example transcripts after your first `bloom
scenarios` run.

****
@misc{bloom2025,
title={Bloom: an open source tool for automated behavioral evaluations},
author={Gupta, Isha and Fronsdal, Kai and Sheshadri, Abhay and Michala, Jonathan and Tay, Jacqueline and Wang, Rowan and Bowman, Samuel R. and Price, Sara},
year={2025},
url={https://github.com/safety-research/bloom},
}
