# Semantic Course Search

Full-stack semantic search experience for university course catalogs. The
Flask API serves a Svelte single-page application that queries pgvector-backed
embeddings to surface relevant courses by meaning instead of keywords.

## Tech Stack
- **Backend:** Flask, PostgreSQL (pgvector), psycopg2 connection pooling
- **Frontend:** Svelte 4 + Vite
- **Embeddings:** Hugging Face `thenlper/gte-base` via PyTorch
- **Tooling:** [uv](https://github.com/astral-sh/uv) for Python dependency and
  virtualenv management

## Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) ≥ 0.4
- Node.js 18+
- PostgreSQL (with the `pgvector` extension) accessible to the app
- Course CSVs in `coursedata/<school>/<SCHOOL>_courses.csv`

## Schema Overview
The data pipeline now uses shared tables instead of one table per school:

- `courses`: canonical course metadata for every school (column `school` marks
the institution).
- `course_embeddings`: pgvector embeddings keyed by `course_id` with a strict
  one-to-one relationship to `courses`.

Running the loader scripts replaces the rows for the targeted school and keeps
other institutions untouched, making it easy to rebuild selectively or search
across all schools.

## Configuration
Back-end credentials can be supplied via the standard `DATABASE_URL`
environment variable or by editing `config.ini` (placeholders included). In
production, prefer environment variables to keep secrets out of source control.

Optional settings:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_MIN_CONNECTIONS` | Minimum pooled connections | `1` |
| `DATABASE_MAX_CONNECTIONS` | Maximum pooled connections | `5` |
| `PORT` | Flask server port | `8000` |
| `VITE_API_BASE_URL` | Front-end API base URL (set during deployments) | `` |

## Local Development

1. **Install Python dependencies** (creates `.venv` automatically):
   ```bash
   uv sync
   ```

2. **Install front-end dependencies**:
   ```bash
   cd client
   npm install
   ```

3. **Populate PostgreSQL (first-time only)**. Pick one of the flows below:
   - Bootstrap multiple schools in one go (creates/updates shared tables):
     ```bash
     uv run python make_dbs.py ASU UIUC --yes
     ```
   - Or run the scripts individually:
     ```bash
     uv run python create_courses_table.py --school ASU --yes
     uv run python courses_to_embeddings.py --school ASU --yes
     ```
   The scripts read from `coursedata/` by default. Use `--csv-path` if you
   provide your own source files.

4. **Run the Flask API**:
   ```bash
   uv run python app.py
   ```

5. **Run the Svelte dev server**:
   ```bash
   cd client
   npm run dev -- --open
   ```

During development, the Vite proxy forwards `/search` requests to the Flask
server when both are running locally.

## Building the Front-End
```bash
cd client
npm run build
```
The generated assets in `client/dist` are served directly by Flask in
production deployments.

## Database Maintenance
- Rebuild a single catalog/table: `uv run python create_courses_table.py --school UNC --yes`
- Regenerate embeddings only: `uv run python courses_to_embeddings.py --school UNC --yes`
- Regenerate all at once: `uv run python make_dbs.py ASU UIUC UNC --yes`

Each command only touches rows for the schools you specify while leaving others
intact. The embeddings script enforces a single embedding per course via a
unique index.

## Deployment
See `DEPLOYMENT.md` for a detailed guide covering both VPS-based and Railway
deployments, including database bootstrap steps.

For a quick start on a fresh Ubuntu or Oracle Linux host you can run the helper script after
cloning the repository:

```bash
sudo -E DATABASE_URL="postgresql://user:pass@host:5432/db" \
  APP_DOMAIN="courses.example.com" \
  COURSE_SCHOOLS="ASU UIUC" \
  bash scripts/bootstrap.sh
```

The script installs prerequisites, runs `uv sync`, builds the frontend, loads
course data via `make_dbs.py`, and provisions systemd/nginx units. Review
`scripts/bootstrap.sh` before executing and adjust variables to match your
environment.
