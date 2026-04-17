import com.android.build.gradle.LibraryExtension
import org.gradle.api.JavaVersion
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.artifacts.VersionCatalogsExtension
import org.gradle.api.tasks.testing.Test
import org.gradle.kotlin.dsl.configure
import org.gradle.kotlin.dsl.withType
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

class StoryAndroidLibraryConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            pluginManager.apply("com.android.library")
            pluginManager.apply("org.jetbrains.kotlin.android")

            configure<LibraryExtension> {
                compileSdk = 34
                buildToolsVersion = "36.1.0"

                defaultConfig {
                    minSdk = 26
                }

                compileOptions {
                    sourceCompatibility = JavaVersion.VERSION_17
                    targetCompatibility = JavaVersion.VERSION_17
                }
            }

            tasks.withType<KotlinCompile>().configureEach {
                compilerOptions {
                    jvmTarget.set(JvmTarget.JVM_17)
                }
            }

            val libs = extensions.getByType(VersionCatalogsExtension::class.java).named("libs")

            dependencies.add("testImplementation", libs.findLibrary("junit-jupiter-api").get())
            dependencies.add("testImplementation", libs.findLibrary("junit-jupiter-params").get())
            dependencies.add("testImplementation", libs.findLibrary("kotlin-test-junit5").get())
            dependencies.add("testRuntimeOnly", libs.findLibrary("junit-jupiter-engine").get())

            tasks.withType<Test>().configureEach {
                useJUnitPlatform()
            }
        }
    }
}
