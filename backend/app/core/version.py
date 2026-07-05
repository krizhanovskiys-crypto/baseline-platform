"""Single source of truth for the running application version.

Bumped by hand alongside RELEASE_NOTES.md — deliberately not derived
from git or overridable via environment, so it always reflects exactly
what was deployed, not what a config value happens to claim.
"""
APP_VERSION = "v0.12.0"
