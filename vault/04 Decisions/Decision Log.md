# Decision Log

## 2026-05-04 - Track the redesign in Obsidian
**Decision**  
Create an Obsidian vault inside `C:\Users\prash\Projects\ai_os\kairos\vault`.

**Why**  
The redesign work needs a persistent workspace for planning, active work, completed milestones, and future decisions.

**Impact**  
All project tracking notes now live alongside the codebase and can be opened directly as an Obsidian vault.

---

## 2026-05-04 - Position Kairos as a premium focus operating system
**Decision**  
Steer the redesign toward a calm, premium, local-first desktop experience.

**Why**  
The current app already has the right functional core. The highest leverage improvement is better guidance, hierarchy, and emotional quality.

**Impact**  
Future design and implementation work should favor clarity, calm, momentum, and polish over adding more raw controls.

---

## 2026-05-14 - Shift Kairos to a behavior-first discipline system

**Decision**  
Position Kairos as a behavior-first personal discipline system for time management, career compounding, and life balance.

**Why**  
The app now has enough core features. The next leverage point is reducing decision load, guiding the user through small loops, and making planning/review psychologically easier.

**Impact**  
Future work should simplify the existing screens before adding new ones. Today should be Now-first, Weekly should prevent fantasy planning, Review should lead with learning, and Coach should become contextual.

---

## 2026-05-14 - Use Review as the product language

**Decision**  
Use `Review` in docs and UI language instead of `History`.

**Why**  
History implies a passive archive. Review implies learning, adjustment, and behavior change.

**Impact**  
The technical route may remain `/history` temporarily, but the user-facing mental model is Review.

---

## 2026-05-14 - Keep docs and vault connected but separate

**Decision**  
Use `docs/` as the formal product documentation source and `vault/` as the Obsidian workspace for thinking, decisions, and execution tracking.

**Why**  
The repo needs durable product docs, while Obsidian is better for brainstorming, links, and active planning.

**Impact**  
When product direction changes, update the repo doc first, then update the matching vault note and decision log.

---

## 2026-05-15 - Fix the guidance gaps before adding more features

**Decision**  
Prioritize visible guidance and local resilience across Today, Weekly, Review, North Star, Brain, Areas, Goals, Research, and Coach.

**Why**  
Kairos should reduce user effort at the moment of action. The gap review showed that some important capabilities existed but were hidden, disconnected, or dependent on an external model provider.

**Impact**  
Today now exposes Auto-plan in the empty state. Weekly exposes auto-allocation in the realism guide. Review starts with three decisions. North Star connects to Brain through values, anti-vision, and alignment notes. Brain answers synthesize into profile fields. Areas can set quick targets. Goals warns when no next task exists. Research has a search-read-save flow. Coach falls back to local guidance when Hugging Face is unavailable.
