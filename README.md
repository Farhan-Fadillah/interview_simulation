# 🎯 AI Business Simulation Interviewer

> An intelligent, AI-powered interview simulation platform designed to evaluate the problem-solving capabilities of prospective bootcamp candidates — complete with real-time analytics and generative HR insights.

---

## 📌 Business Overview

**AI Business Simulation Interviewer** is a full-stack AI application built for **Alumni** — an online technology bootcamp platform with over 50,000 alumni across five major cities in Indonesia. The platform addresses a critical bottleneck in the candidate selection process: conducting consistent, scalable, and objective business simulation interviews.

<img width="1184" height="663" alt="image" src="https://github.com/user-attachments/assets/ee3f92db-da0c-4f4d-bcf7-bc145893e3e5" />

Traditional interview processes are resource-intensive, prone to interviewer bias, and difficult to scale when candidate volume is high. This application replaces or augments the human interviewer in the initial screening phase by deploying a **GPT-4o-powered AI interviewer** that dynamically challenges candidates with real-world business scenarios, probes shallow answers, and applies deliberate pressure tests — all while maintaining a professional and structured interview experience.

<img width="1181" height="666" alt="image" src="https://github.com/user-attachments/assets/3262871d-323f-47b0-b127-c39335b30feb" />

All session data, including per-turn responses, sentiment signals, and final evaluation scores, are persisted to a **Supabase** (PostgreSQL) backend, enabling rich retrospective analysis through a dedicated **Analytics Dashboard** built directly into the app.

---

## 💡 Project Significance and Benefits

| Stakeholder | Key Benefit |
|---|---|
| **HR / Admissions Team** | Eliminates the need for a human interviewer in initial screening rounds, drastically reducing time-to-decision |
| **Candidates** | Receives a consistent, fair, and structured interview experience regardless of when they apply |
| **Program Managers** | Gains data-driven, aggregated cohort insights to identify skill gaps and design targeted training programs |
| **Leadership / CHRO** | Accesses AI-generated strategic talent intelligence to support workforce planning and curriculum design |

### Quantifiable Benefits

- **Scalability** — Capable of running hundreds of interview sessions simultaneously without additional human resources.
- **Consistency** — Every candidate is evaluated against the same rubric, eliminating variance introduced by individual interviewers.
- **Speed** — Real-time scoring and tier recommendations are generated immediately upon session completion.
- **Data Richness** — Every turn (question-answer pair) is stored with sentiment analysis, probing flags, and interview state metadata, enabling granular post-session analysis.
- **Cost Efficiency** — Reduces the operational cost of the initial screening phase while maintaining evaluation quality.

---

## 🌟 Why This Project Matters

The intersection of **Generative AI and Human Resources** is one of the most impactful frontiers in enterprise technology today. This project is a direct, production-oriented embodiment of that intersection.

<img width="1181" height="664" alt="image" src="https://github.com/user-attachments/assets/4cfb5b34-6b27-4f78-9356-11c5c9fccf0d" />

### The Problem It Solves

Bootcamp admissions teams frequently face a trilemma: they must evaluate candidates **quickly**, **fairly**, and **deeply**. Achieving all three simultaneously with human interviewers is extremely difficult — especially as applicant volume grows. Rushed interviews lead to poor hiring decisions; slow processes cause high drop-off rates among qualified candidates.

### The Solution It Delivers

This platform resolves the trilemma by deploying an AI interviewer that:

- **Thinks before it asks** — The LLM internally evaluates each candidate response before deciding the next question, mirroring the thought process of a senior manager.
- **Adapts dynamically** — It escalates to probing follow-ups when answers are vague, and injects deliberate pressure tests (e.g., zero-budget scenarios, tight deadlines) to stress-test candidate thinking under constraints.
- **Scores objectively** — Upon session completion, the AI generates a structured evaluation across four competency dimensions, producing a transparent, auditable result.
- **Learns at the cohort level** — The analytics layer enables HR teams to discover systemic patterns across all candidates, not just individual results.

This project demonstrates that AI can be a genuinely transformative tool in talent acquisition — not as a gimmick, but as a rigorous, data-grounded assessment instrument.

---

## 🔄 Project Flow Overview

The application is organized into two primary functional areas that together create a complete talent evaluation pipeline:

```
┌─────────────────────────────────────────────────────┐
│              CANDIDATE-FACING LAYER                  │
│          AI Business Simulation Interviewer          │
│  [Setup Form] → [Chat Interface] → [Final Scoring]  │
└────────────────────────┬────────────────────────────┘
                         │ Persists sessions & turns
                         ▼
┌─────────────────────────────────────────────────────┐
│                  DATA LAYER                          │
│              Supabase (PostgreSQL)                   │
│     sessions table ←→ turns table (FK: session_id)  │
└────────────────────────┬────────────────────────────┘
                         │ Reads aggregated data
                         ▼
┌─────────────────────────────────────────────────────┐
│               HR-FACING LAYER                        │
│            Analytics Dashboard                       │
│  [KPI Metrics] → [Charts] → [AI Strategic Insight]  │
└─────────────────────────────────────────────────────┘
```

---

## 🪜 Step-by-Step Flow

### Phase 1 — Session Initialization

1. The candidate navigates to the **Simulasi Interview** page via the sidebar.
2. They fill out a setup form providing their **name** and selecting an **interview topic** from three predefined business challenges relevant to Alumni's product:
   - *User acquisition strategy for an education platform*
   - *Free-to-paid (trial-to-paid) conversion optimization*
   - *Active user retention and engagement improvement*
3. Upon submission, a unique `session_id` (UUID) is generated and an **initial session record** is immediately written to the Supabase `sessions` table — this ensures all subsequent turn records can be properly linked via foreign key before the first question is even asked.
4. The system constructs a detailed **LLM conversation history**, injecting the selected topic and Alumni's company profile into the system prompt, then triggers the first API call to GPT-4o to generate the opening question.

### Phase 2 — Conversational Interview Loop

5. The AI interviewer opens the session with a contextual, topic-specific question rendered in the Streamlit chat interface.
6. The candidate types their answer in the chat input field. Upon submission:
   - The answer is immediately displayed in the chat.
   - A **sentiment analysis** call is made in parallel to GPT-4o to classify the response as `positive`, `neutral`, or `negative` with a confidence score.
   - The full conversation history (including all prior turns) is sent to GPT-4o, which returns a structured **JSON response object** containing the next question, internal evaluation signals, and interview state metadata.
7. The JSON response is parsed and the relevant fields are extracted:
   - `question` — the next interview question displayed to the candidate
   - `interviewer_note` — optional contextual hints displayed as a caption (e.g., "Type 'stop interview' when you are done")
   - `is_probing` — flags whether the AI detected a vague or insufficient answer requiring deeper exploration
   - `is_pressure_test` — flags whether the AI is deliberately applying a constraint-based challenge
   - `current_state` — tracks the interview phase: `opening → exploration → pressure_test → user_centricity → closing`
   - `question_number` — tracks the sequential position within the session (min: 5, max: 10 questions)
8. Each completed turn (question-answer pair) is persisted to the Supabase `turns` table with its full metadata, including sentiment scores, probing flags, and timestamp.
9. The loop continues until either:
   - The candidate types **"stop interview"**, or
   - The AI determines the evaluation is sufficiently complete and sets `stop_interview: true` in its response.

### Phase 3 — Evaluation & Scoring

10. Upon interview termination, the AI generates `final_scores` — a structured JSON object containing scores (1–5 scale) across four competency dimensions:
    - **Logical Structure** — clarity and coherence of reasoning
    - **Feasibility** — practicality and realism of proposed solutions
    - **User Centricity** — degree to which the candidate considers end-user impact
    - **Professional Tone** — quality of business communication and language
11. A `total_score` (sum of all dimensions, max 20) and a **tier recommendation** are computed:
    - **Tier 1 — Auto Pass**: Strong across all dimensions, clear strategic thinker
    - **Tier 2 — Conditional Pass**: Acceptable performance with identified development areas
    - **Tier 3 — Revise / Waitlist**: Insufficient performance requiring significant improvement
12. A 2–3 sentence qualitative `summary` of the candidate's overall performance is also generated.
13. The `sessions` table is updated (via `upsert`) with all final scores, tier recommendation, summary, and session end timestamp.
14. The candidate sees a success message and can choose to start a new session.

### Phase 4 — Analytics & HR Intelligence

15. HR personnel navigate to the **Analytics Dashboard** page.
16. All session records are fetched from Supabase and loaded into a Pandas DataFrame.
17. Multi-dimensional **filters** allow slicing the data by candidate name, interview topic, and tier result.
18. The dashboard presents four live **KPI metrics**: total sessions, pass rate (Tier 1 + 2), average total score, and completed sessions count.
19. Three **interactive charts** visualize the data:
    - Donut chart — distribution of tier recommendations
    - Horizontal bar chart — average score per competency dimension
    - Bar chart — session volume by interview topic
20. A detailed **session data table** lists all filtered candidates with their scores, tier, and timestamp.
21. The **AI Strategic Insight** module allows HR to trigger a generative analysis: the system aggregates filtered data (score distributions, tier splits, qualitative summaries) and sends it to GPT-4o, which responds as a Chief HR Officer (CHRO) persona — producing a cohort-level strategic analysis covering collective strengths, systemic weaknesses, and training recommendations.

---

## 🖥️ Streamlit App Features

### 🗣️ Simulasi Interview (Candidate Interface)

<img width="1919" height="420" alt="image" src="https://github.com/user-attachments/assets/45c25a72-ac1e-486a-9acb-c4c60905d98a" />

| Feature | Description |
|---|---|
| **Candidate Setup Form** | Collects name and interview topic before session begins |
| **Dynamic Chat Interface** | Native Streamlit `st.chat_message` UI for a natural conversation experience |
| **AI-Powered Interviewer** | GPT-4o generates contextually adaptive questions based on full conversation history |
| **Probing Logic** | AI automatically detects vague answers and escalates with deeper follow-up questions |
| **Pressure Test Injection** | One deliberate constraint scenario (zero budget, no data, tight deadline) is embedded mid-session |
| **Interviewer Notes** | Contextual guidance messages shown below AI responses (e.g., end-session hints) |
| **Session State Management** | Full conversation history and session metadata maintained in `st.session_state` across reruns |
| **Automatic Session Persistence** | Session and turn records written to Supabase in real-time throughout the interview |
| **Structured JSON Scoring** | Final evaluation delivered as a structured JSON object with per-dimension scores and tier |
| **New Session Reset** | One-click reset to clear all session state and restart a fresh interview |

### 📊 Analytics Dashboard (HR Interface)

<img width="1919" height="927" alt="image" src="https://github.com/user-attachments/assets/5415a3d6-6d0d-44a7-b09a-098d6f3297f1" />



| Feature | Description |
|---|---|
| **Multi-Field Filtering** | Filter sessions simultaneously by candidate name, interview topic, and tier result |
| **KPI Metrics Panel** | Four summary metrics: total sessions, pass rate, average score, completed count |
| **Tier Distribution (Donut Chart)** | Visualizes the proportion of Tier 1 / 2 / 3 recommendations across filtered sessions |
| **Competency Dimension Scores (Bar Chart)** | Horizontal bar chart showing average scores per dimension (max 5), making skill gaps immediately visible |
| **Topic Distribution (Bar Chart)** | Session volume broken down by interview topic, revealing demand and performance patterns per scenario |
| **Session Data Table** | Filterable tabular view of all candidate sessions with scores, tier, and date |
| **AI Strategic Insight (Generative Analytics)** | On-demand GPT-4o powered cohort analysis providing HR-level strategic recommendations based on filtered data |
| **Null-Safe Data Handling** | Graceful handling of incomplete sessions (e.g., candidates who did not finish) with appropriate fallback values |

---

## 🗄️ Database Schema (Supabase)

### `sessions` table

| Column | Type | Description |
|---|---|---|
| `session_id` | `uuid` (PK) | Unique identifier for each interview session |
| `candidate_name` | `text` | Name of the candidate |
| `interview_topic` | `text` | Selected business simulation topic |
| `company_profile` | `text` | Alumni company context injected into the AI prompt |
| `started_at` | `timestamptz` | Session start timestamp (UTC) |
| `ended_at` | `timestamptz` | Session end timestamp (UTC) |
| `total_questions` | `integer` | Number of questions asked in the session |
| `logical_structure` | `float` | Score dimension: logical reasoning (1–5) |
| `feasibility` | `float` | Score dimension: solution practicality (1–5) |
| `user_centricity` | `float` | Score dimension: end-user consideration (1–5) |
| `professional_tone` | `float` | Score dimension: communication quality (1–5) |
| `total_score` | `float` | Sum of all dimension scores (max 20) |
| `tier` | `text` | Final tier recommendation |
| `summary` | `text` | AI-generated qualitative evaluation summary |

### `turns` table

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` (PK) | Auto-generated unique turn identifier |
| `session_id` | `uuid` (FK → sessions) | Links turn to its parent session |
| `turn_number` | `integer` | Sequential position of this turn in the session |
| `question` | `text` | The AI interviewer's question for this turn |
| `answer` | `text` | The candidate's response |
| `is_probing` | `boolean` | Whether the AI applied a probing follow-up |
| `is_pressure_test` | `boolean` | Whether the AI applied a pressure test scenario |
| `current_state` | `text` | Interview phase at time of this turn |
| `sentiment_label` | `text` | Sentiment classification of the answer (`positive / neutral / negative`) |
| `sentiment_score` | `float` | Confidence score of sentiment classification (0.0–1.0) |
| `timestamp` | `timestamptz` | UTC timestamp of this turn |

---

## 🚀 Potential Future Enhancements

- **Voice Interface** — Integrate speech-to-text and text-to-speech APIs to enable a fully spoken interview experience.
- **Multilingual Support** — Extend the system prompt to support English-language interview sessions for international candidates.
- **Custom Rubric Builder** — Allow HR administrators to define custom competency dimensions and scoring weights via a configuration UI.
- **Candidate-Facing Report** — Generate a downloadable PDF scorecard for candidates upon session completion.
- **Longitudinal Tracking** — Track individual candidate performance across multiple sessions to measure improvement over time.
- **LLM Provider Abstraction** — Decouple from OpenAI to support alternative providers (Anthropic Claude, Google Gemini) via a unified API interface.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

Built for **Alumni** — empowering the next generation of Indonesian tech talent through data-driven, AI-augmented candidate evaluation.
