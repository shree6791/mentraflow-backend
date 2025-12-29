# Personalization & Search Optimization Guide

This document outlines personalization requirements for the learning retention system and when advanced techniques (QLoRA/LoRA, MMR) would be needed.

## Current Implementation Status

### ✅ Implemented

1. **Score Thresholds**
   - Default threshold: `0.7` (70% similarity minimum)
   - Filters low-quality results at Qdrant level
   - Configurable per search operation
   - Location: `app/core/constants.py` → `DEFAULT_SCORE_THRESHOLD`

2. **Payload Indexing**
   - Chunks collection: `workspace_id`, `document_id`, `chunk_id`, `user_id`, `created_at` (all indexed)
   - Concepts collection: `workspace_id`, `concept_id`, `concept_name`, `created_at` (all indexed)
   - Efficient filtering at database level
   - Location: `app/core/qdrant_collections.py` → `create_payload_indexes()`

---

## When You'd Need QLoRA/LoRA

### What They Are
- **QLoRA/LoRA**: Fine-tuning techniques for LLMs to adapt base models to specific domains or behaviors
- Used to customize model responses, not for semantic search

### When You'd Need Them

#### ✅ **Needed If:**
1. **Domain-Specific Language Understanding**
   - Medical terminology, legal jargon, highly technical fields
   - General models struggle with specialized vocabulary
   - Example: Medical students need precise anatomical terms

2. **Custom Response Styles**
   - Personalized explanation styles per user
   - "Explain like I'm 5" vs "Detailed technical explanation"
   - Custom formatting requirements

3. **Cost Optimization**
   - Replace expensive GPT-4 calls with smaller fine-tuned models
   - High-volume use cases where API costs are prohibitive

#### Not Needed If:
- ✅ General study materials (textbooks, notes, articles)
- ✅ Standard Q&A, summaries, flashcards work well
- ✅ Using OpenAI's general-purpose models effectively
- ✅ No domain-specific terminology issues

### Alternative: Prompt Engineering
Instead of fine-tuning, use **prompt engineering with user preferences**:
- Include user learning style in prompts
- Adjust explanation depth based on user profile
- Template-based responses for different styles
- **Simpler, more flexible, and easier to maintain**

---

## When You'd Need MMR (Maximal Marginal Relevance)

### What It Is
- **MMR**: Reranking technique that balances relevance and diversity
- Prevents redundant results from single queries
- Ensures diverse coverage of topics

### When You'd Need It

#### ✅ **Needed If:**
1. **Single-Query Scenarios with Redundancy**
   - User searches "machine learning" and gets 10 nearly identical chunks
   - Need diversity from one query instead of multiple queries
   - Example: General search across all documents

2. **Document Discovery/Search Features**
   - Users browse/search across entire knowledge base
   - Need diverse results to avoid showing same content repeatedly
   - Example: "Show me concepts related to neural networks" (want variety)

3. **Personalized Discovery**
   - "Show me diverse concepts I haven't mastered" (across multiple topics)
   - Mixed review sessions with diverse topics
   - Exploration mode for discovering new related concepts

#### Not Needed If:
- ✅ Using multiple semantic queries (already doing this for summaries/flashcards)
- ✅ Document-specific retrieval (filtering by `document_id`)
- ✅ Small result sets (top_k=8)
- ✅ Current multi-query approach provides sufficient diversity

### Alternative: Multiple Queries + Filtering
Your current approach is better for your use case:
- Multiple semantic queries for diversity (summary, flashcards already do this)
- Filter by user progress/mastery level
- Topic-based diversity logic
- **Simpler and more control**

---

## Personalization Requirements for Learning Retention

### High Priority (Core Features)

#### 1. **Spaced Repetition System**
**What:** Algorithm-based review scheduling based on forgetting curves

**Implementation:**
- Track review intervals per concept/flashcard
- Adjust intervals based on user performance (correct/incorrect)
- Algorithms: SM-2, FSRS, or custom implementation
- Store: `user_concept_review` table with:
  - `last_reviewed_at`
  - `next_review_at`
  - `ease_factor`
  - `interval_days`
  - `review_count`
  - `performance_history`

**Why:** Core to learning retention - ensures concepts are reviewed at optimal times

---

#### 2. **User Progress Tracking**
**What:** Track what users know/don't know, mastery levels

**Implementation:**
- Mastery level per concept (0-100% or 0-5 stars)
- Performance history (correct/incorrect counts)
- Knowledge gaps identification
- Store in: `user_concept_mastery` table with:
  - `mastery_level` (0.0-1.0)
  - `total_attempts`
  - `correct_attempts`
  - `last_practiced_at`
  - `strength_score` (calculated from performance)

**Why:** Enables adaptive content selection and personalized recommendations

---

#### 3. **Adaptive Content Selection**
**What:** Show content based on user's current state

**Implementation:**
- Filter flashcards/concepts by:
  - Difficulty level (match user's current ability)
  - Mastery level (prioritize weak areas)
  - Review schedule (spaced repetition)
- Balance new content vs review content
- Prioritize concepts user struggles with

**Why:** Maximizes learning efficiency by focusing on what needs work

---

#### 4. **Learning Analytics**
**What:** Track and analyze user learning patterns

**Implementation:**
- Retention rates per concept
- Concept difficulty analysis (how many users struggle)
- Personalized recommendations ("You should review X")
- Learning velocity tracking
- Store in: `user_learning_analytics` table

**Why:** Provides insights for both users and system optimization

---

### Medium Priority (Enhanced Features)

#### 5. **Multi-Modal Content (Spatial Learning)**
**What:** Support visual/spatial learning styles

**Implementation:**
- Diagrams, charts, visual aids
- 3D models for spatial concepts
- Interactive visualizations
- Image embeddings in Qdrant
- Store in: `concept_media` table with:
  - `concept_id`
  - `media_type` (diagram, 3d_model, video, etc.)
  - `media_url` or `media_data`

**Why:** Cognitive and spatial learning requires visual aids

---

#### 6. **Cognitive Load Management**
**What:** Adapt content presentation to avoid overwhelming users

**Implementation:**
- Chunk size adaptation (smaller chunks for struggling users)
- Interleaving different topics (prevent monotony)
- Rest periods between sessions
- Difficulty progression (easy → medium → hard)

**Why:** Prevents burnout and improves long-term retention

---

### Low Priority (Nice to Have)

#### 7. **Learning Style Adaptation**
**What:** Adjust content presentation to user's learning style

**Implementation:**
- Visual learners: More diagrams, spatial representations
- Auditory learners: Audio explanations, text-to-speech
- Kinesthetic: Interactive exercises, hands-on activities
- Store in: `user_preferences` table (already exists)
  - `learning_style` field
  - `preferred_content_format`

**Why:** Improves engagement and comprehension

---

## Implementation Roadmap

### Phase 1: Foundation (Current)
- ✅ Score thresholds for quality filtering
- ✅ Payload indexing for efficient queries
- ✅ Basic retrieval and search

### Phase 2: Core Personalization (Next)
1. **User Progress Tracking**
   - Create `user_concept_mastery` table
   - Track performance per concept
   - Calculate mastery levels

2. **Spaced Repetition**
   - Implement SM-2 or FSRS algorithm
   - Create `user_concept_review` table
   - Schedule reviews based on performance

3. **Adaptive Content Selection**
   - Filter flashcards by mastery level
   - Prioritize weak areas
   - Balance new vs review content

### Phase 3: Enhanced Features
4. **Learning Analytics**
   - Dashboard for user progress
   - Recommendations engine
   - Difficulty analysis

5. **Multi-Modal Content**
   - Image/diagram support
   - Spatial learning aids
   - Interactive visualizations

### Phase 4: Advanced (Future)
6. **Cognitive Load Management**
7. **Learning Style Adaptation**
8. **MMR** (if general search/discovery features added)

---

## Database Schema Suggestions

### New Tables Needed

```sql
-- User progress per concept
CREATE TABLE user_concept_mastery (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    concept_id UUID REFERENCES concepts(id),
    mastery_level FLOAT DEFAULT 0.0,  -- 0.0 to 1.0
    total_attempts INT DEFAULT 0,
    correct_attempts INT DEFAULT 0,
    last_practiced_at TIMESTAMP,
    strength_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(user_id, concept_id)
);

-- Spaced repetition scheduling
CREATE TABLE user_concept_review (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    concept_id UUID REFERENCES concepts(id),
    flashcard_id UUID REFERENCES flashcards(id),  -- Optional
    last_reviewed_at TIMESTAMP,
    next_review_at TIMESTAMP,
    ease_factor FLOAT DEFAULT 2.5,  -- SM-2 algorithm
    interval_days INT DEFAULT 1,
    review_count INT DEFAULT 0,
    performance_history JSONB,  -- Array of correct/incorrect
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(user_id, concept_id, flashcard_id)
);

-- Learning analytics
CREATE TABLE user_learning_analytics (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    concept_id UUID REFERENCES concepts(id),
    retention_rate FLOAT,  -- Percentage of correct answers over time
    average_response_time FLOAT,  -- Seconds
    difficulty_rating FLOAT,  -- User's perceived difficulty
    last_analyzed_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Concept media (for spatial learning)
CREATE TABLE concept_media (
    id UUID PRIMARY KEY,
    concept_id UUID REFERENCES concepts(id),
    media_type VARCHAR(50),  -- diagram, 3d_model, video, audio
    media_url TEXT,
    media_data JSONB,  -- For embedded data
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Updates to Existing Tables

```sql
-- Add to user_preferences table
ALTER TABLE user_preferences 
ADD COLUMN learning_style VARCHAR(50),  -- visual, auditory, kinesthetic
ADD COLUMN preferred_difficulty VARCHAR(20),  -- easy, medium, hard
ADD COLUMN daily_study_goal_minutes INT;
```

---

## Key Takeaways

### ✅ **Do Implement:**
1. Spaced repetition algorithms (SM-2, FSRS)
2. User progress/mastery tracking
3. Adaptive content filtering
4. Prompt engineering for personalization (not fine-tuning)
5. Learning analytics

### **Don't Implement (Yet):**
- ❌ QLoRA/LoRA - Use prompt engineering instead
- ❌ MMR - Multiple queries + filtering works better for your use case
- ❌ Fine-tuning - Not needed unless domain-specific issues arise

### **Consider Later:**
- MMR if you add general search/discovery features
- Fine-tuning if you need custom response styles that prompts can't achieve
- Multi-modal embeddings for spatial learning

---

## References

- **Spaced Repetition Algorithms:**
  - SM-2: SuperMemo 2 algorithm
  - FSRS: Free Spaced Repetition Scheduler (more modern)
  
- **Learning Retention Research:**
  - Ebbinghaus Forgetting Curve
  - Active Recall vs Passive Review
  - Interleaving vs Blocking

- **Cognitive Load Theory:**
  - Intrinsic, Extraneous, and Germane Load
  - Chunking strategies

---

**Last Updated:** 2025-01-XX  
**Status:** Planning Phase - Ready for implementation when personalization features are prioritized

