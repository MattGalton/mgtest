# mgtest

Write down what your system should do.  Run it with pytest.

`mgtest` is for the useful bit after unit tests: start a service, fetch an input,
call an endpoint, inspect a file, or run a command.

Each YAML test becomes a normal pytest test.

![How an mgtest run works](docs/diagrams/run-flow.svg)

## Architecture at a glance

The diagrams below show the same flow at increasing detail. Blue is how a run enters
mgtest, green is planning, purple is the extension boundary, orange is execution, and
pink is persisted run evidence.

| View | What it shows |
| --- | --- |
| [System context](docs/diagrams/01-system-context.puml) | The project, pytest and CLI entry points, mgtest, the system under test, and run artifacts. |
| [Execution components](docs/diagrams/02-execution-components.puml) | The modules that load a project, register types, compile the dependency graph, execute checks, and retain evidence. |
| [Run sequence](docs/diagrams/03-run-sequence.puml) | A whole run: discovery, compilation, execution, teardown, and reporting. |
| [Check sequence](docs/diagrams/04-check-sequence.puml) | One check and its dependencies: resource setup, test execution, output capture, and cleanup. |

Open the `.puml` files in a PlantUML-capable editor or render them in documentation
automation. They are deliberately high-level: the built-in types and project plugins
share the same spec and instance extension boundary.

## Install mgtest

Install the core framework, then add only the integrations a project uses:

```sh
uv add mgtest-core
uv add mgtest-docker mgtest-redis  # add Docker and Redis support
mkdir -p demo/mgtest
```

`mgtest-core` includes the CLI, pytest plugin, schema generator, and built-ins that
only use the Python standard library or core dependencies. Optional integrations are
separate Python packages, so their client libraries are not installed unless needed:

| Package | Definitions it adds |
| --- | --- |
| `mgtest-docker` | `DockerContainer`, `DockerCompose` |
| `mgtest-redis` | `Redis`, `RedisQuery` |
| `mgtest-sql` | `Postgres`, `SqlQuery` |
| `mgtest-s3` | `S3Bucket`, `S3Object`, `S3ObjectExists`, `S3ObjectMatches` |
| `mgtest-nats` | `NatsServer`, `NatsSubscribe` |
| `mgtest-lsp` | Editor diagnostics, completion, hover, and navigation for mgtest YAML |
| `mgtest-lsp-jetbrains` | JetBrains IDE wrapper that starts `mgtest-lsp` for mgtest YAML |

For convenience, `uv add "mgtest-core[services]"` installs Docker, Redis, and SQL;
`uv add "mgtest-core[all]"` installs every published integration. The workspace root
lists the available packages in `[tool.mgtest.packages]`.

`mgtest-schema` remains part of `mgtest-core`. It loads installed integration entry
points, so regenerate schemas after adding or removing an integration:

```sh
uv run mgtest-schema --vscode .vscode --jetbrains .idea
```

### Editor language server

Install `mgtest-lsp` alongside the integrations used by the project, then configure
your editor to run `mgtest-lsp` over standard input/output. It is a
`python-lsp-server` plugin, so `pylsp` is also a valid server command when both
packages are installed.

```sh
uv add "mgtest-core[lsp]" mgtest-redis
uv run mgtest-lsp
uv run mgtest lsp
```

Run the same analyser directly when debugging editor diagnostics or in CI:

```sh
uv run mgtest analyse --root demo/mgtest demo/mgtest/t_health.yaml
uv run mgtest analyse --json --root demo/mgtest demo/mgtest/t_health.yaml
```

`mgtest analyse` is provided by `mgtest-core`; it does not require the language-server
package. `mgtest-analyse` remains available when `mgtest-lsp` is installed.

### JetBrains plugin

The Kotlin wrapper in [src/mgtest-lsp-jetbrains](src/mgtest-lsp-jetbrains) starts the
same Python server from JetBrains IDEs. It defaults to `uv run --directory <project>
mgtest-lsp`, so the server shares the project's integrations. Build a local installable
ZIP with `cd src/mgtest-lsp-jetbrains && ./gradlew buildPlugin`, then install it with
**Settings | Plugins | gear menu | Install Plugin from Disk…**. The project also owns
its Marketplace publishing and signing configuration; see its README for `publishPlugin`.

The language server loads the same built-ins and Python entry-point integrations as
`mgtest run`. It uses the core Pydantic models and generated authored schemas for
field validation, then adds YAML parse diagnostics, installed-type completion, field
completion, and hover text. Keep `mgtest-schema` configured as a fallback for YAML
editors that do not start an LSP server.

### Extension API

Definitions in an integration package should import `ResourceSpec`, `TestSpec`,
their instances, `ResourceScope`, and `retry` from `mgtest.api`. This is the stable
extension boundary; compiler, runner, and built-in modules remain core internals.
The package contract and stability policy are recorded in
[ADR 0001](docs/architecture/0001-public-extension-sdk.md).

`ExecutionSession` owns setup, execution, scopes, teardown, outcomes, and lifecycle
events. The CLI and pytest adapter only present those facts. See
[ADR 0002](docs/architecture/0002-execution-and-retention.md) and the
[architecture improvement plan](docs/architecture-improvement-plan.md).

## Start with one test

```yaml
# demo/mgtest/t_python.yaml

type: Command
name: python_is_here
shell_command: python3 --version
stdout_contains: Python
```

Then run it:

```sh
pytest demo/mgtest -v
# Show mgtest resource and check lifecycle events as they happen:
pytest demo/mgtest -v -o log_cli=true --log-cli-level=INFO
# or
mgtest run demo/mgtest
```

mgtest uses Python's standard `logging` module. Project loading, planning, and check
execution are emitted at `INFO`; concrete operations and identities use `DEBUG`; reuse,
collection, and teardown use `TRACE`. Pytest captures these records normally and shows
them with its usual failure reports. Set `MGT_LOG_LEVEL=DEBUG` or `MGT_LOG_LEVEL=TRACE`
to enable those records. For live pytest output, also pass `-o log_cli=true
--log-cli-level=DEBUG` (or the equivalent `INFO` level; use `--log-cli-level=5` for TRACE).

### Expected outcomes

Checks pass by default. Set `expected_outcome: failed` for a known failure. Pytest
reports a matching failure as passed, with `mgtest.actual_outcome=failed` and
`mgtest.expectation=matched` report properties. A successful check with that
expectation is a failure with a "passed unexpectedly" message.
`mgtest run` likewise accepts the expected failure and fails the run for an unexpected
pass. This is a property of the check definition; mgtest does not currently support
environment-specific expectation overrides. Baseline comparisons remain ordinary test
types, so they can compare an artifact against a checked-in file and produce a useful
diff.

```yaml
type: Command
name: known_bug
shell_command: ./reproduce-known-bug
expected_outcome: failed
```

### `Command`

`Command` is a one-shot check: run a shell command or Python source, capture its
output, and expect exit code zero. Specify exactly one execution field:

```yaml
shell_command: "curl --fail http://localhost:8080/health"
# or
python_command: "import sys; print(sys.version)"
```

### YAML specialisations

A project can create a named, partially configured version of any installed
resource or check type.  Put the YAML file under `builtin/resources` or
`builtin/tests`; its filename becomes the new type name, `specialises` selects
the parent type, and its other fields are defaults that a definition can
override.

```yaml
# builtin/tests/Echo.yml
specialises: Command
python_command: "print('Hello world')"
stdout_contains: Hello world
```

```yaml
# s_echo/t_echo.yaml
type: Echo
name: hello_world_check
```

`Command` is a check type, so `Echo.yml` belongs in `builtin/tests`. A
specialisation of `Executable`, `S3Bucket`, or another resource type belongs
in `builtin/resources` instead. Specialisations can themselves be specialised;
the loader resolves them by parent type and reports unknown or cyclic parents.

## Then your service needs to stay up

`Executable` is a resource. It starts once and stays alive while tests use it.

`StreamRegex` watches its output.

```yaml
# r_api.yaml
type: Executable
name: api
path: python3
args: [-u, -m, my_service]
auto_start: true
```

```yaml
# t_api_ready.yaml
type: StreamRegex
name: api_ready
resource: "${mgtest:resources.api}"
pattern: "Listening on"
timeout: 10
```

That resource reference tells mgtest that `api` must start first.

### Choose a resource lifetime

Resources use `Suite` scope by default: mgtest starts one instance and stops it when
the containing suite finishes. Use `File` scope to share an instance within one
`t_*.yaml` file and reset it for the next file. Use `Test` scope when every check
needs a clean instance. mgtest tears those down after each check, including a failed
check, and starts a new instance for the next one.

```yaml
type: TemporaryDirectory
name: scratch
scope: File
auto_start: true
```

### Inspect a check's resources

`mgtest get` collects the resource closure for one check without running that check.
By default it calls each resource's optional `prepare()` hook, which is useful for
durable inputs such as checkouts and downloaded media. It writes a manifest, resource
logs, and an `environment.json` file under `.mgtest/gets/`.

```sh
# From inside the project:
mgtest get s_smoke/video_check

# Or name the project explicitly:
mgtest get ./mgtest s_smoke/video_check --prepare

# Start services, expose scalar resource outputs as MGTEST_RESOURCE_* variables,
# and clean them up once the command exits:
mgtest get ./mgtest s_smoke/video_check --command 'open "$MGTEST_GET_DIR"'
mgtest get ./mgtest s_smoke/video_check --shell
```

If the selected check needs output from an earlier check, `get` explains the
dependency. Pass `--with-prerequisites` only when you want to run those prerequisite
checks to produce their outputs.

## Keep the project boring

An mgtest project is simply a directory named `mgtest`. Files are found recursively.

```text
mgtest/
  vars.yaml
  r_database.yaml
  s_smoke/
    vars.yaml
    t_health.yaml
  builtin/
    resources/
    tests/
```

- `r_*.yaml` files define resources.
- `t_*.yaml` files define tests.
- `s_*` folders are suites. Child suites inherit `vars.yaml` values and can override them.
- `s_*.yaml` files are suite manifests that group existing checks without redefining them:

  ```yaml
  # s_smoke.yaml
  tests:
    - s_api/health
    - s_worker/processes_job
  ```
- `builtin/` holds project-local Python plugins.

Use variables for boring configuration:

```yaml
# mgtest/vars.yaml

host: "${oc.env:MGTEST_HOST,127.0.0.1}"
port: 8080
```

```yaml
# mgtest/smoke/t_health.yaml

type: HttpRequest
name: health
url: "http://${vars.host}:${vars.port}/health"
expected_status: 200
json_equals: {status: ready}
```

When one check produces a value for another, reference its output:

```yaml
actual: "${mgtest:resources.repository.outputs.revision}"
```

Use `depends_on` only when something must happen first but no
value is passed:

```yaml
depends_on: ["resources.database", "tests.seed_data"]
```

### Chain checks deliberately

A `t_*.yaml` file can contain a `tests` sequence. mgtest adds a dependency from each
item to the preceding item, so a failed check skips the remainder of that file under
pytest. This is useful for a readable progression from process readiness, to output
creation, to content validation.

```yaml
# t_export.yaml
tests:
  - type: StreamRegex
    name: export_started
    resource: "${mgtest:resources.exporter}"
    pattern: "export complete"
  - type: FileExists
    name: export_was_written
    path: "${vars.export_path}"
  - type: FileMatches
    name: export_is_valid
    path: "${vars.export_path}"
    contains: "expected record"
```

To chain separate files in the same suite, give the first check a name and declare it
as a normal test dependency. The compiler orders it before the dependent file; pytest
skips the dependent check if its prerequisite failed.

```yaml
# t_validate.yaml
type: FileMatches
name: export_is_valid
depends_on: ["tests.export_was_written"]
path: "${vars.export_path}"
contains: "expected record"
```

## Pick a built-in

| Need                            | Use |
|---------------------------------| --- |
| Run a one-shot command          | `Command` |
| Keep a local process running    | `Executable` + `StreamRegex` |
| Wait for an HTTP or TCP service | `HttpRequest` or `TcpConnect` |
| Check a file                    | `FileExists` or `FileMatches` |
| Compare generated file data     | `FileBaseline`, `JsonBaseline`, or `DirectoryBaseline` |
| Run a container or stack        | `DockerContainer` or `DockerCompose` (`mgtest-docker`) |
| Checkout a respository          | `GitRepository` |
| Provision an S3 bucket          | `S3Bucket` (`mgtest-s3`) |
| Upload an ephemeral S3 object   | `S3Object` (`mgtest-s3`) |
| Create a disposable directory   | `TemporaryDirectory` |
| Run a PostgreSQL container      | `Postgres` (`mgtest-sql`) |
| Run a Redis container           | `Redis` (`mgtest-redis`) |
| Query and assert Redis data     | `RedisQuery` (`mgtest-redis`) |
| Query PostgreSQL                | `SqlQuery` (`mgtest-sql`) |
| Run a local NATS server         | `NatsServer` (`mgtest-nats`) |
| Wait for a NATS message         | `NatsSubscribe` (`mgtest-nats`) |
| Validate JSON against a schema  | `JsonSchema` |
| Check S3 object presence/content| `S3ObjectExists` or `S3ObjectMatches` |
| Inspect ZIP or tar contents     | `ArchiveContains` |
| Verify a local port is free     | `PortAvailable` |

### Baselines and asynchronous output

Baseline checks are ordinary tests. `FileBaseline` compares bytes, `JsonBaseline`
compares parsed JSON values, and `DirectoryBaseline` compares every directory,
file, and symlink below a tree. Their `baseline` path is relative to the `t_*.yaml`
document, which keeps checked-in expected data beside the check that owns it.

`FileExists`, `FileMatches`, and `ArchiveContains` accept an optional `timeout` and
`interval`. With a timeout they poll until the condition passes, making them suitable
prerequisites for a later baseline comparison. Baseline checks are immediate, so the
test sequence makes readiness explicit.

```yaml
tests:
  - type: FileExists
    name: export_finished
    path: "${vars.output_directory}/.finished"
    timeout: 10
  - type: FileBaseline
    name: export_matches_baseline
    path: "${vars.output_directory}/export.txt"
    baseline: baselines/export.txt
```

### `NatsServer` and `NatsSubscribe`

`NatsServer` starts a local `nats-server` executable and waits for its client port.
Install the NATS server binary separately, then use its `url` output in a subscription
check. `NatsSubscribe` waits for one message until its timeout expires and can assert
the decoded UTF-8 payload.

```yaml
# r_nats.yaml
type: NatsServer
name: nats
auto_start: true

# t_event.yaml
type: NatsSubscribe
name: received_event
url: "${mgtest:resources.nats.outputs.url}"
subject: exports.completed
payload: '{"status":"ok"}'
timeout: 10
```

### `S3Bucket`

`S3Bucket` creates a bucket when it does not exist and exposes `bucket`, `uri`,
`region`, and `endpoint_url` as outputs. It deletes only a bucket it created; set
`delete_on_teardown: false` to retain that bucket after the run. boto3 uses its
standard AWS credential chain, and `endpoint_url` makes the same definition work
with a local S3-compatible service such as LocalStack.

```yaml
# boto3 authentication comes from the environment or its normal credential chain:
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_SESSION_TOKEN=...  # required only for temporary credentials
type: S3Bucket
name: uploads
bucket: my-unique-test-bucket
region: eu-west-2
# endpoint_url: http://localhost:4566  # for LocalStack or another S3-compatible service
# LocalStack commonly accepts: AWS_ACCESS_KEY_ID=test, AWS_SECRET_ACCESS_KEY=test
```

## When CI fails, keep the evidence

Every run gets a directory under `.mgtest/runs/<run-id>/`:

```text
manifest.json
resolved-config.yaml
tests/.../outputs.json
tests/.../failure.txt
resources/.../logs.txt
```

Cache configuration and run retention live in `.mgtest/config.yaml`:

```yaml
cache:
  max_size_mb: 1024
runs:
  max_count: 50
  max_age_days: 30
```

Use `.mgtest/cache/` as the CI cache path. Upload `.mgtest/runs/` when a job fails.

```sh
mgtest home                 # cache and run summary
mgtest home --runs          # what happened recently
mgtest home --show-run ID   # inspect one run
mgtest home --cache         # cache size and hit rate
mgtest home --doctor        # Git, Docker, Compose, ffmpeg
mgtest home --prune
```

## Add one thing of your own

Drop a Python file into `mgtest/builtin/resources` or `mgtest/builtin/tests`.

```python
# mgtest/buildin/tests/is_even.py

from mgtest.engine.api.test.instance import TestInstance
from mgtest.engine.api.test.spec import TestSpec


class IsEvenInstance(TestInstance):
    def run(self, resources):
        assert self.definition.value % 2 == 0


class IsEven(TestSpec):
    value: int

    def create_instance(self):
        return IsEvenInstance(self)
```

```yaml
# is_even.yaml

type: IsEven
name: answer
value: 42
```

Define a nested `Output` Pydantic model only when another YAML file needs typed,
reusable results.

For a stable YAML name that differs from the class name, set `TYPE = "stable-name"`.

## Commands worth knowing

```sh
mgtest init ./mgtest
mgtest run ./mgtest
mgtest run ./mgtest s_smoke/s_api
mgtest run ./mgtest s_smoke/s_api/health
mgtest list ./mgtest
mgtest home --clear-cache
mgtest home --clear-runs
mgtest-schema --help
```

An optional `mgtest run` selector is a suite path or a check name. A suite includes its
descendants; use `suite/path/check` when a check name appears in more than one suite.
`mgtest list` prints the suite and check tree. mgtest still validates the full project,
but starts resources only for the selected checks and their runtime dependencies.

Python 3.12+ is required. In this repository, run `uv sync --all-packages` to install
every workspace package, then `uv run pytest`.

The workspace root collects each package's `tests/` directory. The only top-level tests
are the opt-in real integration checks below; running pytest from an individual package
uses that package's own `pyproject.toml` test path.

### Real integration lane

The normal test matrix keeps its mocked integration tests fast. The manually triggered
`Real integration` GitHub Actions workflow starts MinIO, then runs
`tests/real_integration` against real Docker, Redis, PostgreSQL, and S3-compatible
services. It is intentionally separate from pull-request CI because it pulls images
and creates containers. To run the same checks locally, start an S3-compatible service
and set `MGT_REAL_S3_ENDPOINT`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` before
running `uv run pytest tests/real_integration`.
