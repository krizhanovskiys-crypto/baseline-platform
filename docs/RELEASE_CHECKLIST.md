# Baseline Release Checklist

**Version:** 1.0  
**Owner:** Baseline Engineering  
**Status:** Active

This checklist must be completed before every release or commit of a user-facing feature.

---

## Stop Release Rule

If any item in this checklist fails, the release is blocked.

Do not commit user-facing functionality until all mandatory checks pass or the remaining issues are explicitly documented and approved.

---

## 1. Automated checks

- [ ] `pytest` passes with no failures
- [ ] Dispatcher starts successfully (`python -m backend.app.bot.main`)
- [ ] No traceback during startup
- [ ] No failing migrations (`alembic upgrade head`)
- [ ] No lint/type errors (if applicable)

---

## 2. Core user flows

Verify manually:

- [ ] `/start`
- [ ] Registration (onboarding wizard)
- [ ] Edit Profile
- [ ] Create Match
- [ ] Find Players
- [ ] Invite Player
- [ ] Accept Invitation
- [ ] Decline Invitation
- [ ] My Matches
- [ ] Match Details (when implemented)

---

## 3. Telegram UX

Verify:

- [ ] Reply keyboards render correctly
- [ ] Inline keyboards render correctly
- [ ] Callback buttons respond
- [ ] Emojis display as intended
- [ ] Localization — EN, UK, RU
- [ ] No broken navigation paths
- [ ] Back and Home buttons return to the correct screen

---

## 4. Database

Verify:

- [ ] Game record created with correct status
- [ ] Invitation record created after Invite action
- [ ] Status transitions are correct (DRAFT → OPEN → PARTIALLY_FILLED → FULL → CONFIRMED)
- [ ] No duplicate records
- [ ] No orphan records

---

## 5. Notifications

Verify:

- [ ] Organizer receives notifications at correct lifecycle events
- [ ] Invited player receives invitation message
- [ ] Error messages are shown when appropriate
- [ ] Delivery failure is reported honestly (no false success)
- [ ] No misleading success messages when Telegram delivery fails

---

## 6. Regression

Confirm that previously working functionality still works:

- [ ] Find Partner
- [ ] Create Match
- [ ] Invitations
- [ ] My Matches
- [ ] Profile
- [ ] Edit Profile

---

## 7. Manual Telegram test

Run one complete real-world flow before every release.

**Organizer**

1. Create Match
2. Find Players
3. Invite a player

**Player**

4. Receive invitation notification
5. Accept invitation

**Organizer**

6. Verify the player appears in the match roster

**Player**

7. Verify the match appears in My Matches

---

## 8. Ready for commit?

- [ ] All automated tests passed
- [ ] Manual Telegram flow completed successfully
- [ ] No known blockers
- [ ] Technical debt documented
- [ ] Commit approved

---

> A feature is considered complete only after it passes both automated verification and real Telegram testing.
