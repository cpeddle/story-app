import com.android.build.gradle.LibraryExtension
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.artifacts.VersionCatalogsExtension
import org.gradle.kotlin.dsl.configure

class StoryAndroidLibraryComposeConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("story.android.library")
            pluginManager.apply("org.jetbrains.kotlin.plugin.compose")

            configure<LibraryExtension> {
                buildFeatures {
                    compose = true
                }
            }

            val libs = extensions.getByType(VersionCatalogsExtension::class.java).named("libs")

            dependencies.add("implementation", dependencies.platform(libs.findLibrary("compose-bom").get()))
            dependencies.add("implementation", libs.findLibrary("compose-ui").get())
            dependencies.add("implementation", libs.findLibrary("compose-ui-graphics").get())
            dependencies.add("implementation", libs.findLibrary("compose-material3").get())
            dependencies.add("implementation", libs.findLibrary("compose-foundation").get())
            dependencies.add("implementation", libs.findLibrary("compose-runtime").get())
            dependencies.add("debugImplementation", libs.findLibrary("compose-ui-tooling").get())
        }
    }
}
