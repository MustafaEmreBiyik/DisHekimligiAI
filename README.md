# Dental Education

A dental education simulation system that uses Google's Gemini AI to provide interactive learning scenarios for dental students.

The system utilizes a **Hybrid AI Architecture**, combining the natural language understanding capabilities of Large Language Models (Google Gemini & Gemma) with a deterministic rule-based assessment engine to provide accurate, safe, and objective feedback.

## 🚀 Key Features

- **Interactive Clinical Scenarios:** Realistic patient simulations covering various pathology categories (Infectious, Neoplastic, Immunologic, etc.).
- **Hybrid Assessment Engine:**
  - **LLM Layer:** Interprets student intent and natural language inputs using Google Gemini.
  - **Rule Layer:** Scores actions against strict clinical protocols defined in JSON rules, ensuring objective grading.
- **MedGemma Validator:** A specialized module using the **Gemma-2-9b-it** model via Hugging Face to validate clinical decisions against safety protocols and contraindications.
- **Pathology Category Rules:** Strict validation logic for specific disease categories (e.g., checking for "Wickham striae" in Lichen Planus cases).
- **Streamlit Web Interface:** A modern, responsive UI for chat interactions and real-time feedback.

## 🛠 System Architecture

The application follows a modular architecture:

1.  **The Agent (`app/agent.py`):** Acts as the orchestrator. It receives raw student input, sends it to the LLM for interpretation (converting text to structured JSON), and passes the result to the assessment engine.
2.  **Assessment Engine (`app/assessment_engine.py`):** Compares the interpreted action against `scoring_rules.json`. It calculates scores and determines if specific scenario flags (e.g., "anamnesis_completed") should be triggered.
3.  **Scenario Manager (`app/scenario_manager.py`):** Manages the state of the simulation, tracking patient data, revealed findings, and student progress.
4.  **MedGemma Service (`app/services/med_gemma_service.py`):** A dedicated service for high-reasoning clinical validation, ensuring student actions do not violate safety constraints (e.g., prescribing NSAIDs to a patient with a peptic ulcer).

## 📋 Prerequisites

- **Python 3.8+**
- **Google Gemini API Key** (for the main chat agent)
- **Hugging Face API Key** (for the MedGemma validation service)

## 📦 Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/betuldanismaz/dentai.git
    cd dentai
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

Create a `.env` file in the root directory of the project. You can use the example below as a template:

```ini
# .env file
GEMINI_API_KEY=your_google_gemini_api_key_here
HUGGINGFACE_API_KEY=your_hugging_face_api_key_here
```
