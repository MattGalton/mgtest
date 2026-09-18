package io.github.mgtest.jetbrains

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.util.execution.ParametersListUtil
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.platform.lsp.api.LspClientManager
import com.intellij.platform.lsp.api.LspIntegrationProvider
import com.intellij.platform.lsp.api.ProjectWideLspClientDescriptor

/** Starts one mgtest language-server process for each project that contains mgtest YAML. */
class MgtestLspIntegrationProvider : LspIntegrationProvider {
    override fun fileOpened(
        project: Project,
        file: VirtualFile,
        clientStarter: LspIntegrationProvider.LspClientStarter,
    ) {
        if (MgtestLspClientDescriptor.isMgtestFile(file)) {
            clientStarter.ensureClientStarted(MgtestLspClientDescriptor(project))
        }
    }
}

fun restartMgtestLsp(project: Project) {
    LspClientManager.getInstance(project)
        .stopAndRestartClientsIfNeeded(MgtestLspIntegrationProvider::class.java)
}

class RestartMgtestLspAction : AnAction("Restart mgtest Language Server") {
    override fun actionPerformed(event: AnActionEvent) {
        event.project?.let(::restartMgtestLsp)
    }
}

private class MgtestLspClientDescriptor(project: Project) :
    ProjectWideLspClientDescriptor(project, "mgtest") {
    override fun isSupportedFile(file: VirtualFile): Boolean = isMgtestFile(file)

    override fun createCommandLine(): GeneralCommandLine {
        val settings = MgtestLspSettings.getInstance(project).values
        if (settings.command.isNotBlank()) {
            LOG.info("Starting mgtest language server using configured command '${settings.command}'")
            return GeneralCommandLine(settings.command)
                .withParameters(ParametersListUtil.parse(settings.arguments))
                .withWorkDirectory(project.basePath)
        }
        val root = requireNotNull(project.basePath) { "mgtest requires a project directory" }
        LOG.info("Starting mgtest language server through uv for $root")
        return GeneralCommandLine("uv")
            .withParameters("run", "--directory", root, "mgtest-lsp")
            .withWorkDirectory(root)
    }

    companion object {
        private val LOG = Logger.getInstance(MgtestLspClientDescriptor::class.java)

        fun isMgtestFile(file: VirtualFile): Boolean {
            val extension = file.extension?.lowercase()
            if (extension !in setOf("yaml", "yml")) return false
            return file.name in setOf("vars.yaml", "vars.yml", "variables.yaml", "variables.yml") ||
                file.name.startsWith("r_") || file.name.startsWith("t_") || file.name.startsWith("s_") ||
                file.parent?.name in setOf("resources", "tests")
        }
    }
}
