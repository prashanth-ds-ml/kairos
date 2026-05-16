# kairos

Kairos is now usable as a small personal web app backed by MongoDB, so the same goals, today plan, and focus history are available from any machine.

## Run Locally

Use local JSON while developing:

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
$env:PYTHONPATH = "src"
.\.venv\Scripts\flask.exe --app kairos.web run
```

Open `http://127.0.0.1:5000`.

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
2. Follow the Now action.
3. Set intention, must-win, and daily pact.
4. Commit to one to three tasks.
5. Start focus from Today or open `Focus` and select the exact target.
6. Complete the block with actual minutes, result, quality, mood, and energy when useful.
7. Open `Review` weekly to compare planned vs actual, inspect friction, and adjust the next plan.

## Life OS Loop

1. Open `North Star` when direction feels unclear.
2. Define the 1-year vision, 90-day outcomes, current season focus, and top 3 priorities.
3. Open `Areas` weekly and score Career, Learning, Health, Money, Relationships, and Personal Systems.
4. Set weekly minute targets for areas that need deliberate investment.
5. Open `Weekly` to set realistic capacity, allocate goals, and handle rollover.
6. Create goals under the matching life area so daily work connects back to the life you are building.

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

Production should use MongoDB because hosted filesystems are usually temporary. The app has a JSON fallback for local use, but deployed data should live in MongoDB.
