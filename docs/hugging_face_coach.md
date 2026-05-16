# Hugging Face Coach Setup

Review date: 2026-05-16

Kairos has a Coach tab that can use Hugging Face Inference Providers.

## Environment Variables

Set one token variable before starting Kairos. `HF_TOKEN` is preferred; `HUGGINGFACE_API_TOKEN` and `HUGGINGFACE_HUB_TOKEN` are also supported.

```powershell
$env:HF_TOKEN = "hf_your_token"
```

Optional model override:

```powershell
$env:HF_MODEL = "Qwen/Qwen3-8B"
```

Then run Kairos normally.

Current default model in Kairos:

- controlled by `HF_MODEL`; the app currently falls back to local guidance if the configured model or token is unavailable

For local development, you can also create a `.env` file in the project root. `.env` is ignored by git.

```text
HF_TOKEN=hf_your_new_token_here
HF_MODEL=Qwen/Qwen3-8B
```

Kairos loads `.env` on startup without overriding real environment variables. For deployment, put `HF_TOKEN` in the hosting provider's environment variable settings instead of committing it. Local `.env` keys are normalized, so an existing `HF_Token` entry will also be read as `HF_TOKEN`.

## Token Permission

Create a Hugging Face fine-grained token with permission to make calls to Inference Providers.

If a token was pasted into chat, logs, screenshots, or any public place, revoke it and create a new one before using it.

If Kairos says Hugging Face rejected the request, the app reached Hugging Face but the token was not allowed to use Inference Providers. Open-weight models still require this token permission. In that case, Kairos returns a local deterministic coach answer instead of blocking the user.

The Coach header shows the active model and whether Inference Providers is enabled. It does not expose the token value.

## What The Coach Can See

The Coach receives only a compact Kairos summary:

- Active goals and open tasks.
- Life area scores and targets.
- Today time blocks.
- Recent daily logs.
- Weekly focus minutes.
- Weekly trigger and pact counts.

It should not receive unrelated files or external memory.

## Product Rule

The Coach suggests. You decide.

Use it for:

- Planning the day.
- Finding neglected life areas.
- Reviewing trigger patterns.
- Turning goals into time blocks.
- Creating a pact for the week.

## 2026-05-14 Product Direction

Coach should not only live as a separate tab. It should become contextual help at decision points.

Recommended embedded prompts:

| Page | Coach prompt |
| --- | --- |
| Today | Help me choose the next block. |
| Focus | Help me unblock this task. |
| Weekly | Suggest a realistic weekly plan. |
| Review | Explain what this week is telling me. |
| Goals | Break this goal into next actions. |
| Areas | Which area needs attention and why? |

Coach responses must remain concise, practical, and grounded only in Kairos data. The user should never feel that the model is judging them.

Current product context:

- Today keeps the time-block composer collapsed by default.
- Goals keeps the create-goal form collapsed by default.
- Weekly supports capacity planning, goal allocation, and rollover.
- Review includes weekly charts for focus, area balance, goal progress, outcome mix, triggers, and focus consistency.
- Coach can also fall back to a local guidance summary built from Kairos data when Hugging Face is not available.

Related docs:

- `docs/README.md`
- `docs/psychological_product_blueprint.md`
- `docs/product_discipline_audit.md`
