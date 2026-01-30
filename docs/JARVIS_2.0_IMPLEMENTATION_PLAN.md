# Jarvis 2.0 Implementation Plan
## Full Duplex (Barge-in) + Long-term Memory

---

## Executive Summary

This document provides a complete, step-by-step implementation guide for two major Jarvis 2.0 features:

1. **Full Duplex Conversation (Barge-in)** - Allow users to interrupt Jarvis mid-speech
2. **Long-term Memory** - Remember conversations and user preferences across sessions

**Target Agent**: moltbot (or any AI coding assistant)  
**Estimated Effort**: 2-3 days per feature  
**Priority**: Full Duplex first (more impactful UX improvement)

---

# Part 1: Full Duplex Conversation (Barge-in)

## 1.1 Current Architecture Analysis

### Current Flow (Half-Duplex)
```
[User speaks] → [Wait for silence] → [ASR final] → [Agent thinks] → [TTS plays]
                                                                         ↓
                                                           [Mic MUTED during TTS]
                                                                         ↓
                                                              [TTS finishes]
                                                                         ↓
                                                              [Mic re-enabled]
```

**Problem**: User cannot interrupt. Must wait for TTS to finish.

### Target Flow (Full-Duplex)
```
[User speaks] → [ASR] → [Agent] → [TTS starts playing]
                                          ↓
                              [Mic STILL LISTENING via AEC]
                                          ↓
                         [User speaks again] → [VAD detects voice]
                                          ↓
                              [TTS IMMEDIATELY STOPS]
                                          ↓
                         [New ASR session starts]
```

**Key Insight**: AEC (Acoustic Echo Cancellation) is already implemented. We just need to:
1. Keep mic listening during TTS
2. Detect user's voice (not echo)
3. Stop TTS immediately when user interrupts

---

## 1.2 Implementation Steps

### Step 1: Modify AEC to Run Continuously

**File**: `jarvis_assistant/services/audio/aec.py`

**Current State**: AEC processes audio only during ACTIVE state.

**Required Change**: AEC should process audio ALWAYS, including during TTS playback.

```python
# BEFORE (in hybrid_jarvis.py)
if self.state == State.ACTIVE:
    cleaned_audio = self.aec.process(mic_audio, speaker_audio)

# AFTER
# Always process through AEC
cleaned_audio = self.aec.process(mic_audio, speaker_audio)
```

**Validation**:
1. Play TTS audio
2. Speak into mic during TTS
3. Check if AEC output contains only user voice (not TTS echo)

---

### Step 2: Implement Barge-in VAD (Voice Activity Detection)

**New File**: `jarvis_assistant/services/audio/barge_in_detector.py`

```python
"""
Barge-in Detector - Detects user voice during TTS playback

This module monitors AEC-cleaned audio during TTS playback.
When user voice is detected, it signals to stop TTS immediately.
"""

import numpy as np
from collections import deque
import time

class BargeInDetector:
    """
    Detects user voice during TTS playback using energy + ZCR.
    
    Key Design Decisions:
    1. Uses short-term energy (not just amplitude) for robustness
    2. Requires 100ms of sustained voice to avoid false triggers
    3. Has a 500ms cooldown after TTS starts to avoid self-triggering
    """
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 energy_threshold: float = 0.01,
                 sustained_ms: int = 100,
                 cooldown_ms: int = 500):
        """
        Args:
            sample_rate: Audio sample rate (16000 for our system)
            energy_threshold: Energy level to consider as voice (tune this!)
            sustained_ms: How long voice must be present to trigger
            cooldown_ms: Ignore input for this long after TTS starts
        """
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.sustained_samples = int(sample_rate * sustained_ms / 1000)
        self.cooldown_samples = int(sample_rate * cooldown_ms / 1000)
        
        # Rolling buffer for energy tracking
        self.energy_buffer = deque(maxlen=self.sustained_samples)
        
        # State
        self.tts_start_time = None
        self.enabled = False
        
    def on_tts_start(self):
        """Call this when TTS playback begins"""
        self.tts_start_time = time.time()
        self.enabled = True
        self.energy_buffer.clear()
        
    def on_tts_stop(self):
        """Call this when TTS playback ends"""
        self.enabled = False
        self.tts_start_time = None
        
    def process(self, audio_chunk: np.ndarray) -> bool:
        """
        Process AEC-cleaned audio chunk.
        
        Args:
            audio_chunk: numpy array of int16 audio samples
            
        Returns:
            True if barge-in detected, False otherwise
        """
        if not self.enabled:
            return False
            
        # Cooldown check
        if self.tts_start_time:
            elapsed_ms = (time.time() - self.tts_start_time) * 1000
            if elapsed_ms < self.cooldown_samples / self.sample_rate * 1000:
                return False
        
        # Calculate short-term energy
        audio_float = audio_chunk.astype(np.float32) / 32768.0
        energy = np.sqrt(np.mean(audio_float ** 2))
        
        # Add to rolling buffer
        self.energy_buffer.append(energy)
        
        # Check if sustained voice detected
        if len(self.energy_buffer) >= self.sustained_samples // 160:  # 160 samples per chunk
            avg_energy = np.mean(self.energy_buffer)
            if avg_energy > self.energy_threshold:
                print(f"🎤 [BARGE-IN] User voice detected! (energy={avg_energy:.4f})")
                return True
                
        return False
```

---

### Step 3: Integrate Barge-in into HybridJarvis

**File**: `jarvis_assistant/core/hybrid_jarvis.py`

**Location**: Add to `__init__` method (around line 250)

```python
# Add import at top of file
from jarvis_assistant.services.audio.barge_in_detector import BargeInDetector

# In __init__
self.barge_in_detector = BargeInDetector(
    sample_rate=16000,
    energy_threshold=0.01,  # TUNE THIS VALUE
    sustained_ms=100,
    cooldown_ms=500
)
```

**Location**: Modify speaker worker (around line 1600)

```python
# In _speaker_worker, when starting TTS playback:
self.barge_in_detector.on_tts_start()

# When TTS finishes or is interrupted:
self.barge_in_detector.on_tts_stop()
```

**Location**: Modify mic reader loop (around line 1200)

```python
# In mic reading loop, ALWAYS process through barge-in detector
if self.barge_in_detector.enabled:
    # Get AEC-cleaned audio
    cleaned_audio = self.aec.process(mic_audio, speaker_audio)
    
    # Check for barge-in
    if self.barge_in_detector.process(cleaned_audio):
        # STOP TTS IMMEDIATELY
        self._stop_tts_playback()
        
        # Start new listening session
        self._transition_to(State.ACTIVE, reason="barge_in")
        
        # Clear any pending TTS
        while not self.speaker_queue.empty():
            self.speaker_queue.get_nowait()
```

---

### Step 4: Implement TTS Stop Function

**File**: `jarvis_assistant/core/hybrid_jarvis.py`

**New Method** (add around line 1800):

```python
def _stop_tts_playback(self):
    """
    Immediately stop TTS playback for barge-in.
    
    This is called when user interrupts Jarvis.
    """
    print("🛑 [BARGE-IN] Stopping TTS playback!")
    
    # 1. Clear speaker queue
    while not self.speaker_queue.empty():
        try:
            self.speaker_queue.get_nowait()
        except:
            break
    
    # 2. Signal TTS client to stop
    if hasattr(self, 'tts_v1') and self.tts_v1:
        asyncio.create_task(self.tts_v1.stop())
    
    # 3. Reset audio state
    self.self_speaking_mute = False
    self.barge_in_detector.on_tts_stop()
    
    # 4. If using S2S, send interrupt signal
    if self.skip_cloud_response:
        # Already suppressed, just start new session
        pass
    else:
        # May need to reset S2S session
        asyncio.create_task(self._reset_cloud_session())
```

---

### Step 5: Add TTS Stop to DoubaoTTSV1

**File**: `jarvis_assistant/services/doubao/tts_v3.py`

**Add Method** (around line 200):

```python
async def stop(self):
    """Stop current TTS synthesis immediately"""
    print("🔇 [TTS V1] Stopping synthesis")
    
    # Set flag to stop receiving audio
    self._stop_requested = True
    
    # Close current synthesis task if running
    if hasattr(self, '_current_task') and self._current_task:
        self._current_task.cancel()
        
    # Audio will stop when speaker queue drains
```

---

### Step 6: Testing & Tuning

#### Test 1: Basic Barge-in
```bash
./venv/bin/python3 main.py
# 1. Say "Hey Jarvis, tell me a long story"
# 2. Wait for TTS to start
# 3. Say "Stop!" or "Next"
# Expected: TTS stops immediately, Jarvis listens to new command
```

#### Test 2: Energy Threshold Tuning
```python
# Create test script: tests/test_barge_in.py

import numpy as np
from jarvis_assistant.services.audio.barge_in_detector import BargeInDetector

def test_threshold():
    detector = BargeInDetector(energy_threshold=0.005)  # Try different values
    
    # Test with silence
    silence = np.zeros(160, dtype=np.int16)
    assert not detector.process(silence), "Should not trigger on silence"
    
    # Test with speech
    speech = np.random.randint(-5000, 5000, 160, dtype=np.int16)
    detector.on_tts_start()
    
    # Process multiple chunks to exceed sustained_ms
    for _ in range(20):
        result = detector.process(speech)
    
    assert result, "Should trigger on sustained speech"
    print("✅ Barge-in detector test passed!")

if __name__ == "__main__":
    test_threshold()
```

#### Tuning Parameters
| Parameter | Default | Description | Tune If... |
|-----------|---------|-------------|------------|
| `energy_threshold` | 0.01 | Voice detection sensitivity | False triggers → increase; Missed → decrease |
| `sustained_ms` | 100 | How long voice must persist | False triggers → increase |
| `cooldown_ms` | 500 | Ignore input after TTS starts | Self-triggering → increase |

---

## 1.3 Barge-in Feature Checklist

- [ ] Create `barge_in_detector.py`
- [ ] Add import to `hybrid_jarvis.py`
- [ ] Initialize detector in `__init__`
- [ ] Call `on_tts_start()` when TTS begins
- [ ] Call `on_tts_stop()` when TTS ends
- [ ] Process audio through detector during TTS
- [ ] Implement `_stop_tts_playback()` method
- [ ] Add `stop()` method to `tts_v3.py`
- [ ] Create test script
- [ ] Tune energy threshold
- [ ] Test end-to-end barge-in

---

# Part 2: Long-term Memory

## 2.1 Architecture Design

### Memory Types
1. **Episodic Memory**: Specific conversations and events
2. **Semantic Memory**: Facts about user (preferences, habits)
3. **Procedural Memory**: How to do things (currently in tools)

### Storage Strategy
```
┌─────────────────────────────────────────────┐
│              ChromaDB (Vector Store)        │
│  ┌───────────────┐  ┌───────────────────┐  │
│  │ Conversations │  │ User Preferences  │  │
│  │  (Episodic)   │  │    (Semantic)     │  │
│  └───────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────┘
                      ↓
              Embedding Model
          (text-embedding-ada-002 or local)
                      ↓
              Query: "What's my usual order?"
                      ↓
              Top-K Relevant Memories
                      ↓
              Injected into Agent Context
```

---

## 2.2 Implementation Steps

### Step 1: Install Dependencies

**File**: `jarvis_assistant/requirements.txt`

Add:
```
chromadb>=0.4.0
sentence-transformers>=2.2.0  # For local embeddings
```

Install:
```bash
cd /Users/kaijimima1234/Desktop/jarvis
./venv/bin/pip install chromadb sentence-transformers
```

---

### Step 2: Create Memory Manager

**New File**: `jarvis_assistant/core/long_term_memory.py`

```python
"""
Long-term Memory Manager for Jarvis

Provides:
1. Conversation storage and retrieval
2. User preference learning
3. Semantic search over past interactions

Storage: ChromaDB (local vector database)
Embeddings: sentence-transformers (runs locally)
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Memory storage path
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "memory")


class MemoryEntry:
    """Represents a single memory entry"""
    
    def __init__(self, 
                 content: str,
                 memory_type: str,  # "conversation", "preference", "fact"
                 timestamp: float = None,
                 metadata: dict = None):
        self.content = content
        self.memory_type = memory_type
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}
        
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class LongTermMemory:
    """
    Main memory manager class.
    
    Usage:
        memory = LongTermMemory()
        
        # Store a conversation
        memory.add_conversation("User asked about Tesla stock", "It was $420")
        
        # Store a preference
        memory.add_preference("coffee", "User prefers iced americano")
        
        # Retrieve relevant memories
        memories = memory.search("What coffee does the user like?", k=3)
    """
    
    def __init__(self, persist_dir: str = None):
        """
        Initialize memory manager.
        
        Args:
            persist_dir: Directory to store ChromaDB data
        """
        self.persist_dir = persist_dir or MEMORY_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        
        print(f"🧠 [MEMORY] Initializing long-term memory at: {self.persist_dir}")
        
        # Initialize embedding model (runs locally)
        print("🧠 [MEMORY] Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.persist_dir,
            anonymized_telemetry=False
        ))
        
        # Create collections
        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            metadata={"description": "Conversation history"}
        )
        
        self.preferences = self.client.get_or_create_collection(
            name="preferences", 
            metadata={"description": "User preferences and facts"}
        )
        
        # Load statistics
        conv_count = self.conversations.count()
        pref_count = self.preferences.count()
        print(f"🧠 [MEMORY] Loaded {conv_count} conversations, {pref_count} preferences")
        
    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text"""
        return self.embedder.encode(text).tolist()
        
    def add_conversation(self, 
                         user_query: str, 
                         assistant_response: str,
                         tools_used: List[str] = None):
        """
        Store a conversation exchange.
        
        Args:
            user_query: What the user said
            assistant_response: What Jarvis responded
            tools_used: List of tools that were invoked
        """
        # Create summary for embedding
        summary = f"User: {user_query}\nJarvis: {assistant_response[:200]}"
        
        # Generate unique ID
        doc_id = f"conv_{int(time.time() * 1000)}"
        
        # Store in ChromaDB
        self.conversations.add(
            documents=[summary],
            embeddings=[self._embed(summary)],
            metadatas=[{
                "user_query": user_query,
                "response_preview": assistant_response[:500],
                "tools_used": json.dumps(tools_used or []),
                "timestamp": time.time(),
                "date": datetime.now().isoformat()
            }],
            ids=[doc_id]
        )
        
        print(f"🧠 [MEMORY] Stored conversation: {user_query[:50]}...")
        
        # Persist to disk
        self.client.persist()
        
    def add_preference(self, 
                       category: str, 
                       preference: str,
                       source: str = "inferred"):
        """
        Store a user preference or fact.
        
        Args:
            category: Category of preference (e.g., "food", "music", "work")
            preference: The actual preference
            source: How this was learned ("stated", "inferred")
        """
        doc_id = f"pref_{category}_{int(time.time())}"
        
        self.preferences.add(
            documents=[preference],
            embeddings=[self._embed(preference)],
            metadatas=[{
                "category": category,
                "source": source,
                "timestamp": time.time(),
                "date": datetime.now().isoformat()
            }],
            ids=[doc_id]
        )
        
        print(f"🧠 [MEMORY] Stored preference [{category}]: {preference[:50]}...")
        self.client.persist()
        
    def search(self, 
               query: str, 
               k: int = 5,
               memory_type: str = "all") -> List[Dict]:
        """
        Search for relevant memories.
        
        Args:
            query: Search query
            k: Number of results to return
            memory_type: "conversation", "preference", or "all"
            
        Returns:
            List of memory dicts with content and metadata
        """
        results = []
        query_embedding = self._embed(query)
        
        if memory_type in ["conversation", "all"]:
            conv_results = self.conversations.query(
                query_embeddings=[query_embedding],
                n_results=min(k, self.conversations.count()) if self.conversations.count() > 0 else 1
            )
            
            if conv_results and conv_results['documents']:
                for i, doc in enumerate(conv_results['documents'][0]):
                    results.append({
                        "type": "conversation",
                        "content": doc,
                        "metadata": conv_results['metadatas'][0][i],
                        "distance": conv_results['distances'][0][i] if conv_results.get('distances') else 0
                    })
        
        if memory_type in ["preference", "all"]:
            if self.preferences.count() > 0:
                pref_results = self.preferences.query(
                    query_embeddings=[query_embedding],
                    n_results=min(k, self.preferences.count())
                )
                
                if pref_results and pref_results['documents']:
                    for i, doc in enumerate(pref_results['documents'][0]):
                        results.append({
                            "type": "preference",
                            "content": doc,
                            "metadata": pref_results['metadatas'][0][i],
                            "distance": pref_results['distances'][0][i] if pref_results.get('distances') else 0
                        })
        
        # Sort by relevance (lower distance = more relevant)
        results.sort(key=lambda x: x.get('distance', 0))
        
        return results[:k]
    
    def get_context_for_query(self, query: str, max_tokens: int = 500) -> str:
        """
        Get formatted context string for Agent prompt.
        
        This is the main method to call before sending query to Agent.
        
        Args:
            query: User's current query
            max_tokens: Approximate max length of context
            
        Returns:
            Formatted string to inject into Agent system prompt
        """
        memories = self.search(query, k=5)
        
        if not memories:
            return ""
            
        context_parts = ["## Relevant Memories\n"]
        
        for mem in memories:
            if mem['type'] == 'preference':
                context_parts.append(f"- [Preference] {mem['content']}")
            else:
                context_parts.append(f"- [Past Conversation] {mem['content'][:200]}")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > max_tokens * 4:  # Approximate chars per token
            context = context[:max_tokens * 4] + "..."
            
        return context
    
    def extract_preferences_from_conversation(self, 
                                               user_query: str, 
                                               response: str) -> Optional[Dict]:
        """
        Automatically extract preferences from conversation.
        
        This uses simple pattern matching. For production, use LLM.
        
        Returns:
            Dict with category and preference if found, None otherwise
        """
        # Simple keyword-based extraction
        preference_patterns = [
            ("我喜欢", "preference", "stated"),
            ("我不喜欢", "dislike", "stated"),
            ("我通常", "habit", "stated"),
            ("我的", "personal", "stated"),
            ("记住", "reminder", "stated"),
            ("I like", "preference", "stated"),
            ("I prefer", "preference", "stated"),
        ]
        
        for pattern, category, source in preference_patterns:
            if pattern in user_query:
                return {
                    "category": category,
                    "preference": user_query,
                    "source": source
                }
                
        return None
```

---

### Step 3: Integrate Memory into Agent

**File**: `jarvis_assistant/core/agent.py`

**Add Import** (at top):
```python
from jarvis_assistant.core.long_term_memory import LongTermMemory
```

**Modify Agent Class**:

```python
class JarvisAgent:
    def __init__(self, ...):
        # Existing init code...
        
        # Initialize long-term memory
        self.memory = LongTermMemory()
        
    async def run(self, query: str) -> str:
        """
        Execute agent with memory-enhanced context.
        """
        # 1. Retrieve relevant memories
        memory_context = self.memory.get_context_for_query(query)
        
        # 2. Build enhanced system prompt
        system_prompt = self._build_system_prompt()
        if memory_context:
            system_prompt += f"\n\n{memory_context}"
        
        # 3. Execute agent logic (existing code)
        response = await self._execute(query, system_prompt)
        
        # 4. Store this conversation in memory
        self.memory.add_conversation(
            user_query=query,
            assistant_response=response,
            tools_used=self._get_used_tools()
        )
        
        # 5. Extract and store any preferences
        pref = self.memory.extract_preferences_from_conversation(query, response)
        if pref:
            self.memory.add_preference(
                category=pref['category'],
                preference=pref['preference'],
                source=pref['source']
            )
        
        return response
```

---

### Step 4: Add Memory to .gitignore

**File**: `.gitignore`

Add:
```
memory/
*.db
*.parquet
```

This prevents personal conversation history from being uploaded to GitHub.

---

### Step 5: Create Memory Test Script

**New File**: `tests/test_memory.py`

```python
#!/usr/bin/env python3
"""
Test script for Long-term Memory system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from jarvis_assistant.core.long_term_memory import LongTermMemory
import shutil

TEST_MEMORY_DIR = "/tmp/jarvis_test_memory"


def test_memory():
    # Clean up from previous test
    if os.path.exists(TEST_MEMORY_DIR):
        shutil.rmtree(TEST_MEMORY_DIR)
    
    print("\n" + "="*60)
    print("🧠 Long-term Memory Test")
    print("="*60 + "\n")
    
    # Initialize
    memory = LongTermMemory(persist_dir=TEST_MEMORY_DIR)
    
    # Test 1: Store conversation
    print("\n📝 Test 1: Storing conversations...")
    memory.add_conversation(
        user_query="What's Tesla stock price?",
        assistant_response="Tesla (TSLA) is currently at $420.69",
        tools_used=["get_stock_price"]
    )
    memory.add_conversation(
        user_query="What's the weather in Beijing?",
        assistant_response="Beijing weather: Cloudy, 5°C",
        tools_used=["get_weather"]
    )
    print("✅ Conversations stored")
    
    # Test 2: Store preference
    print("\n📝 Test 2: Storing preferences...")
    memory.add_preference(
        category="food",
        preference="User prefers iced americano coffee",
        source="stated"
    )
    memory.add_preference(
        category="music",
        preference="User likes classical music for focus",
        source="inferred"
    )
    print("✅ Preferences stored")
    
    # Test 3: Search
    print("\n🔍 Test 3: Searching memories...")
    
    results = memory.search("coffee", k=3)
    print(f"  Search 'coffee': Found {len(results)} results")
    for r in results:
        print(f"    - [{r['type']}] {r['content'][:50]}...")
    
    results = memory.search("stock price", k=3)
    print(f"\n  Search 'stock price': Found {len(results)} results")
    for r in results:
        print(f"    - [{r['type']}] {r['content'][:50]}...")
    
    # Test 4: Context generation
    print("\n📋 Test 4: Context generation...")
    context = memory.get_context_for_query("What coffee do I like?")
    print(f"  Generated context:\n{context}")
    
    print("\n" + "="*60)
    print("✅ All memory tests passed!")
    print("="*60 + "\n")
    
    # Cleanup
    shutil.rmtree(TEST_MEMORY_DIR)


if __name__ == "__main__":
    test_memory()
```

---

## 2.3 Memory Feature Checklist

- [ ] Install chromadb and sentence-transformers
- [ ] Create `long_term_memory.py`
- [ ] Add memory directory to `.gitignore`
- [ ] Integrate memory into Agent's `run()` method
- [ ] Create test script
- [ ] Test conversation storage
- [ ] Test preference extraction
- [ ] Test semantic search
- [ ] Test context injection into Agent

---

# Part 3: Testing Strategy

## 3.1 Unit Tests

| Test | File | What to Verify |
|------|------|----------------|
| Barge-in Detection | `tests/test_barge_in.py` | Energy threshold triggers correctly |
| Memory Storage | `tests/test_memory.py` | ChromaDB stores and retrieves |
| Memory Search | `tests/test_memory.py` | Semantic search returns relevant results |

## 3.2 Integration Tests

| Test | Description | How to Run |
|------|-------------|------------|
| Barge-in E2E | Interrupt Jarvis mid-speech | `python3 main.py` + speak during TTS |
| Memory E2E | Ask about past conversations | Query something discussed earlier |

## 3.3 Debugging Tips

### Barge-in Issues

**Problem**: False triggers (TTS keeps stopping)
- **Solution**: Increase `energy_threshold` or `cooldown_ms`

**Problem**: Can't interrupt (barge-in never triggers)
- **Solution**: Decrease `energy_threshold`, check AEC is working

**Problem**: Echo still present after AEC
- **Solution**: Check speaker/mic routing, increase AEC filter length

### Memory Issues

**Problem**: ChromaDB won't initialize
- **Solution**: Check disk space, permissions on memory directory

**Problem**: Irrelevant memories retrieved
- **Solution**: Tune embedding model, filter by recency

**Problem**: Memory grows too large
- **Solution**: Add pruning logic to delete old conversations

---

# Part 4: Implementation Order

## Recommended Sequence

1. **Week 1: Barge-in**
   - Day 1: Create barge-in detector class
   - Day 2: Integrate into HybridJarvis
   - Day 3: Add TTS stop capability
   - Day 4-5: Tune and test

2. **Week 2: Memory**
   - Day 1: Set up ChromaDB + embeddings
   - Day 2: Create memory manager
   - Day 3: Integrate into Agent
   - Day 4: Add preference extraction
   - Day 5: Test and tune

---

# Part 5: Files to Create/Modify

## New Files
| Path | Description |
|------|-------------|
| `jarvis_assistant/services/audio/barge_in_detector.py` | Barge-in detection logic |
| `jarvis_assistant/core/long_term_memory.py` | Memory manager |
| `tests/test_barge_in.py` | Barge-in unit test |
| `tests/test_memory.py` | Memory unit test |

## Files to Modify
| Path | Changes |
|------|---------|
| `jarvis_assistant/core/hybrid_jarvis.py` | Add barge-in integration |
| `jarvis_assistant/services/doubao/tts_v3.py` | Add stop() method |
| `jarvis_assistant/core/agent.py` | Add memory integration |
| `jarvis_assistant/requirements.txt` | Add chromadb, sentence-transformers |
| `.gitignore` | Add memory/ directory |

---

# Part 6: Success Criteria

## Barge-in Success
- [ ] User can say "stop" and TTS stops within 200ms
- [ ] No false triggers from TTS echo
- [ ] New command is correctly recognized after barge-in
- [ ] Works on both Mac and Raspberry Pi

## Memory Success
- [ ] Conversations are persisted across restarts
- [ ] User can reference past conversations naturally
- [ ] Preferences are automatically extracted and used
- [ ] Search returns semantically relevant results
- [ ] Memory doesn't leak to GitHub

---

# Appendix: Key Code Locations

| Feature | File | Line Range |
|---------|------|------------|
| AEC Processing | `hybrid_jarvis.py` | 1180-1220 |
| Mic Reader Loop | `hybrid_jarvis.py` | 1100-1300 |
| Speaker Worker | `hybrid_jarvis.py` | 1500-1700 |
| TTS Playback | `tts_v3.py` | 100-200 |
| Agent Run | `agent.py` | 50-150 |
| Agent Singleton | `hybrid_jarvis.py` | 237-246 |

---

**Document Version**: 1.0  
**Created**: 2026-01-30  
**Author**: Antigravity (for moltbot execution)

> **Note to moltbot**: Please read the existing `jarvis-development/SKILL.md` before implementing. It contains critical DO's and DON'Ts that must be followed.
