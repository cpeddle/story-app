# Android Architecture — Deep Reference

Companion document to [`SKILL.md`](SKILL.md). Contains full matrices, tables, and technical decision log for the Story App Android architecture.

## Module Dependency Matrix

```
:app                    → ALL modules (wires DI)
:feature:scene          → :domain, :core:ui, :core:model, :core:common
:feature:character-editor → :domain, :core:ui, :core:model, :core:common
:feature:onboarding     → :domain, :core:ui, :core:model, :core:common
:feature:settings       → :domain, :core:ui, :core:model, :core:common
:domain                 → :core:model, :core:common (PURE KOTLIN — zero Android imports)
:data                   → :domain, :core:model (implements repository interfaces)
:core:ui                → :core:model (Compose components, theme)
:core:model             → (standalone — data classes, enums, sealed types)
:core:common            → (standalone — utilities, extension functions)
:core:testing           → :core:model (test fixtures, fakes)
:audio                  → :core:model (SoundPool wrapper)
:content-filter         → :core:model (TFLite wrapper)
```

### Enforcement Rules

- `:feature:*` MUST NOT depend on `:data` — access persistence only through `:domain` interfaces
- `:feature:*` MUST NOT depend on other `:feature:*` modules — no lateral feature coupling
- `:domain` MUST have zero Android imports — pure Kotlin only
- `:data` implements repository interfaces defined in `:domain`
- `:app` is the only module that wires Hilt implementations to interfaces

## Room Entities

| Entity | Module | Purpose |
|--------|--------|---------|
| `CharacterEntity` | `:data` | Character state, archetype, paper-doll selections |
| `MoodPairEntity` | `:data` | Directional mood per character pair |
| `SceneEntity` | `:data` | Scene layout, placed objects, character positions |
| `ObjectEntity` | `:data` | Object binary state, position |

## Compose Canvas — Full Architecture

- MUST use AndroidSVG library for SVG parsing and CSS overrides (TD-14)
- MUST rasterise on `Dispatchers.IO` — never on the main thread
- MUST cache `ImageBitmap` in memory — split body and face caches (TD-16)
  - **Body cache:** invalidate on paper-doll selection change (outfit, hair, accessories)
  - **Face cache:** 3 mood variants (happy/neutral/grumpy) per character, pre-rasterised
  - Face swap on mood change is instant (bitmap lookup, no re-rasterisation)
- Draw via `Canvas` composable using `drawImage()` — 2 calls per character (body + face)
- Never re-parse SVG in render loop
- MUST NOT use `ColorFilter` for multi-colour SVG parts
- Touch targets: minimum 56dp × 56dp
- Scene entity limit: ≤6 characters + ≤15 objects (21 entities max)

### Depth Scaling (RS-6)

- **All movable entities** scale with Y-position via `DepthBounds.scaleForY()` — fixed decor does not scale
- Scale applied at draw time via `Canvas.scale()` (GPU matrix transform, <0.1ms per frame)
- Cache bitmaps at scale 1.0, scale down at draw time — no additional cache memory
- `DepthBounds` per scene: stored in scene template, defines yMin/yMax/scaleAtBack/scaleAtFront/curve
- Default curve: `EasingCurve.EASE_IN_CUBIC` (validated on-device, RS6-D11)
- Z-ordering derived from Y-position for movable entities; fixed elements keep manual `zIndex`
- Hit-test radius always ≥56dp regardless of visual scale
- Dragged entity renders on top during drag; Z-order corrects on release
- Module placement: `DepthBounds`+`EasingCurve` in `:core:model`, `scaleForY()` in `:domain`

For the complete SVG authoring and layer stack pipeline, see the **art-pipeline** skill.

## Performance Budget

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cold start | <2s | First frame visible |
| Idle frame rate | 60 fps | No active interaction |
| Drag frame rate | ≥30 fps | During character drag |
| Auto-save latency | <100ms | Room write completion |
| APK size | <50 MB | Release build |
| Memory ceiling | <150 MB | Runtime peak |
| Character rasterisation | ~75ms body, ~30ms face | Per character, background thread |
| 6-character memory | ~57.6 MB | Cached ImageBitmaps (1 body + 3 faces per character) |

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
| TD-16 | Hybrid SVG rendering with split body/face caches |
| TD-17 | Unified flat vector style for characters and scenes |
| TD-18 | Y-position depth scaling with per-scene DepthBounds (RS-6) |
