import org.jetbrains.intellij.platform.gradle.tasks.RunIdeTask
import org.gradle.process.CommandLineArgumentProvider
import org.gradle.api.tasks.compile.JavaCompile
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    kotlin("jvm") version "2.4.20"
    id("org.jetbrains.intellij.platform")
}

group = "io.github.mgtest"
version = providers.gradleProperty("pluginVersion").get()

repositories {
    mavenCentral()
    intellijPlatform { defaultRepositories() }
}

dependencies {
    intellijPlatform { intellijIdea(providers.gradleProperty("platformVersion")) }
}

kotlin {
    jvmToolchain(25)
    compilerOptions.jvmTarget = JvmTarget.JVM_25
}

intellijPlatform {
    pluginConfiguration {
        id = providers.gradleProperty("pluginId")
        name = providers.gradleProperty("pluginName")
        version = providers.gradleProperty("pluginVersion")
        description = providers.fileContents(layout.projectDirectory.file("README.md")).asText.map {
            it.substringAfter("<!-- Plugin description -->").substringBefore("<!-- Plugin description end -->")
        }
        ideaVersion { sinceBuild = providers.gradleProperty("pluginSinceBuild") }
    }
    publishing {
        token = providers.environmentVariable("PUBLISH_TOKEN")
        channels = providers.gradleProperty("publishChannel").map { listOf(it) }.orElse(listOf("default"))
    }
    signing {
        certificateChain = providers.environmentVariable("CERTIFICATE_CHAIN")
        privateKey = providers.environmentVariable("PRIVATE_KEY")
        password = providers.environmentVariable("PRIVATE_KEY_PASSWORD")
    }
    pluginVerification { ides { recommended() } }
}

tasks {
    withType<JavaCompile> {
        options.release = 25
    }
    withType<RunIdeTask> {
        jvmArgumentProviders += CommandLineArgumentProvider {
            listOf("-Didea.log.debug.categories=#io.github.mgtest.jetbrains")
        }
    }
}
