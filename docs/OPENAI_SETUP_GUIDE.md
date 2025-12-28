# OpenAI Platform Setup Guide

## Step-by-Step: What to Select on OpenAI Platform

### 1. **Get Your API Key**

1. Go to: https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Name it: `MentraFlow Production` (or similar)
4. **Copy the key immediately** - you won't see it again!
5. Paste it into your `.env` file: `OPENAI_API_KEY=sk-...`

### 2. **Choose Your Models**

#### For Chat/LLM Operations (StudyChatAgent, FlashcardAgent, etc.)
- **Model**: `gpt-4o-mini` ✅ (Already configured)
- **Why**: Cost-effective, fast, great for most tasks
- **Cost**: $0.15/$0.60 per 1M tokens (input/output)
- **Location**: Already set in `.env` as `OPENAI_MODEL=gpt-4o-mini`

#### For Embeddings (Document Processing)
- **Model**: `text-embedding-3-small` ✅ (Now configured)
- **Why**: Perfect for 15-page PDFs, cost-effective
- **Cost**: $0.02 per 1M tokens
- **Location**: Set in `.env` as `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`

### 3. **API Access & Billing**

#### Enable API Access
1. Go to: https://platform.openai.com/account/billing
2. Add payment method (required for API access)
3. Set usage limits if desired (recommended for production)

#### Recommended Usage Limits
- **Hard Limit**: $100/month (adjust based on needs)
- **Soft Limit**: $50/month (warning threshold)
- **Rate Limits**: Default is usually fine for development

### 4. **What You DON'T Need to Select**

❌ **Don't need to select**:
- Fine-tuning (you're using base models)
- Custom models
- Assistants API (you're using direct API calls)
- Whisper (audio transcription - not needed)
- DALL-E (image generation - not needed)

✅ **What you're using**:
- Chat Completions API (for LLM agents)
- Embeddings API (for document embeddings)

### 5. **API Endpoints You'll Use**

#### Chat Completions (for agents)
```
POST https://api.openai.com/v1/chat/completions
Model: gpt-4o-mini
```

#### Embeddings (for documents)
```
POST https://api.openai.com/v1/embeddings
Model: text-embedding-3-small
```

### 6. **Cost Estimation for Your Use Case**

**15-page PDF processing:**
- Embeddings: ~10,000 tokens × $0.02/1M = **$0.0002 per document**
- Chat queries: ~500 tokens × $0.15/1M = **$0.000075 per query**

**Monthly estimate (100 documents, 1000 queries):**
- Embeddings: 100 × $0.0002 = **$0.02**
- Chat: 1000 × $0.000075 = **$0.075**
- **Total: ~$0.10/month** (very affordable!)

### 7. **Security Best Practices**

1. ✅ **Never commit `.env` file** (already in `.gitignore`)
2. ✅ **Use environment variables** (already configured)
3. ✅ **Rotate API keys** periodically
4. ✅ **Set usage limits** on OpenAI dashboard
5. ✅ **Monitor usage** at https://platform.openai.com/usage

### 8. **Testing Your Setup**

After adding your API key to `.env`, test with:

```python
# Test embedding
from openai import OpenAI
client = OpenAI(api_key="your-key")
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="test text"
)
print(f"Dimensions: {len(response.data[0].embedding)}")  # Should be 1536
```

### 9. **Troubleshooting**

**"Insufficient quota" error:**
- Add payment method at https://platform.openai.com/account/billing

**"Invalid API key" error:**
- Check key is correct in `.env`
- Ensure no extra spaces
- Regenerate key if needed

**Rate limit errors:**
- Default: 3,500 requests/minute for gpt-4o-mini
- Default: 1,000,000 tokens/minute for embeddings
- Should be fine for your use case

---

## Quick Checklist

- [ ] Created API key at https://platform.openai.com/api-keys
- [ ] Added key to `.env` file: `OPENAI_API_KEY=sk-...`
- [ ] Added payment method at https://platform.openai.com/account/billing
- [ ] Set usage limits (optional but recommended)
- [ ] Verified `.env` has both `OPENAI_MODEL` and `OPENAI_EMBEDDING_MODEL`
- [ ] Tested connection (optional)

---

**You're all set!** Your configuration is ready:
- ✅ `OPENAI_MODEL=gpt-4o-mini` (for chat/LLM)
- ✅ `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` (for embeddings)

