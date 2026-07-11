# Baseline iOS — Architecture

**Purpose:** the technical reference for the iOS client's folder
structure and current state. Companion to `docs/Baseline_Domain_Model.md`
(target domain) and `docs/Baseline_API_v2_Architecture.md` (target API
contract) — those two describe where the client is *headed*; this
document describes what actually exists in the Xcode project today.
Created alongside the project itself (production foundation pass), not
retrofitted later, specifically so it never drifts into describing
files or layers that were never built — a documented failure mode
already seen elsewhere in this repo's docs.

---

## Project location

The Xcode project lives **outside this repository**, at
`~/Projects/BaselineDemo/` — a separate client codebase from this
Python/Telegram backend, matching how `docs/Baseline_Domain_Model.md`
§0.1 frames the platform ("Backend, Telegram, iOS, Web Admin, Android —
one domain model underneath all of them", not one repo).

```
~/Projects/BaselineDemo/
├── BaselineDemo.xcodeproj/
└── BaselineDemo/              ← source root (Xcode group "BaselineDemo")
    ├── App/
    ├── Theme/
    ├── Components/
    ├── Networking/
    ├── Models/
    ├── Features/
    └── Resources/
```

- **Product name / target:** `BaselineDemo`
- **Bundle identifier:** `com.baseline.demo`
- **Minimum iOS:** 17.0
- **Interface:** SwiftUI, Swift language mode 5

## Folder structure and what belongs in each

| Folder | Purpose | Current contents |
|---|---|---|
| `App/` | App lifecycle entry point and the app's root shell | `BaselineDemoApp.swift` (`@main`, instantiates `RootView()`), `RootView.swift` (the `TabView` with the app's 5 tabs) |
| `Theme/` | Design tokens and shared view modifiers — the one place colors/fonts are defined | `Theme.swift` (`enum Theme` color tokens, `ThemedBackground` view modifier) |
| `Components/` | SwiftUI views reused across more than one Feature — never a single-feature-only view | `PlayerRow.swift`, `MatchCard.swift`, `InfoRow.swift` |
| `Networking/` | The future backend client layer (`URLSession` calls against `docs/Baseline_API_v2_Architecture.md`'s endpoints) | Empty — see "Current state" below |
| `Models/` | Plain data types and (for now) their sample data | `Models.swift` (`Player`, `Match`, `MatchRole`), `MockData.swift` (static sample arrays) |
| `Features/` | One subfolder per screen/tab — a Feature owns the views specific to it, never shared across Features (shared views move to `Components/`) | `Home/`, `FindPartner/`, `OrganizeMatch/`, `MyMatches/`, `Profile/` — each with its one `View.swift` |
| `Resources/` | Non-code assets | `Assets.xcassets` (empty catalog — no app icon/accent color configured yet) |

**Where `MockData.swift` lives, and why:** not listed among the 7
requested top-level folders on its own — placed in `Models/` since it's
sample data for the types declared in `Models.swift`, not a Feature.
Every screen currently reads from it directly; this is the one thing
that changes once `Networking/` is real (see below).

**Why `Components/` isn't empty:** `PlayerRow`, `MatchCard`, and
`InfoRow` were previously declared inline inside the feature view files
that first used them (`HomeView.swift`, `ProfileView.swift`) even
though `MatchCard` is used by two different Features (`Home` and
`MyMatches`). Extracted into their own files as part of this
foundation pass — same views, same visual output, just no longer
duplicated-by-proximity inside a feature file that isn't the only
feature using them. No view logic or design changed.

## Current state

- **UI:** unchanged from the original mockup — same 5 tabs (Home, Find
  Partner, Organize Match, My Matches, Profile), same visual design,
  same interactions (or lack of them). This pass moved files and
  configured the project; it did not touch any screen's UI or logic.
- **Data:** 100% `Models/MockData.swift`. No screen calls the backend.
- **`Networking/`:** exists as an empty folder/group, reserved for the
  `URLSession` client that will eventually call the endpoints in
  `docs/Baseline_API_v2_Architecture.md` (`GET /api/v1/games/`,
  `GET /api/v1/players/{id}/partners`, etc.). Not started.

## Relationship to the backend architecture docs

`docs/Baseline_Domain_Model.md` and `docs/Baseline_API_v2_Architecture.md`
describe a considerably larger target surface than what exists in the
Xcode project today — Tournament screens, a `ProfileViewModel`-style
MVVM layer, a `BaselineDesignSystem` module, an Authentication domain.
**None of that exists yet.** Those two documents are the target
contract for future work, not a description of the current client.
Treat them as forward-looking, and treat this document as the one that
reflects reality — if the two ever disagree about what's *already
built*, this document wins, per the same "repository reality overrides
assumptions" rule the backend docs already operate under.

## Build verification

`xcodebuild build -project BaselineDemo.xcodeproj -scheme BaselineDemo
-destination 'generic/platform=iOS Simulator'` succeeds with zero
errors and no warnings beyond a benign "no AppIntents.framework
dependency found" notice (expected — the project has no App Intents).
