import org.jetbrains.intellij.platform.gradle.extensions.intellijPlatform

plugins {
    id("org.jetbrains.intellij.platform.settings") version "2.19.0"
}

rootProject.name = "mgtest-lsp-jetbrains"

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        intellijPlatform { defaultRepositories() }
    }
}
