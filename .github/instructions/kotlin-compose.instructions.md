---
description: 'Kotlin and Jetpack Compose coding conventions for Story App. Covers coroutines, sealed classes, Compose patterns, and testing.'
applyTo: '**/*.kt'
---

# Kotlin & Jetpack Compose Conventions

## Kotlin Style

- Use `data class` for immutable value types. Use `sealed interface` for state/event hierarchies.
- Prefer `when` expressions with exhaustive branches over `if/else` chains for sealed types.
- Use `val` over `var`. Mutable state lives only in ViewModels via `MutableStateFlow`.
- Prefer extension functions for utility operations on domain types.
- Use `require()` / `check()` for preconditions at public API boundaries only.

## Coroutines

- Use structured concurrency. Never use `GlobalScope`.
- Long-running work (DB reads, asset loading, SVG rasterisation) MUST run on `Dispatchers.IO`.
- Domain and data layers are responsible for dispatching off-main.
- Use `viewModelScope` in ViewModels. Use `CoroutineScope` injection in domain services.
- Test coroutines with `runTest` and `Turbine` for Flow assertions.

## Sealed Class Patterns (MVI)

```kotlin
// State — one per screen, immutable snapshot
sealed interface SceneUiState {
    data object Loading : SceneUiState
    data class Playing(val scene: SceneSnapshot) : SceneUiState
}

// Events — dispatched from UI
sealed interface SceneUiEvent {
    data class TapCharacter(val characterId: String) : SceneUiEvent
    data class DragCharacter(val id: String, val offset: Offset) : SceneUiEvent
}

// Side effects — one-shot actions
sealed interface SceneSideEffect {
    data class PlaySound(val soundId: SoundId) : SceneSideEffect
    data class Navigate(val route: String) : SceneSideEffect
}
```

## Jetpack Compose

- Hoist state to the ViewModel. Composables receive state and emit events.
- Use `Modifier` as the first optional parameter on all composable functions.
- Chain modifiers in reading order: `Modifier.padding().size().clickable()`.
- Use `LaunchedEffect` for side effects tied to composition lifecycle.
- Use `remember` / `rememberSaveable` for local UI state only (not game state).
- Scene rendering uses `Canvas` composable with `DrawScope` — no Android Views in the scene.

## Compose Canvas (Scene Rendering)

- Draw characters as cached `ImageBitmap` via `drawImage()` — never re-parse SVG in the render loop.
- Use `detectDragGestures` and `detectTapGestures` for input.
- Touch targets: minimum 56dp × 56dp (≈2cm on target device).
- Limit scene entities to ≤6 characters + ≤15 objects (21 total).

## Dependency Injection (Hilt)

- Annotate ViewModels with `@HiltViewModel` and use `@Inject constructor`.
- Domain layer uses `javax.inject.Inject` only — no Android imports.
- Organise Hilt modules in `:data` (`@Provides` for Room, DataStore) and `:app` (`@Binds` for repository interfaces).
- Use `@Singleton` scope for repository implementations and engine instances.

## Room / Persistence

- Define entities with `@Entity`, DAOs with `@Dao`, queries with `@Query`.
- Return `Flow<T>` from DAOs for reactive updates.
- Use `@Transaction` for multi-table operations.
- Keep migration paths explicit — no `fallbackToDestructiveMigration()`.

## Testing

- Unit tests: JUnit 5 (`@Test`, `@Nested`, `@ParameterizedTest`).
- Flow tests: Turbine (`test { awaitItem(); awaitComplete() }`).
- Compose UI tests: `createComposeRule()` with `onNodeWithText()` / `onNodeWithContentDescription()`.
- Robolectric for Android-dependent unit tests (Context, Resources) — avoids emulator overhead.
- Use `@Config(sdk = [33])` to pin SDK level in Robolectric tests for reproducibility.
- Domain engine tests: pure functions, no mocking needed. Favour exhaustive state-transition tests.
- Repository tests: in-memory Room database with fake data.

## i18n

- Never hardcode user-facing strings. Use `R.string.*` references.
- Store all strings in `res/values/strings.xml` (EN) and `res/values-nl/strings.xml` (NL).
- Data model stores string keys, UI resolves to localised text at display time.

## What to Avoid

- ❌ `GlobalScope.launch` — use structured concurrency
- ❌ `MutableLiveData` — use `MutableStateFlow`
- ❌ Android View imports in `:domain` module
- ❌ `ColorFilter` tinting for multi-colour SVG parts — use AndroidSVG CSS overrides
- ❌ Hardcoded strings in Composables
- ❌ `fallbackToDestructiveMigration()` in Room
- ❌ Non-exhaustive `when` on sealed types
