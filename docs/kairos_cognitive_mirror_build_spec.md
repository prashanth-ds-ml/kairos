# Kairos Cognitive Mirror and Best-Self Coach Build Spec

Role: Product Leader / Product Designer / Systems Builder  
Review date: 2026-05-16  
Status: living build document

This document defines the evolved Kairos product after the idea shifted from a time-management app into a cognitive mirror plus best-self coach plus execution system.

Related docs:

- `docs/README.md` explains the documentation map and reading order.
- `docs/psychological_product_blueprint.md` defines the behavior-first philosophy.
- `docs/implementation_roadmap.md` translates the philosophy into build phases.
- `docs/product_discipline_audit.md` explains product loops, gaps, and redundancy.
- `docs/design_experience_review.md` explains the screen-level UX direction.
- `docs/hugging_face_coach.md` explains the current Coach setup.

## 1. Problem Statement

Most people do not fail because they lack ambition.
They fail because they do not have a system that helps them:

- see their own patterns clearly,
- understand what they actually value,
- notice what repeatedly pulls them off track,
- turn reflection into a realistic next action,
- and keep that loop going when motivation drops.

The common alternatives are incomplete:

- Task managers track work but do not understand the person.
- Journals capture thoughts but do not turn them into action.
- Habit apps push repetition but do not build self-knowledge.
- Generic AI assistants can answer questions but do not preserve a durable human context.

Kairos exists to close that gap.

## 2. Product Thesis

Kairos is a personal cognitive operating system.

It should help a user become more consistent by combining:

- a cognitive mirror that reflects identity, values, triggers, energy, and recurring patterns,
- a best-self coach that turns that reflection into the next honest move,
- and a planning system that converts intention into action.

The app should not claim to know the user better than the user knows themselves.
It should help the user see themselves more clearly than they can in the moment.

## 3. Vision

Kairos becomes the trusted personal mirror that helps someone understand who they are, what they value, what breaks their discipline, and what action best matches their current state.

## 4. Mission

Help the user capture their thoughts, behavior, goals, and friction; reflect them back in a clear and editable way; and convert that reflection into realistic plans, better decisions, and more consistent action.

## 5. Product Promise

See yourself clearly. Act like the person you are becoming.

## 6. Positioning

Kairos is not:

- a generic task manager,
- a passive note app,
- a therapy tool,
- a motivational content feed,
- or a black-box AI persona.

Kairos is:

- a local cognitive mirror,
- a best-self coach,
- a planning system,
- and a memory layer that compounds over time.

## 7. Product Model

The product should be understood in four layers.

### Mirror

The Mirror layer collects and shows:

- North Star answers,
- Brain questionnaire answers,
- life area scores,
- goal structures,
- focus triggers,
- weekly review notes,
- research notes,
- and search memory.

The Mirror layer answers:

- What have you been saying?
- What keeps happening?
- What do you seem to value?
- Where are you overcommitting or avoiding?
- What state are you in right now?

### Coach

The Coach layer turns the mirror into action.

It should answer:

- What is the smallest useful next move?
- What should be simplified?
- Which obstacle keeps repeating?
- What would the user's best self protect this week?

The coach should be concise, grounded, non-judgmental, and derived from Kairos data.

### Plan

The Plan layer turns reflection into commitments:

- Today
- Focus
- Weekly
- Goals
- Areas

### Memory

The Memory layer preserves the user's durable context:

- raw questionnaire answers,
- synthesized Brain profile fields,
- saved research,
- Obsidian notes,
- and review history.

## 8. Why This Can Become Big

The opportunity is bigger than time management.

Most tools handle one slice:

- planning,
- journaling,
- note capture,
- or AI chat.

Kairos can connect all four around self-understanding and behavior change.

The moat is not model novelty.
The moat is the compounding chain:

1. the user answers,
2. Kairos recognizes patterns,
3. the mirror becomes more precise,
4. the coach becomes more relevant,
5. the plan becomes more realistic,
6. the review becomes more honest,
7. the memory becomes more useful.

That loop can become a durable personal operating system.

## 9. Psychological Foundations

Kairos should borrow from evidence-based workflows, but it should not become clinical or preachy.

### 9.1 Implementation Intentions

If-then planning is one of the simplest and most useful behavior-change tools.

Use it for:

- daily pacts,
- focus pacts,
- weekly pacts,
- and obstacle handling.

Pattern:

- If X happens, then I will do Y.

Relevant source:

- https://www.sciencedirect.com/science/article/abs/pii/S0001691816304048

### 9.2 WOOP

WOOP gives a clean four-step planning flow:

- Wish
- Outcome
- Obstacle
- Plan

Use it for:

- weekly planning,
- blocked goals,
- and future-self planning.

Relevant source:

- https://woopmylife.org/en/practice

### 9.3 Self-Determination Theory

The three core needs to respect are:

- autonomy,
- competence,
- relatedness.

Use this to make the product feel self-directed, capable, and connected instead of controlling.

Relevant sources:

- https://selfdeterminationtheory.org/topics/application-basic-psychological-needs/
- https://selfdeterminationtheory.org/basic-psychological-need-satisfaction-scales/

### 9.4 Future Self Continuity

Kairos should increase the user's sense that the future self is real and connected to the present self.

Use this for:

- North Star,
- best possible self prompts,
- and coach prompts that compare present behavior to future identity.

Relevant sources:

- https://pubmed.ncbi.nlm.nih.gov/27064598/
- https://ggia.berkeley.edu/practice/best_possible_self

### 9.5 CBT Thought Records

When the user misses, stalls, or gets blocked, the app should ask for a structured reflection:

- situation,
- thought,
- feeling,
- evidence,
- balanced view,
- next action.

Relevant source:

- https://www.nhs.uk/every-mind-matters/mental-wellbeing-tips/self-help-cbt-techniques/thought-record/

### 9.6 Indistractable

Nir Eyal's model maps well to Kairos:

- internal triggers,
- external triggers,
- traction,
- pacts,
- timeboxing.

This should remain one of Kairos' central behavioral vocabularies.

Relevant source:

- https://www.nirandfar.com/wp-content/uploads/2025/02/Indistractable_Lesson_Plan_for_Educators_07152020.pdf

### 9.7 Jungian Depth Language

Use Jungian ideas carefully as reflective language, not diagnosis.

Useful concepts:

- persona,
- shadow,
- individuation,
- future self,
- inner conflict,
- integration.

This is useful in Brain prompts if the tone stays reflective and non-clinical.

Relevant sources:

- https://www.britannica.com/topic/analytic-psychology
- https://www.britannica.com/science/individuation-psychology

### 9.8 Best-Self Coaching Language

The product can borrow the tone of:

- Jim Kwik: mindset, motivation, method.
- Tony Robbins: results, purpose, massive action.
- Vishen: vision, state shift, structured reflection.

Use them as language patterns, not as doctrine.

Relevant sources:

- https://www.jimkwik.com/about-new/
- https://www.jimkwik.com/podcasts/kwik-brain-161-3-steps-to-becoming-limitless/
- https://www.tonyrobbins.com/rpm-system
- https://www.mindvalley.com/6phase-meditation

## 10. Product Pillars

### 10.1 Mirror

The Mirror pillar should:

- collect meaningful answers,
- keep raw answers visible,
- synthesize only what can be inspected,
- and show patterns without shame.

Key outputs:

- identity,
- values,
- anti-vision,
- current state,
- struggles,
- energy patterns,
- triggers,
- research memory,
- and weekly lessons.

### 10.2 Coach

The Coach pillar should:

- remain grounded in app data,
- offer one next move,
- avoid analysis dumps,
- and keep working when the external model is unavailable.

Key outputs:

- next action,
- simplification,
- warning,
- obstacle framing,
- or weekly adjustment.

### 10.3 Plan

The Plan pillar should:

- make capacity real,
- keep work small enough to start,
- and connect goals to specific actions.

Key surfaces:

- Today,
- Focus,
- Weekly,
- Goals,
- Areas.

### 10.4 Memory

The Memory pillar should:

- preserve raw answers,
- preserve saved research,
- link context across time,
- and remain editable.

Key stores:

- Brain answers,
- Brain profile,
- North Star,
- search memory,
- Obsidian notes,
- review history.

## 11. UX Principles

### 11.1 One Moment, One Question

Each screen should answer one question.

- Today: What should I do now?
- Focus: What am I doing for this block?
- Weekly: What is realistic this week?
- Review: What happened and what should change?
- Brain: What do I know about myself?
- Coach: What is the next move?

### 11.2 Read First, Edit Second

The user should see the summary or card before the form.

### 11.3 No Shame Language

Do not frame misses as failure.

Prefer:

- blocked,
- partial,
- underfunded,
- unclear,
- overcommitted,
- needs attention.

### 11.4 State-Aware Actions

The app should change its primary action based on state:

- no plan -> plan,
- planned -> start,
- blocked -> simplify,
- overcapacity -> reduce,
- finished -> review,
- tired -> shrink the next step.

### 11.5 Visible Chain of Truth

The user should be able to trace:

- answer -> synthesis -> coach guidance -> plan -> review.

### 11.6 Coach Should Feel Like the Best Self

The coach voice should feel like:

- calm,
- specific,
- grounded,
- and oriented toward the user's own stated values.

It should not feel like an outsider judging the user.

## 12. Screen System

### Today

Primary question: What should I do now?

Purpose:

- plan the day,
- choose 1-3 commitments,
- start the next block,
- close the loop.

Must contain:

- clear Now action,
- commitments,
- daily loop,
- shutdown,
- and secondary backlog.

### Focus

Primary question: What am I doing for this block?

Purpose:

- reduce choice,
- protect attention,
- record completion,
- and capture friction.

### Weekly

Primary question: What is realistic this week?

Purpose:

- set capacity,
- allocate goals,
- rollover backlog,
- expose fantasy planning,
- and guide a realistic week.

### Review

Primary question: What happened and what should change?

Purpose:

- explain the week,
- show planned vs actual,
- highlight the best goal,
- surface the neglected area,
- and recommend one adjustment.

### North Star

Primary question: Why does this matter?

Purpose:

- define identity,
- values,
- anti-vision,
- 90-day outcomes,
- and seasonal direction.

### Areas

Primary question: Is my life balanced enough?

Purpose:

- score life domains,
- set target minutes,
- compare actual to target,
- and identify underfunded areas.

### Goals

Primary question: What outcome am I moving and what is the next action?

Purpose:

- structure outcomes,
- show next tasks,
- show health,
- and keep goals executable.

### Brain

Primary question: What have I learned about myself?

Purpose:

- store questionnaire answers,
- synthesize profile fields,
- show recent memory,
- and support the mirror layer.

### Research

Primary question: What did I learn from this search?

Purpose:

- search locally,
- read inside Kairos,
- save only useful material,
- and attach it to goals, areas, or questions.

### Coach

Primary question: What is the next move?

Purpose:

- interpret the current state,
- simplify the decision,
- and keep the user moving.

## 13. Question System

The question system should be moment-based, not form-based.

### Onboarding Questions

Use these to establish the initial mirror:

- Who are you becoming?
- What do you want more of?
- What do you want less of?
- What are you avoiding?
- What would a good week look like?
- What would your best self protect?

### Daily Questions

Use these at the start or end of the day:

- What matters today?
- What is the must-win?
- What could pull me away?
- What do I need to protect?
- What is the smallest next step?

### Post-Session Questions

Use these after a focus block:

- What happened?
- Was this complete, partial, or blocked?
- What was the trigger?
- What was the friction?
- How was my quality, mood, and energy?
- What should change next time?

### Weekly Questions

Use these in Review:

- What moved forward?
- What did not?
- What was underfunded?
- What was the main friction?
- What should I simplify next week?

### Future-Self Questions

Use these to strengthen continuity:

- What does my best self protect?
- What does my future self thank me for?
- What would I regret ignoring?
- What does a good year from now look like?

### Shadow / Avoidance Questions

Use these carefully:

- What am I refusing to look at?
- What am I avoiding because it feels uncomfortable?
- What pattern keeps repeating?
- What identity am I protecting by not changing?

## 14. Data Model Intent

The app should preserve three types of context.

### Raw

Unprocessed answers, notes, and saved research.

### Synthesized

Editable profile fields and summary statements.

### Operational

Plans, sessions, weekly commitments, and review outcomes.

This separation matters because the user needs both truth and usable structure.

## 15. Build Order

### Phase 1: Finalize the Mirror

- stabilize Brain profile fields,
- expand question library,
- keep raw answers visible,
- make synthesis editable,
- preserve deletion/forget controls.

### Phase 2: Make Coach Useful at the Right Moment

- embed coach prompts on decision-heavy screens,
- generate concise guidance,
- keep a local fallback,
- and avoid analysis dumps.

### Phase 3: Connect Mirror to Plan

- link Brain insights to North Star,
- connect values to Goals,
- connect avoidance to Weekly and Focus,
- connect review lessons to next plans.

### Phase 4: Strengthen Memory

- improve Obsidian sync,
- improve search memory,
- add read/save organization,
- and make retrieval more useful.

### Phase 5: Add Future-Self Tools

- best possible self prompts,
- future-self continuity prompts,
- shadow / persona reflection,
- and seasonal reset flows.

## 16. Success Metrics

The product is working when:

- the user knows what to do next quickly,
- the user can explain their own patterns more clearly,
- weekly plans become more realistic,
- review produces one concrete adjustment,
- the user returns to Kairos when stuck,
- the memory layer becomes more useful over time,
- and the coach produces short, grounded guidance.

## 17. Risks and Guardrails

### Risk: Over-psychologizing the user

Guardrail:

- keep language reflective, not diagnostic,
- keep the user in control,
- and avoid certainty claims.

### Risk: Guru voice

Guardrail:

- use the user's own words,
- be concise,
- avoid hype,
- avoid moralizing.

### Risk: Memory overload

Guardrail:

- keep raw, synthesized, and operational layers separate,
- support delete/forget,
- and keep capture moments limited.

### Risk: Too much collection, not enough action

Guardrail:

- every mirror surface must point to a plan or a coach move,
- every question must have a purpose,
- every review must end in an adjustment.

### Risk: External model dependency

Guardrail:

- Coach must degrade gracefully into a local answer,
- and the app should remain useful without an external provider.

## 18. Big Product Direction

If Kairos succeeds, it becomes more than a planner.

It becomes the place where a person:

- remembers who they are becoming,
- notices what keeps breaking discipline,
- sees their own values clearly,
- makes better promises to themselves,
- and gets coached toward the next honest action.

That is the product to build.
## UX flow priority

Design is secondary to flow. The product should first solve the user's sequence of thought and action, then refine the visual system around that flow.

The primary journey is:

1. Arrive
   - User understands what Kairos is and why it exists.

2. Understand
   - Kairos asks a short, high-signal question set to learn North Star, values, current state, constraints, energy, and goals.

3. Translate
   - Kairos turns self-knowledge into a weekly direction and a small number of concrete goals.

4. Execute
   - The timer becomes the work engine tied to a goal or meaningful activity.

5. Reflect
   - Post-session prompts capture triggers, blockers, energy, mood, and quality.

6. Review
   - Weekly review shows planned vs actual, recurring patterns, misses, and next adjustments.

The current shell maps that journey to:

`Start -> Mirror -> Plan -> Focus -> Review`

Everything else is secondary to this loop:

`identity -> intention -> plan -> action -> reflection -> adjustment`

This means:

- Every screen should have one job.
- Any page that repeats another page's meaning should be merged or reduced.
- Reflection must feed planning.
- Planning must feed execution.
- Execution must feed review.
- The app should always answer the user's implicit question: "What should I do next?"
