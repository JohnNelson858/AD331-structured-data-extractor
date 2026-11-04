# Step 6: local container deployment

John Nelson · AD 331 · local Docker demo alternative

## Status and verification boundary

The Dockerfile, Compose configuration, persistence verifier and optional secret
configuration are implemented. **Actual Docker build and runtime are pending on
the Dell.** Docker is not installed in the assistant workspace, so no image
build, health status or persistence result is fabricated.

Assistant checks: **118 passed in 10.83s**, including seven new application
configuration cases; Python compilation, uv lock check and Git whitespace check
passed. Compose YAML was parsed and its expected port, offline defaults, volume
and secret references were inspected. This is not Docker Compose validation.
Full pytest output is in step6_test_results.txt. No provider API call was made.

John reported the preceding Windows guard correction verified: **111 passed in
12.80s** on the Dell. Step 5 is now verified there; this update adds seven cases.

## 1. Start Docker Desktop and stop the native app

Open Docker Desktop and wait for the engine to be running. Use Linux containers
with the installed WSL 2 backend. In the PowerShell window currently running the
native app, press Ctrl+C. Both the native and container app use local port 8001;
only one should own that port at a time.

From the existing project folder:

```powershell
git pull --ff-only
docker info --format '{{.OSType}}'
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 120
docker compose ps
```

Expected OS: linux. config --quiet prints nothing on success. The first build
pulls Python/uv images and locked dependencies, so it needs internet access and
may take a few minutes. These downloads do not spend OpenAI API credits.

Expected service: extractor, status Up/healthy, port
127.0.0.1:8001->8000/tcp. Dockerfile health probes use only the local /health
route and make no billable extraction requests. The wait timeout concerns
container readiness; image download/build can take longer.

If startup fails, inspect:

```powershell
docker compose logs --tail 60 extractor
```

If Docker is unavailable, start Docker Desktop. If port 8001 is in use, stop the
native app or previous instance and retry the Compose up command. Do not rebuild
or reinstall unrelated tools just to address a port conflict.

## 2. Verify the actual container UI

Open http://127.0.0.1:8001 and refresh. The UI looks the same because the same
application now runs inside the container. Confirm container status in PowerShell
so the video can establish which deployment is serving the page.

Leave Offline sample demo selected. Load sample, then Run extraction. Expected:
Accepted, 1 attempt, reconciliation passes. Repeat the reflection and deliberate
DLQ controls if desired. The default Compose service explicitly sets empty key
and key-file values and does not mount the host .env; the app begins offline.

## 3. Verify all routes and persistent DLQ storage

With the container healthy, run on the Dell:

```powershell
uv run python scripts/verify_docker.py --check-persistence
```

This script talks to local loopback HTTP only and explicitly requests offline
fixtures. It checks:

1. Uploaded PDF: SUCCESS / 1 attempt.
2. Uploaded HTML: SUCCESS / 1 attempt.
3. Incorrect total: reflection repair / 2 attempts.
4. Reflection disabled: DLQ / 1 attempt.
5. Fenced JSON: heuristic repair / 1 attempt.
6. Hard failure: DLQ / 4 attempts.
7. The generated DLQ record exists inside the container with correct metadata.
8. The extractor container is recreated using the default Compose file, then
   returns healthy with a different container ID and the same DLQ record hash.

It does not rebuild the image. Container recreation briefly interrupts the page;
refresh after completion. The helper explicitly selects this repository's
Compose file, so COMPOSE_FILE from another project does not redirect the check.
The script requires the default offline configuration; do not combine it with
the optional live override.

Expected final line: **PASS. Saved verification report:
runtime/docker_verification.json**. Its JSON report includes
`dlq_after_recreation: PASS: new container, identical saved record bytes`.
The report is local/ignored and contains no provider credentials or source text.
Send the final report/summary for verification. A failed or skipped check is not
proof of completed deployment; inspect the named failure before recording.

Container DLQ records live in the Docker-managed named volume extractor_dlq,
mounted at /app/runtime/dlq. They are separate from the host's runtime/dlq
records created during earlier native runs. Compose prefixes the volume name
with this project's name. On first use Docker initializes it from the image's
non-root-owned mount directory; actual write permission is verified by the
hard-failure check. The helper reads a specified UUID record without exposing
raw document content.

## 4. Re-run the updated unit/integration suite

```powershell
uv run pytest -v --maxfail=1
```

Expected: 118 passed. These run on the Dell's Python environment; they are
separate from the actual container verifier. Production images intentionally
omit pytest/dev dependencies. The new seven cases check environment-selected
DLQ routing, explicit-path precedence, BOM-compatible secret files, safe errors
for missing/empty/invalid files and explicit offline configuration.

## 5. Stop and resume safely

```powershell
docker compose down
```

This stops/removes the service and network while keeping the named DLQ volume.
To resume:

```powershell
docker compose up -d --wait
```

Do not add --volumes/-v to down when retaining DLQ records; that option deletes
the saved volume. Ctrl+C closes a foreground logs view; use compose down to stop
the detached service. Docker Desktop can be quit after the container is stopped.

## Optional later live API configuration

This is not needed for the offline build or verification above. For real model
extraction, an opt-in second Compose file mounts an ignored local key file as
/run/secrets/openai_api_key. The key is read on startup and never baked into the
image or returned in the browser configuration. A nonempty key-file setting takes
precedence over the environment key. Invalid/empty files fail startup with a safe
message. Windows UTF-8 BOM and trailing newline are supported.

When ready for a separately billed live check, create .secrets/openai_api_key.txt
locally using Notepad and enter only your OpenAI API key. Do not paste the key
into chat, Git, a terminal command, screenshot or video. .secrets is ignored by
Git and the Docker build allowlist. Use only your synthetic documents for the
class demonstration.

```powershell
New-Item -ItemType Directory -Force .secrets
notepad .secrets\openai_api_key.txt
```

After saving the key file, opt in explicitly:

```powershell
docker compose -f docker-compose.yml -f docker-compose.live.yml up -d --wait
```

The app still opens in Offline mode. Choose Live OpenAI and check the API-charge
acknowledgement before a real extraction. Up to four provider calls may be used
per run. Actual live provider extraction remains unverified until that separate
check succeeds; API billing is separate from ChatGPT Plus.

Return to the default offline deployment by running the base configuration:

```powershell
docker compose up -d --force-recreate --wait
```

## Implementation notes and references

- Multi-stage build uses official Python 3.11 slim-bookworm and uv 0.13.4,
  syncing uv.lock with --locked --no-dev --no-install-project.
- The base image supplies its Python 3.11 patch version; explicit --python
  /usr/local/bin/python overrides the host patch pin while satisfying project
  requirements. Package versions are locked. Base-image tags are not digest pins.
- Only runtime code, synthetic samples, venv and inspection/health helpers enter
  the final image. The allowlisted build context excludes .env, .secrets, .git,
  host .venv and generated runtime records. No COPY . . or credential build args.
- Non-root uid/gid 10001, read-only root filesystem, writable named DLQ volume
  and bounded /tmp tmpfs; capabilities dropped; local loopback port binding.
- The server listens on 0.0.0.0 inside the isolated container so Docker can forward
  traffic. Only 127.0.0.1:8001 is published on the Dell. Public/cloud deployment
  and authentication are outside this local alternative.
- The application now honors DLQ_DIR. Previously the example listed that variable
  but the app always used its default path. Explicit Python arguments retain
  precedence for tests and other callers.

Primary references:
- https://docs.astral.sh/uv/guides/integration/docker/
- https://docs.docker.com/compose/how-tos/use-secrets/
- https://docs.docker.com/engine/storage/volumes/
- https://docs.docker.com/reference/cli/docker/compose/up/

After actual Dell runtime/persistence evidence, finalize the rubric checklist,
verify live extraction separately, complete the student's schema/audit review,
and prepare the timed 5-7 minute video narration and submission links. This
Docker preparation alone does not mark the whole assignment complete.
