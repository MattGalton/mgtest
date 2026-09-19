# Integrations and built-ins

Install the core framework first, then add only the packages your project uses.

```sh
uv add mgtest-core
uv add mgtest-docker mgtest-redis
```

`mgtest-core[services]` installs Docker, Redis, and SQL support. `mgtest-core[all]`
installs every published integration.

| Package | Definitions and capability |
| --- | --- |
| `mgtest-core` | Commands, HTTP, TCP, files, JSON, archives, baselines, Git, executable processes, temporary directories, and schema generation. |
| `mgtest-docker` | `DockerContainer`, `DockerCompose` |
| `mgtest-redis` | `Redis`, `RedisQuery` |
| `mgtest-sql` | `Postgres`, `SqlQuery` |
| `mgtest-s3` | `S3Bucket`, `S3Object`, `S3ObjectExists`, `S3ObjectMatches` |
| `mgtest-nats` | `NatsServer`, `NatsSubscribe` |
| `mgtest-lsp` | Diagnostics, completion, hover, and navigation for mgtest YAML |

## Editor support

Generate schemas after changing installed integrations:

```sh
uv run mgtest-schema --vscode .vscode --jetbrains .idea
```

For language-server support, install `mgtest-lsp` alongside the integrations your
project uses. It runs over standard input/output and can be started with either command:

```sh
uv run mgtest-lsp
uv run mgtest lsp
```

`mgtest analyse` runs the same analysis directly, which is useful in CI or when
debugging editor diagnostics:

```sh
uv run mgtest analyse --root demo/mgtest demo/mgtest/t_health.yaml
```
