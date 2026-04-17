plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "io.storyapp"
    compileSdk = 34
    buildToolsVersion = "36.1.0"

    defaultConfig {
        applicationId = "io.storyapp"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0-rs6-stage2"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(project(":core:model"))
    implementation(project(":domain"))
    implementation(project(":feature:scene"))

    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.foundation)

    implementation(libs.androidx.lifecycle.runtime)
    implementation(libs.androidx.activity.compose)
}
