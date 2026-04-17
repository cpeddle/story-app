plugins {
    id("story.android.library.compose")
}

android {
    namespace = "io.storyapp.feature.scene"
}

dependencies {
    implementation(project(":core:model"))
    implementation(project(":domain"))

    implementation(libs.androidx.lifecycle.runtime)
    implementation(libs.androidx.lifecycle.runtime.compose)
}
