# 🚀 Jarvis AGI Roadmap: From "Assistant" to "General Agent"

> "How to surpass Xiao Ai?" -> Stop matching keywords, start **Reasoning**.

## 📊 Status Assessment (Current)
| Dimension | Xiao Ai (Xiaomi) | Jarvis (Current) | General Agent (Goal) |
|-----------|------------------|------------------|----------------------|
| **Core Brain** | Intent/Slot Filling (NLP) | **Regex/Keyword Matching** | **LLM Reasoning (GPT/Gemini)** |
| **Memory** | User Profile (Basic) | **Keyword Search** | **Vector Database (Semantic)** |
| **Control** | IoT Command | **Local Scripting** | **Autonomous Tool Use** |
| **Growth** | Static Updates | **Feedback Loop (Phase 5)** | **Self-Evolution** |
| **Authenticity**| Filtered/Corporate | **100% Real (Phase 6)** | **Truth-Seeking** |

> **Verdict**: Jarvis is currently a "Smart Automation Bot". It is robust and authentic, but lacks the "Cognitive Brain" to understand complex, ambiguous instructions like "Plan a weekend trip for me" without hardcoded regex.

---

## 🗺️ The Path to AGI (Phase 8+)

To surpass Xiao Ai, we must replace the "Regex Brain" with a "Cognitive Brain".

### Phase 8: Cognitive Brain (The "Spark") 🧠
**Backend**: **Doubao (Volcengine)** - Verified availability.
- [ ] **Integration**: Use `jarvis_doubao.py` as reference.
- [ ] **LLM Planner**: Replace `_extract_args` regex with Doubao API.
- [ ] **Complex Reasoning**: "Plan a trip to Shanghai" -> Breaks down into Weather, Flight, Hotel tools.
- [ ] **Function Calling**: Use Doubao's tool calling capability.

### Phase 9: Deep Memory (The "Soul") 📚
**Goal**: Remember *context*, not just keywords.
- [ ] **Vector Database**: Store conversations as vectors (ChromaDB/FAISS).
- [ ] **Context Retrieval**: "Remember what I said about my knee?" -> Retrieves medical context.

### Phase 10: Multimodality (The "Senses") 👁️
**Goal**: See and Hear interactively.
- [ ] **Vision**: Analyze screen/camera (Goal: "Watch this video and tell me when...").
- [ ] **Real Voice**: End-to-end voice loop (not text-to-speech).

---

## 🛠️ Immediate Action Plan (Phase 8)

1.  **Select LLM Backend**:
    -   Option A: Cloud (OpenAI/Gemini) - Smartest, Cost.
    -   Option B: Local (Ollama/Llama3) - Private, Free, Heavy on hardware.

2.  **Refactor `agent_core.py`**:
    -   Delete `_extract_args` (Regex).
    -   Implement `plan_with_llm(user_input, tools_schema)`.

3.  **Benefit**:
    -   User: "My throat hurts, get me something soothing."
    -   **Current Jarvis**: "Error: No keyword found."
    -   **Phase 8 Jarvis**: "Thinking... Throat hurts -> Need medicine/tea -> Search Web for 'soothing tea' -> Order via Meituan (if tool exists)."

---

**Recommendation**: Start Phase 8 immediately.
