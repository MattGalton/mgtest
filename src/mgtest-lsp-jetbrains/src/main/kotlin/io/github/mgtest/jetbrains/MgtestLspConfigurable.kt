package io.github.mgtest.jetbrains

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.project.Project
import com.intellij.ui.components.JBTextField
import com.intellij.util.ui.FormBuilder
import javax.swing.JComponent
import javax.swing.JPanel

class MgtestLspConfigurable(private val project: Project) : Configurable {
    private val command = JBTextField()
    private val arguments = JBTextField()

    override fun getDisplayName() = "mgtest"

    override fun createComponent(): JComponent = FormBuilder.createFormBuilder()
        .addLabeledComponent("Server command:", command)
        .addLabeledComponent("Arguments:", arguments)
        .addComponentFillVertically(JPanel(), 0)
        .panel

    override fun isModified(): Boolean {
        val state = MgtestLspSettings.getInstance(project).values
        return command.text != state.command || arguments.text != state.arguments
    }

    override fun apply() {
        val state = MgtestLspSettings.getInstance(project).values
        val command = this.command.text.trim()
        val arguments = this.arguments.text.trim()
        if (state.command != command || state.arguments != arguments) {
            state.command = command
            state.arguments = arguments
            restartMgtestLsp(project)
        }
    }

    override fun reset() {
        MgtestLspSettings.getInstance(project).values.let {
            command.text = it.command
            arguments.text = it.arguments
        }
    }
}
