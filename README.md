# kairos

Kairos is now usable as a small personal web app backed by MongoDB, so the same goals, today plan, and focus history are available from any machine.

Current direction: keep the web app as the visual/reference interface, but move active development to a CLI-first workflow so Kairos can track real work while it is being built.

## Install The CLI On Another Machine

Prerequisites:

- Python 3.10 or newer
- Git
- Optional but recommended: a MongoDB URI if you want the same Kairos data on multiple machines

Clone the repo:

```powershell
git clone https://github.com/prashanth-ds-ml/kairos.git
cd kairos
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Kairos as a terminal command:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

Verify the CLI:

```powershell
kairos --version
kairos doctor
kairos paths
```

Start Kairos:

```powershell
kairos
```

If `kairos` is not found after install, run it through Python once and check the script path:

```powershell
python -m kairos.cli --version
python -m site --user-base
```

Then add the Python scripts directory under that user base to your `PATH`. On Windows this is usually similar to:

```powershell
C:\Users\<you>\AppData\Roaming\Python\Python312\Scripts
```

For local-only use, keep the default JSON fallback or explicitly set:

```powershell
kairos config set KAIROS_STORAGE json
```

For cross-machine use, configure MongoDB so every installed CLI points at the same data store:

```powershell
kairos config set KAIROS_STORAGE mongodb
kairos config set KAIROS_MONGODB_URI "<your MongoDB URI>"
kairos config set KAIROS_MONGODB_DATABASE kairos
kairos config set KAIROS_MONGODB_COLLECTION state
```

Kairos stores per-machine config and local fallback data under:

```powershell
C:\Users\<you>\.kairos
```

On macOS or Linux, the equivalent directory is:

```bash
~/.kairos
```

Update an existing install:

```powershell
git pull
python -m pip install -e . --upgrade
```

## Run Locally

Install the CLI once as a user-level command:

```powershell
python -m pip install --user .
```

Kairos keeps independent CLI config and local fallback data under:

```powershell
C:\Users\prash\.kairos
```

After that, `kairos` can run from any directory.

```powershell
kairos
```

`kairos` opens an interactive session. Inside it, run commands like:

```text
kairos> daily
kairos> goal create
kairos> add task
kairos> today plan
kairos> focus
kairos> exit
```

One-shot commands also work:

```powershell
kairos --version
kairos doctor
kairos paths
kairos config list
kairos status
kairos goal create
kairos goal list
kairos goal add-task
kairos today plan
kairos focus start
kairos daily
kairos today
kairos season
```

Use local JSON while developing the web app:

```powershell
$env:KAIROS_STORAGE = "json"
$env:PYTHONPATH = "src"
.\.venv\Scripts\flask.exe --app kairos.web run --debug
```

Use MongoDB locally or remotely:

```powershell
$env:KAIROS_STORAGE = "mongodb"
$env:KAIROS_MONGODB_URI = "mongodb://localhost:27017"
$env:KAIROS_MONGODB_DATABASE = "kairos"
$env:KAIROS_MONGODB_COLLECTION = "state"
$env:PYTHONPATH = "src"
.\.venv\Scripts\flask.exe --app kairos.web run
```

Open `http://127.0.0.1:5000`.

The desktop prototype is still available as:

```powershell
kairos-desktop
```

## Local SearXNG Search Memory

Kairos can use a local SearXNG instance for the `Research` page. Saved results become Kairos search memory; raw result lists are not stored by default.

Start SearXNG with Docker:

```powershell
$env:PATH = "C:\Program Files\Docker\Docker\resources\bin;$env:PATH"
docker compose -f docker-compose.searxng.yml up -d
```

Configure Kairos:

```powershell
KAIROS_SEARXNG_URL=http://127.0.0.1:8080
```

Then restart Kairos and open:

- SearXNG: `http://127.0.0.1:8080`
- Kairos Research: `http://127.0.0.1:5000/research`

Research workflow:

1. Search from Kairos Research.
2. Choose `Read in Kairos` to open a readable preview inside the app.
3. If a site blocks extraction, use `Open original` and keep the save form in Kairos.
4. Save only useful pages with a note and a link to a goal, area, North Star theme, or open question.

Useful checks:

```powershell
Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8080/search?q=kairos&format=json"
docker ps
```

## Deploy On Render

1. Push this repo to GitHub.
2. Create a Render Web Service from the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn --chdir src kairos.web:app`
5. Add environment variables:
   - `KAIROS_STORAGE=mongodb`
   - `KAIROS_MONGODB_URI=<your MongoDB connection string>`
   - `KAIROS_MONGODB_DATABASE=kairos`
   - `KAIROS_SECRET_KEY=<any long random string>`
   - `KAIROS_ACCESS_KEY=<one private key you remember>`

`render.yaml` is included, so Render can also detect the service settings from the repo. Keep the MongoDB URI and access key in Render environment variables, not in git.

When `KAIROS_ACCESS_KEY` is set, the first visit asks for that key and stores it in a browser cookie. There are still no user accounts, usernames, or passwords.

## Daily Loop

1. Open `Today`.
2. Follow the suggested reflection if it is relevant.
3. Confirm the 21-day Season if the app asks for it.
4. Set intention, must-win, and daily pact.
5. Commit to one to three tasks.
6. Start focus from Today or open `Focus` and select the exact target.
7. Complete the block with actual minutes, result, quality, mood, and energy when useful.
8. Open `Review` weekly to compare planned vs actual, inspect friction, and adjust the next plan.

## CLI-First Workflow

The terminal workflow now writes to the same storage as the web app and is the fastest daily operating surface.

Start from any directory:

```powershell
kairos
```

The home screen shows the current 21-day season, a daily discipline progress bar, completed minutes as XP, today's selected commitments, completed goals/tasks, and the next focus target.

Kairos refreshes the configured storage before the command center is drawn. During an interactive session, use `refresh`, `reload`, `sync`, or `home` to reload the latest state without restarting:

```text
kairos> refresh
```

Current daily loop:

```powershell
kairos daily
kairos goal create
kairos goal add-task
kairos goal list
kairos today plan
kairos focus
kairos status
```

`kairos focus` is an interactive alias for `kairos focus start`. It shows available goals/tasks, runs the timer, saves the session result, and marks completed tasks done. `kairos status` shows storage, season, total focus minutes, completed work grouped by priority/goal/task, and the next target.

`kairos daily` shows a small `(⌐■_■) KAIROS` logo and asks three to five questions. Answers are saved as Brain reflections and the daily intention/must-win are written into the daily log.

To open Kairos automatically when Windows starts:

```powershell
kairos setup startup
```

## Life OS Loop

1. Open `Season` to define the current 21-day operating agreement.
2. Pick one primary track, one support track, success criteria, constraints, and paused goals.
3. Use `Apply empty fields` to draft a season from current goals and Brain context.
4. Use `Update Direction` when the season should refresh North Star and area targets.
5. Open `Areas` weekly and score Career, Learning, Health, Money, Relationships, and Personal Systems.
6. Open `Weekly` to set realistic capacity, allocate goals, and handle rollover.
7. Open `North Star` when longer-term direction feels unclear.
8. Create goals under the matching life area so daily work connects back to the life you are building.

## Brain And Research

- `Brain` stores editable self-understanding, confirmed memories, memory candidates, saved research, and the question engine.
- The current question bank has 121 questions: 55 Likert, 44 open, 18 choice, 3 frequency, and 1 ranking.
- `Research` is a source-backed search, read, and save flow. Use it like a lightweight Perplexity-style research session, then save only the insight that should affect planning or memory.
- Brain and Research are memory layers. They should support Today, Season, Weekly, Review, and Coach without becoming a generic note dump.

## Product Docs

- `docs/README.md` is the documentation map.
- `docs/psychological_product_blueprint.md` is the behavior-first product blueprint.
- `vault/` is the Obsidian workspace for decisions, workboard, and linked planning notes.

## UI Tests

Install browser test tooling:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Run the app, then:

```powershell
$env:KAIROS_BASE_URL = "http://127.0.0.1:5000"
.\.venv\Scripts\python.exe tests\playwright_smoke.py
```

## Storage

Production and cross-machine personal use should use MongoDB because hosted filesystems are usually temporary and local JSON does not follow the user across machines. The app has a JSON fallback for local use, but real ongoing data should live in MongoDB.

The MongoDB adapter uses one collection as a document bucket. Inside that collection, Kairos stores documents such as `_id=goals`, `_id=sessions`, `_id=current_season`, `_id=brain_memories`, and `_id=research_sessions`. A collection name like `state` or `kairos_state` is clearest, but any configured collection works.

Do not commit `.env`. If a MongoDB password is ever pasted into chat or logs, rotate it in MongoDB Atlas.
