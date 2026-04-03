# DentAI

DentAI is an AI-supported dental education platform designed to help students practice clinical reasoning through interactive patient cases. Instead of studying pathology only as static notes or slide decks, learners work through simulated oral medicine and oral pathology encounters, ask questions, perform examinations, gather findings, form differentials, and move toward diagnosis and management decisions inside a guided digital environment.

The project focuses on turning clinical knowledge into repeatable practice. It is built around the idea that students improve faster when they can actively test their decision-making, receive immediate feedback, and revisit their own performance patterns over time.

## Project purpose

DentAI was created to support dental students during the difficult transition from theoretical learning to clinical reasoning. In many traditional learning settings, students memorize lesion descriptions, disease names, and treatment principles, but have fewer chances to practice the flow of an actual encounter: what to ask first, what to inspect, which hidden clues matter, what is risky to miss, and how to distinguish similar-looking conditions.

DentAI addresses that gap by presenting cases as interactive simulations rather than passive content. The learner is not just shown the answer. They are expected to investigate, interpret, and act.

## What the app is

At its core, DentAI is a case-based simulator with a hybrid evaluation model:

- An AI layer interprets the student's free-text clinical actions and conversational input.
- A rule-based assessment layer scores meaningful actions against case-specific expectations.
- A persistent session layer keeps track of what the student has already discovered, what findings are still hidden, and how the case is progressing.
- An analytics layer converts session history into performance trends, action breakdowns, and recommendations.

This makes the project more than a chatbot and more than a quiz bank. It is a structured educational system that combines open-ended interaction with controlled educational scoring.

## Learning experience

DentAI is designed around a realistic student workflow.

The learner begins by logging in and choosing a case. Each case represents a clinical scenario with a patient profile, a chief complaint, and hidden findings that are only revealed when the student performs relevant actions. The student then interacts with the system in natural language, for example by asking about medical history, checking allergies, performing an oral examination, requesting a relevant test, or exploring systemic symptoms.

As the interaction continues, the system interprets the learner's intent and maps it into normalized clinical actions. Those actions are then compared with case rules to determine whether the learner is progressing appropriately, missing key information, or taking a weak or unsafe route. This creates a training flow that feels conversational while still staying anchored to specific educational objectives.

The student experience is meant to reward good habits:

- asking relevant history questions before jumping to conclusions
- performing focused oral and extraoral examinations
- recognizing findings that support or challenge a diagnosis
- considering systemic context rather than treating lesions in isolation
- avoiding unsafe or clinically inappropriate shortcuts

## Educational philosophy

DentAI emphasizes clinical reasoning over simple answer retrieval. The project is not built around "guess the diagnosis" alone. It encourages a broader sequence of professional thinking:

- gather information
- identify meaningful findings
- prioritize safety
- connect the case presentation to pathology knowledge
- decide on next steps
- reflect on performance afterward

That matters because in real clinical education, knowing a disease name is only one part of competence. Students also need to learn how to arrive at a diagnosis responsibly and how to justify their decisions.

## Core simulation model

Each case in DentAI contains educational structure behind the scenes. A scenario can include:

- patient demographics
- chief complaint
- medical and social history
- hidden clinical findings
- expected learner actions
- diagnosis targets
- differential diagnosis context
- treatment-related expectations

Some findings remain concealed until the learner performs the appropriate step. For example, a case may not reveal an oral lesion pattern until the student performs an oral exam, or may not expose an important systemic clue until the student asks the right follow-up question. This makes the interaction feel closer to a guided clinical encounter than a static case card.

## Hybrid AI and rules approach

One of the most important ideas in DentAI is that educational simulation should not rely entirely on a generative model.

The project uses AI where flexibility is useful and rules where reliability is necessary.

The AI component helps the system understand student language. Students do not need to type exact predefined commands. They can express themselves more naturally, and the model attempts to interpret whether the learner is chatting casually, taking a clinical action, checking a safety issue, requesting a diagnostic step, or moving toward treatment planning.

The rule engine then provides structure. Once an action is interpreted, DentAI compares it to the scoring rules for the active case. This allows the platform to award points, reveal findings, update state, and keep evaluation tied to educational intent rather than to vague model impressions.

This hybrid design is especially important in a medical or dental learning context because it balances flexibility with consistency.

## Silent evaluation concept

The project also includes a "silent evaluator" idea in its workflow. The learner mainly sees the patient-facing or tutor-facing response, while deeper evaluation can happen in the background. That means the conversation can continue naturally without exposing every internal scoring decision in the middle of the interaction.

This is useful educationally because the student can stay engaged with the case instead of being interrupted by technical scoring output after every message. At the same time, the system still collects enough structured information to support analytics, feedback, and research-oriented review later.

## Types of cases currently represented

The case library centers on oral pathology and clinically important oral lesions. Current scenarios in the repository include cases such as:

- Oral lichen planus
- Chronic periodontitis in a medically relevant patient
- Primary herpetic gingivostomatitis
- Pediatric infectious oral presentation
- Behcet disease
- Secondary syphilis with oral findings
- Desquamative gingivitis and mucous membrane pemphigoid context

These cases are educationally valuable because they mix local oral findings with broader clinical interpretation. Some require recognition of lesion pattern, some emphasize systemic history, some test safety awareness, and some challenge the learner to separate similar-looking conditions.

## What students practice inside DentAI

DentAI is built to support repeated practice of the kinds of micro-decisions that matter during case work. Depending on the scenario, students may practice:

- medical history taking
- allergy and medication review
- oral examination
- extraoral examination
- differential diagnosis thinking
- identifying red flags
- asking for diagnostic tests
- linking symptoms to systemic disease
- deciding whether a management pathway is appropriate
- recognizing when an intervention would be unsafe or irrelevant

Because the cases are interactive, learners can experience the consequences of missing a clue or taking a less effective path. That makes the project useful not just for content recall, but for judgment training.

## Feedback and analytics

DentAI does not stop at the simulated conversation. The project also tracks student interactions over time and turns those into performance insights.

The platform records sessions, chat actions, scores, and feedback data. These can be used to generate:

- total score trends
- action histories
- action-type breakdowns
- per-student performance summaries
- simple recommendations about weaker areas

This matters because students often need more than "right" or "wrong." They benefit from seeing patterns in how they work. A learner may discover that they consistently perform well in history-taking but miss critical examination steps, or that they frequently underperform in one type of scenario. DentAI tries to make those patterns visible.

## Quiz and reinforcement features

In addition to interactive cases, the repository includes multiple-choice question support. These questions appear to be organized around oral pathology, infectious disease, and traumatic lesion topics. That gives the project a second learning mode:

- open-ended simulation for reasoning practice
- structured question review for reinforcement and recall

This combination is valuable because students often need both. Simulation helps with process and judgment, while question banks help consolidate factual distinctions and key diagnostic principles.

## Research and academic value

DentAI also has value as an educational research platform. Because it stores session data, feedback, and interaction history, it can support analysis of how students engage with cases, where they struggle, and which kinds of prompts or scenarios produce stronger learning patterns.

The repository already includes analytics export routes and supporting documentation artifacts, which suggests the system is not only for direct teaching use but also for studying educational outcomes and learner behavior.

## Who the project is for

DentAI is especially suited for:

- dental students learning oral pathology and oral diagnosis
- instructors who want a guided digital practice environment
- curriculum projects exploring AI-assisted clinical education
- researchers interested in interaction data from simulated case learning

It is most useful in contexts where learners need practice reasoning through oral lesions and patient presentation rather than only memorizing textbook descriptions.

## What makes DentAI distinct

Several things make the project stand out from a standard educational chatbot:

- it uses case progression rather than isolated prompt-response interaction
- it keeps hidden findings and discovery logic inside each scenario
- it combines natural language interpretation with explicit scoring rules
- it preserves session state and student history
- it includes analytics, feedback capture, and quiz support alongside simulation

That combination gives the project a stronger educational shape. The system is trying to teach a process, not just generate plausible answers.

## Current product shape

In its current form, DentAI includes:

- authenticated user access with role-aware behavior
- a student-facing case dashboard and chat workflow
- session persistence across case attempts
- performance statistics and recommendation features
- quiz support for reinforcement outside the simulation flow
- instructor-facing monitoring and drilldown endpoints
- admin-facing content, user, rules, and health management endpoints

The repository still contains traces of an earlier Streamlit-based iteration, but the active product path is the FastAPI backend plus the Next.js frontend.

## Technical architecture

At a system level, DentAI is organized as a web application with a clear split between interface, application logic, and persistence.

- The frontend is a Next.js application that handles authentication state, route protection, case browsing, chat interaction, statistics views, quiz views, and role-specific screens.
- The backend is a FastAPI application that exposes REST endpoints under `/api/*`.
- Core educational logic lives in Python services and engines that interpret actions, evaluate them, update scenario state, and persist telemetry.
- Persistence is handled through SQLAlchemy with SQLite as the default runtime database.

The technical shape is intentionally hybrid. The language model is used to interpret student input, but important educational decisions such as scoring, state transition, role checks, and telemetry persistence are handled in deterministic backend code.

## Backend responsibilities

The backend is responsible for the parts of the system that need consistency, persistence, and policy enforcement:

- authenticating users and issuing JWT access tokens
- enforcing role boundaries for student, instructor, and admin features
- loading case content and scoring rules
- resolving or initializing case session state
- processing chat interactions
- storing logs, scores, feedback, recommendations, and audit data
- generating analytics and CSV exports
- exposing recommendation, instructor, and admin APIs

The FastAPI application wires these domains together through routers mounted in `app/api/main.py`.

## Request lifecycle

The main chat workflow follows a predictable backend path:

1. The frontend sends an authenticated request to the chat API with `message` and `case_id`.
2. The backend resolves the user from the JWT and loads or creates a `StudentSession`.
3. The student's raw message is stored in `ChatLog`.
4. The agent interprets the message into a normalized clinical action.
5. The assessment engine checks that action against case-specific rules.
6. Scenario state is updated and session score is adjusted.
7. The assistant response plus evaluation metadata is written back to `ChatLog`.
8. The structured response is returned to the frontend for display.

This matters because it means the user-facing chat is not ephemeral. Every important step is translated into stored session state and evaluable history.

## Authentication and authorization

DentAI now uses environment-backed JWT configuration rather than a hardcoded secret.

- JWT signing secret is read from `DENTAI_SECRET_KEY`.
- Access token TTL is controlled by `DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES`.
- Auth payloads carry `user_id`, `role`, and `display_name`.
- Protected routes resolve an `AuthenticatedUser` context from the token.
- Route-level role guards enforce access for student, instructor, and admin paths.

This is a meaningful step up from the older flat student-only auth approach because the platform now has explicit authorization boundaries for operational and instructional features.

## Data and persistence model

DentAI stores more than basic chat history. The database layer now models the operational state of the platform:

- `users` stores application identities, roles, and archive status
- `student_sessions` stores per-case progress and persisted scenario state
- `chat_logs` stores user and assistant messages plus evaluation metadata
- `exam_results` stores completed assessment outcomes
- `feedback_logs` stores post-session learner feedback
- `case_definitions` stores DB-backed case content for managed publishing flows
- `case_publish_history` stores versioned publish snapshots
- `recommendation_snapshots` stores explainable recommendation decisions
- `coach_hints` stores per-session coaching interventions
- `validator_audit_log` stores validator and safety audit traces

This schema supports both direct product behavior and later analysis. It is not only a chat transcript store.

## Scenario state model

The scenario manager maintains persistent case state rather than recalculating context from scratch on each request. A state object can include:

- active `case_id`
- patient context
- revealed findings
- case category
- case difficulty
- action history
- current score
- completion flags

This is the mechanism that allows a case to behave like a progression system. Findings can remain hidden until a student earns or triggers them, and the session can continue across multiple requests without losing educational context.

## AI interpretation layer

The agent layer is responsible for converting a free-text learner message into structured intent. The model is prompted to classify whether input is ordinary chat or a clinically meaningful action, normalize the action into a backend-friendly key, identify intent category, and return concise explanatory feedback.

This design is important because it lets the interface stay natural while keeping the rest of the backend strict. The system does not require students to learn a command language, but it still reduces their input into canonical action identifiers that the rule engine can score.

## Rule engine and scoring

Rule evaluation is handled separately from AI interpretation. That separation is one of the stronger design decisions in the repository.

- scoring rules are loaded from `data/scoring_rules.json`
- rules are matched by `case_id` and normalized action key
- each matching rule can return score change, rule outcome, and state updates
- unrecognized actions fall back to an unscored result rather than corrupting state

This means educational scoring remains inspectable and editable. The model can help interpret language, but it is not the final authority for scoring.

## Analytics and telemetry

DentAI records enough structured data to support both learner feedback and operational monitoring.

Current analytics-related behavior includes:

- tracking session scores over time
- extracting interpreted actions from assistant metadata
- computing action-type usage and mean score
- generating recommendation text based on weakness patterns
- exporting actions, feedback, and sessions as CSV

The admin domain also surfaces higher-level operational data such as service health, safety-flag counts, and prompt-injection pattern counts in user messages.

## Recommendation engine

The recommendation system is not generic content ranking. It is tied to educational signals.

- it uses prior session and result history
- it checks weak competency overlap against case competency tags
- it adjusts ranking based on completed versus unattempted work
- it records recommendation snapshots for auditability

This is a useful design choice because recommendations can later be explained, inspected, and traced back to stored inputs rather than remaining opaque model suggestions.

## Instructor and admin domains

The platform has moved beyond a student-only tool.

Instructor endpoints support:

- overview summaries of students
- weak competency inspection
- session drilldown
- safety-flag visibility
- recommendation spotlighting for students

Admin endpoints support:

- user creation and role updates
- soft-archive behavior for accounts
- case creation and updates
- case publishing history
- scoring rule updates
- runtime health inspection

That shifts DentAI from a prototype simulator toward a platform with actual operational surfaces.

## Frontend integration

The frontend communicates with the backend through a centralized Axios client in `frontend/lib/api.ts`.

Key behaviors in the client layer include:

- configurable base URL through `NEXT_PUBLIC_API_URL`
- automatic bearer token attachment
- automatic cleanup of local auth state on `401`
- typed wrappers for student, instructor, admin, recommendation, analytics, feedback, and quiz APIs

This is relevant because the frontend is not just rendering pages. It already has a defined contract layer for multiple product roles.

## Runtime configuration

The current codebase expects several runtime configuration values:

- `GEMINI_API_KEY` for primary LLM-backed interpretation
- `HUGGINGFACE_API_KEY` for MedGemma-related service availability checks
- `DENTAI_SECRET_KEY` for JWT signing
- `DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES` for auth token lifetime
- `DENTAI_DATABASE_URL` for database location override
- `NEXT_PUBLIC_API_URL` for frontend-to-backend routing

These are not optional in the same way. For example, JWT configuration is validated at API startup, while some AI-related services degrade more gracefully.

## Engineering constraints and current tradeoffs

The current implementation has a few practical tradeoffs that are worth stating explicitly:

- SQLite is simple for local development and research workflows, but it will become a concurrency bottleneck under heavier multi-user deployment.
- Some case content still exists in JSON files while newer admin workflows assume DB-backed case definitions, so the content model is in transition.
- There are legacy traces from earlier versions of the project, which means not every part of the repository is equally current.
- The system depends on model interpretation quality for action normalization, so prompt quality and fallback behavior remain important.

These are not blockers, but they are real constraints and they matter when evaluating the current maturity of the system.

## Short technical note

DentAI is implemented with a Python backend and a Next.js frontend. The backend handles case logic, authentication, session persistence, evaluation, recommendations, instructor/admin tooling, and analytics. The frontend provides the user-facing experience for login, case selection, chat interaction, statistics, quizzes, and role-based navigation.
