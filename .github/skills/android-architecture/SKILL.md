---
name: android-architecture
description: 'MVI architecture patterns, module boundaries, Hilt DI, Room persistence, Compose Canvas rendering, SoundPool audio, and performance budget for the Story App Android tablet project. Invoke when creating ViewModels, defining module dependencies, wiring DI, setting up persistence, or implementing scene rendering.'
---

# Android Architecture — Story App

## When to Use This Skill

Invoke when:
- Creating or modifying a ViewModel, Repository, DAO, or UseCase
- Adding a new module or changing module dependencies
- Implementing scene rendering or character compositing
- Wiring Hilt dependency injection
- Evaluating performance against the budget
- Setting up Room entities, migrations, or queries

## Architecture Pattern: MVI

### Complex Screens (Scene, Character Editor)

```
UiEvent → ViewModel → Domain Engine → Repository → Room
            ↓
         UiState (sealed)
            ↓
      Composable
            ↓
      SideEffect (SharedFlow)
```

- One sealed `UiState` with exhaustive `when` branches
- One sealed `UiEvent` — UI dispatches events, never mutates state
- `SharedFlow<SideEffect>` for one-shot actions (sound, navigation, toast)
- Single `StateFlow<UiState>` exposed — UI collects, never pushes

### Simple Screens (Settings, About)

Plain `MutableStateFlow` acceptable; maintain unidirectional flow.

## Module Boundaries

**Key Enforcements:**
- `:feature:*` → `:domain`, `:core:ui`, `:core:model`, `:core:common` only
- `:feature:*` MUST NOT depend on `:data` or other `:feature:*` modules
- `:domain` → zero Android imports (pure Kotlin)
- `:data` implements `:domain` interfaces
- `:app` wires Hilt implementations

See [`references.md`](references.md) for full dependency matrix.

## Hilt Dependency Injection

- ViewModels: `@HiltViewModel` + `@Inject constructor`
- Domain: `javax.inject.Inject` only
- Bindings: `@Binds` in `:app`, `@Provides` in `:data`
- Scope: `@Singleton` for repos and engines
- Context: `@ApplicationContext` only where needed

## Room Persistence

- `@Entity` / `@Dao` annotations
- DAOs return `Flow<T>` (reactive)
- `@Transaction` for multi-table operations
- Explicit migrations (MUST NOT destructive)
- Auto-save target: <100ms latency

See [`references.md`](references.md) for entity definitions.

## Compose Canvas — Scene Rendering

- MUST use AndroidSVG (TD-14)
- Rasterise on `Dispatchers.IO` — never main thread
- Cache `ImageBitmap`, invalidate on paper-doll change only
- Draw via `drawImage()` — no SVG re-parsing in render loop
- Touch targets: 56dp minimum
- Scene: ≤6 characters + ≤15 objects max

See **art-pipeline** skill for full rendering pipeline.

## SoundPool Audio

- SFX only (no background music in MVP)
- Use `SoundPool` (TD-6), not MediaPlayer/ExoPlayer
- Preload at entry, fire-and-forget playback

## Security

- MUST NOT declare `INTERNET` permission — fully offline
- MUST NOT collect analytics or telemetry
- App-private storage only
- ProGuard/R8 mandatory for release
- Content filtering: on-device TFLite (TD-13)

## Deep Reference

See [`references.md`](references.md) for full module dependency matrix, Room entity table, performance budget, and technical decision log (TD-1–TD-15).
- App-private storage only — no export, no sharing intents
- ProGuard/R8 mandatory for release builds
- Content filtering via on-device TFLite (TD-13)

## Technical Decision Log

Reference these IDs when justifying architectural choices:

| ID | Decision |
|----|----------|
| TD-1 | Jetpack Compose (not Views/XML) |
| TD-2 | Hilt (not Koin) |
| TD-3 | Room + DataStore (not Realm) |
| TD-4 | MVI-pragmatic (complex) + StateFlow (simple) |
| TD-5 | Compose Canvas for scene rendering |
| TD-6 | SoundPool for SFX |
| TD-7 | Compose Navigation with type-safe routes |
| TD-8 | Multi-module architecture |
| TD-9 | Convention plugins in build-logic/ |
| TD-10 | JUnit 5 + Turbine + Compose Testing |
| TD-11 | Kotlinx Serialization |
| TD-12 | Version Catalog (libs.versions.toml) |
| TD-13 | On-device TFLite content filter |
| TD-14 | AndroidSVG for paper-doll rendering |
| TD-15 | Flat vector / SVG art style |
