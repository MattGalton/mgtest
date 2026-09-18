# mgtest LSP for JetBrains IDEs

<!-- Plugin description -->
Starts the `mgtest-lsp` Python language server for mgtest YAML files, providing the
same diagnostics, completion, hover text, navigation, and document symbols as the
core mgtest analyser.
<!-- Plugin description end -->

This is a standalone IntelliJ Platform plugin project. Its Gradle build, Kotlin
sources, sandbox, signing, and Marketplace publishing configuration all live here;
it is intentionally not a member of the repository's uv workspace.

## Local development and installation

Requirements: JDK 25 and `uv`. The first build downloads the target IntelliJ Platform
and Gradle dependencies.

```sh
cd src/mgtest-lsp-jetbrains
./gradlew runIde
```

`runIde` opens an isolated IDE sandbox with the plugin installed. Open an mgtest project
there and the plugin starts `uv run --directory /path/to/project mgtest-lsp`.

Build an installable ZIP with:

```sh
./gradlew buildPlugin
```

Install `build/distributions/mgtest-lsp-jetbrains-<version>.zip` using **Settings |
Plugins | gear menu | Install Plugin from Disk…**, then restart the IDE. This is a
manual local install and does not require a Marketplace account.

The default uses `uv` in the opened project so it sees that project's installed
`mgtest-lsp` and integrations. For a different environment, set **Settings | Tools |
mgtest**:

- **Server command**: an executable, such as `/path/to/.venv/bin/mgtest-lsp`.
- **Arguments**: optional command-line arguments, split using normal shell quoting.

The plugin starts for `r_*.yaml`, `t_*.yaml`, `s_*.yaml`, variables YAML, and YAML
specialisations below `resources/` or `tests/`.

## Verification and publication

```sh
./gradlew verifyPlugin
./gradlew buildPlugin
PUBLISH_TOKEN=... ./gradlew publishPlugin
```

`verifyPlugin` checks compatibility against JetBrains-recommended IDEs. `publishPlugin`
uses `PUBLISH_TOKEN` and the default Marketplace channel; use `-PpublishChannel=beta`
for a beta release. Set `CERTIFICATE_CHAIN`, `PRIVATE_KEY`, and `PRIVATE_KEY_PASSWORD`
to sign the ZIP before publishing. Create the Marketplace listing once manually, then
future versioned releases can use `publishPlugin`.
