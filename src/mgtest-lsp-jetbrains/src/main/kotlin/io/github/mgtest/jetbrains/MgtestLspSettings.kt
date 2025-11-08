package io.github.mgtest.jetbrains

import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project

@Service(Service.Level.PROJECT)
@State(name = "MgtestLspSettings", storages = [Storage("mgtest-lsp.xml")])
class MgtestLspSettings : PersistentStateComponent<MgtestLspSettings.State> {
    data class State(var command: String = "", var arguments: String = "")

    var values = State()
        private set

    override fun getState() = values.copy()

    override fun loadState(state: State) {
        values = state
    }

    companion object {
        fun getInstance(project: Project): MgtestLspSettings = project.service()
    }
}
