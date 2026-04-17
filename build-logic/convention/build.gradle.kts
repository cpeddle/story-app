plugins {
    `kotlin-dsl`
}

dependencies {
    compileOnly(libs.android.gradlePlugin)
    compileOnly(libs.kotlin.gradlePlugin)
    compileOnly(libs.compose.gradlePlugin)
}

gradlePlugin {
    plugins {
        register("storyKotlinLibrary") {
            id = "story.kotlin.library"
            implementationClass = "StoryKotlinLibraryConventionPlugin"
        }
        register("storyAndroidLibrary") {
            id = "story.android.library"
            implementationClass = "StoryAndroidLibraryConventionPlugin"
        }
        register("storyAndroidLibraryCompose") {
            id = "story.android.library.compose"
            implementationClass = "StoryAndroidLibraryComposeConventionPlugin"
        }
    }
}
