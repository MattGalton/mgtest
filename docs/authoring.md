# Write checks

An mgtest project is a directory called `mgtest`. Files are loaded recursively.

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

- `r_*.yaml` defines a resource: something started or provisioned for checks.
- `t_*.yaml` defines one check or an ordered sequence of checks.
- `s_*` directories are suites. Their `vars.yaml` values are inherited by child suites.
- `builtin/` holds project-local Python extensions.

## Start a service, then check it

Resources express the things your checks need. This executable starts once for the
suite by default, and the check waits for its readiness message.

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

The resource reference is also a dependency: mgtest starts `api` before it runs
`api_ready`.

## Use configuration and outputs

Use `vars.yaml` for ordinary project configuration. Environment fallbacks keep local
development and CI settings in the same definition.

```yaml
# vars.yaml
host: "${oc.env:MGTEST_HOST,127.0.0.1}"
port: 8080
```

```yaml
type: HttpRequest
name: health
url: "http://${vars.host}:${vars.port}/health"
expected_status: 200
json_equals: {status: ready}
```

When a resource or check exposes a typed output, another definition can use it:

```yaml
actual: "${mgtest:resources.repository.outputs.revision}"
```

Use `depends_on` when ordering is needed but no value flows between definitions:

```yaml
depends_on: ["resources.database", "tests.seed_data"]
```

## Choose the right resource lifetime

`scope` controls how frequently a resource is created.

| Scope | Lifetime |
| --- | --- |
| `Suite` | One instance for the suite; this is the default. |
| `File` | One instance for each `t_*.yaml` file. |
| `Test` | A new instance for every check. |

```yaml
type: TemporaryDirectory
name: scratch
scope: File
auto_start: true
```

mgtest tears resources down after their scope finishes, including after a failure.

## Put a readable progression in one file

A `tests` sequence makes every item depend on the one before it. This makes a
readiness-to-result flow easy to read and means later checks are skipped when an
earlier prerequisite fails.

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

See [integrations](integrations.md) for the available types and [run evidence](running.md)
for diagnosing a failure.
