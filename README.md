# DentAI

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



