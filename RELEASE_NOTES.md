# Baseline Release Notes

---

## v0.3.0

### New

* Player onboarding
* Player profile
* Settings
* Find Partner
* Organize Match
* Find Players for a Match
* Match invitations
* Accept invitation
* Decline invitation
* Automatic match player count updates
* Ukrainian, English and Russian localization

### Improved

* Simplified terminology ("Invite" instead of "Select")
* Streamlined match organization flow
* Cleaner user interface

### Removed

* Rating from all user-facing interfaces

### Internal

* New Invitation domain
* Invitation model
* Invitation repository
* Invitation service
* Invitation handlers
* Alembic migration support
* Standardized architecture (Model → Repository → Service → Handler)
