# Oral Pathology Assessment Platform

An AI-powered educational platform for clinical dental training, combining large medical language models with adaptive learning systems to deliver accurate, personalized diagnostic feedback across a comprehensive library of pathology cases.

---

## Architecture Overview

The platform follows a microservices architecture with clear separation between AI inference, session management, and learning analytics. The backend exposes a FastAPI REST layer backed by PostgreSQL, designed for low-latency inference and concurrent session handling across a student cohort.

```
┌─────────────────────────────────────────────────────────┐
│                    React / Next.js                       │
│              (Adaptive UI · Case Viewer)                 │
└────────────────────────┬────────────────────────────────┘
                         │ REST / WebSocket
┌────────────────────────▼────────────────────────────────┐
│                    FastAPI Gateway                       │
│   ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
│   │  AI Inference│  │   Session   │  │  Learning    │  │
│   │   Service    │  │  Manager    │  │  Analytics   │  │
│   └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  │
│          │                 │                 │          │
│   ┌──────▼─────────────────▼─────────────────▼───────┐  │
│   │                   PostgreSQL                      │  │
│   └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Core Components

### AI Diagnostic Engine

Integrates **MedGemma**, Google's medical-domain large language model, as the primary reasoning layer for clinical case evaluation. A deterministic validation wrapper enforces clinical correctness constraints before any model output reaches the student, preventing hallucinated diagnoses and ensuring feedback aligns with established pathology criteria.

- Structured prompting pipelines tailored to oral pathology taxonomies
- Confidence-gated response filtering using deterministic rule sets
- Multi-turn conversational reasoning to support differential diagnosis workflows

### Computer Vision Pipeline

Automated analysis of dental radiographs and intraoral clinical imagery using a dedicated vision module integrated into the inference service.

- Multi-modal input handling (periapical, panoramic, bitewing radiographs + clinical photos)
- Region-of-interest detection for lesion localization and measurement
- Instant annotated feedback overlaid on student-submitted imagery
- Supports diagnostic validation across caries staging, bone loss quantification, and soft-tissue pathology identification

### Adaptive Learning Engine

A two-layer prediction system combines classical psychometric modeling with modern machine learning to personalize case sequencing in real time.

**Layer 1 — Item Response Theory (IRT)**
- Estimates latent student ability (θ) and per-case difficulty, discrimination, and guessing parameters
- Continuously updates ability estimates after each case interaction using maximum likelihood estimation
- Drives next-case selection to maintain optimal challenge level targeted at the current ability estimate

**Layer 2 — Trajectory Prediction**
- LSTM network models temporal sequences of student performance to detect skill regression and plateau patterns
- XGBoost classifier predicts at-risk students based on engagement signals, error distributions, and session pacing
- Combined outputs feed a scheduler that adjusts case difficulty, category weighting, and hint availability per student

### Case Library

200+ clinical scenarios spanning the major oral pathology domains:

| Category | Coverage |
|---|---|
| Dental Caries | Incipient, cavitated, arrested, root caries |
| Periodontal Disease | Gingivitis, chronic/aggressive periodontitis, peri-implantitis |
| Oral Lesions | Benign mucosal lesions, potentially malignant disorders, reactive lesions |
| Periapical Pathology | Apical periodontitis, cysts, granulomas |
| Developmental Anomalies | Structural defects, eruption disorders |

Each case implements **progressive information disclosure** — clinical history, radiographic evidence, and examination findings are released incrementally, replicating the authentic decision-making cadence of a real clinical encounter. Students commit to a working diagnosis before additional data is unlocked, preventing anchoring on complete information.

### Backend Services

**FastAPI** serves as the primary API layer, chosen for its async-native I/O model and automatic OpenAPI schema generation.

- Async request handling for concurrent AI inference without thread blocking
- JWT-based authentication with role-differentiated access (student, instructor, admin)
- Session state persisted in PostgreSQL with transactional guarantees — partial progress is never lost
- Secure student progress tracking: raw response logs, time-on-task, hint usage, and attempt history stored per session and aggregated per student

### Frontend

Built with **React** and **Next.js**, the interface is purpose-designed for medical education workflows rather than adapted from a generic template.

- Server-side rendering for fast initial case load
- Component architecture separates case rendering, diagnostic input, radiograph viewer, and feedback panel — each independently updatable
- Radiograph viewer with pan/zoom, annotation overlay, and comparison mode (pre/post treatment)
- Accessibility-first design: keyboard navigation, WCAG 2.1 AA contrast compliance, screen-reader–compatible diagnostic forms
- Responsive layout supporting tablet use during simulated clinical rounds

---

## Data Model

```
students          ──< sessions ──< responses
cases             ──< case_media
cases             ──< case_findings (IRT parameters)
students          ──< ability_estimates (time-series)
students          ──< trajectory_predictions
```

Ability estimates are stored as time-series snapshots rather than a single scalar, enabling longitudinal analysis of student growth and regression detection.

---

## Technology Stack

| Layer | Technology |
|---|---|
| LLM | MedGemma (medical-domain fine-tune) |
| Vision | Custom CV pipeline (PyTorch) |
| Adaptive Engine | IRT · LSTM · XGBoost |
| Backend | FastAPI · Python 3.11 |
| Database | PostgreSQL 16 |
| Frontend | React 18 · Next.js 14 · TypeScript |
| Auth | JWT · bcrypt |
