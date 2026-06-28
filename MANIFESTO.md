# BASELINE MANIFESTO

## Why Baseline exists

Baseline exists to make playing tennis easier.

Finding people to play with should be as simple as sending a message—not spending days in group chats.

Our goal is to remove friction between the decision to play and stepping onto the court.

---

# Mission

Connect tennis players, coaches, clubs and communities through one simple platform.

---

# Vision

Baseline is not a Telegram bot.

Telegram is only the first client.

Baseline is a tennis platform that will eventually power:

* Telegram
* Mobile apps
* Web
* Club dashboards
* Tournament management

One backend.

Multiple clients.

---

# Product Principles

Every feature must solve a real user problem.

Simple beats clever.

Less is better.

The shortest user flow wins.

Never build features only because they are technically interesting.

---

# Our Users

Baseline is built for an entire tennis ecosystem.

## Player

Find partners.

Join matches.

Play more tennis.

---

## Coach

Teach.

Organize lessons.

Recommend players.

Build communities.

Become a verified coach.

---

## Club

Publish courts.

Host events.

Run tournaments.

Manage members.

---

## Community

Bring people together around tennis.

---

# Roles

Role defines who you are.

Examples:

* Player
* Coach
* Club

---

# Permissions

Permissions define what you can manage.

Levels:

* User
* Moderator
* Admin
* Owner

Roles and permissions are independent.

---

# Trust

Trust is earned.

Not claimed.

Baseline should always prefer verified information over self-declared information.

Examples:

Verified Coach

Verified Club

Verified Tournament

Future verified player levels.

---

# Architecture Principles

Business logic belongs in Services.

Repositories only access data.

Handlers never contain business logic.

Every new domain should follow:

Model

Repository

Service

Handler

---

# Product Philosophy

Baseline should always do part of the work for the user.

Users should not fight the interface.

The platform should reduce decisions, clicks and messages.

---

# Scaling

Everything should scale naturally from:

One city

↓

Multiple cities

↓

One country

↓

Multiple countries

No feature should be designed only for Toronto.

---

# What we are NOT building

We are not building another chat.

We are not building another social network.

We are not building another booking system.

We are building infrastructure for the tennis community.

---

# Definition of Success

A player opens Baseline.

Finds people.

Schedules a match.

Steps onto the court.

Everything else is secondary.
