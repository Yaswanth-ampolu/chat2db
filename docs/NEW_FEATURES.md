# Major Update - Dynamic Model Fetching & Fixed Errors

## 🎉 What's New

This update completely fixes the "error creating agent" issue and adds dynamic model fetching from AI provider APIs!

## 🐛 Critical Fixes

### 1. Fixed `bind_tools` Error
**Problem:** `'ChatGoogleGenerativeAI' object has no attribute 'bind_tools'`

**Root Cause:** Outdated langchain packages (v0.1.x) didn't have the `bind_tools` method

**Solution:**
- Updated all langchain packages to v0.2+ (requirements.txt)
- `langchain-google-genai`: 0.0.11 → 1.0.0+
- `langchain-openai`: 0.0.5 → 0.1.0+
- `langchain-anthropic`: 0.0.2 → 0.1.0+
- `langchain-core`: 0.1.16 → 0.2.0+
- `langgraph`: 0.0.20 → 0.2.0+

**Install updates:**
```bash
cd /home/yaswanth/programming/PinnacleAi/python/chat2sql
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## 🚀 New Features

### 1. Dynamic Model Fetching (api_models.py)

**New file:** `api_models.py` - Fetches available models directly from AI provider APIs

**Features:**
- ✅ Fetches real-time model list from Google Gemini API
- ✅ Fetches available models from OpenAI API
- ✅ Automatic fallback to known models if API fails
- ✅ Support for **ALL** Gemini models including:
  - `gemini-2.0-flash-exp` (latest experimental)
  - `gemini-2.0-flash-thinking-exp-01-21` (thinking model)
  - `gemini-exp-1206` (experimental Dec 2024)
  - `gemini-1.5-pro`, `gemini-1.5-pro-002`
  - `gemini-1.5-flash`, `gemini-1.5-flash-002`
  - `gemini-1.5-flash-8b` (lightweight)

**Usage:**
```python
from api_models import ModelFetcher

# Fetch Google models with API key
models = await ModelFetcher.fetch_google_models(api_key="your-key")

# Fetch all models for a provider
models = await ModelFetcher.fetch_all_models("google", api_key)
```

### 2. Configuration Management (config.py)

**New file:** `config.py` - Persistent configuration storage

**Features:**
- ✅ Saves API keys securely to `~/.chat2sql/config.json`
- ✅ Remembers last used provider and model
- ✅ Supports environment variables (`.env` file)
- ✅ Auto-loads saved settings on startup

**Usage:**
```python
from config import get_config

config = get_config()

# Save API key
config.set_api_key("google", "your-api-key")

# Get last used model
last_model = config.get_last_model("google")
```

**Environment variables supported:**
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### 3. Enhanced Models Modal (ui/modals.py)

**Improvements:**
- ✅ **Dynamic model loading** - Fetches real models from API
- ✅ **"Refresh Models" button** - Re-fetch with current API key
- ✅ **Auto-saves API keys** - No need to re-enter
- ✅ **Remembers last selection** - Auto-selects your favorite provider/model
- ✅ **Loading status** - Shows "Loading models..." and "✓ X models available"
- ✅ **Error resilience** - Falls back to known models if API fails

**How it works:**
1. Open `/models` command
2. Select provider (Google/OpenAI/Anthropic)
3. Enter API key (or auto-loads saved one)
4. Models fetch automatically from the API
5. See ALL available models (including experimental ones!)
6. Select a model
7. Click "Save"

Next time you open `/models`:
- Your API key is already filled in
- Your last provider is pre-selected
- Your last model is highlighted

## 📁 New File Structure

```
chat2sql/
├── app.py                  # Main entry point
├── agent.py                # AI agent logic
├── tools.py                # Database tools
├── config.py               # ✨ NEW: Configuration management
├── api_models.py           # ✨ NEW: Dynamic model fetching
├── ui/
│   ├── __init__.py
│   ├── styles.py
│   ├── modals.py           # ✨ UPDATED: Dynamic model loading
│   └── chat_view.py
├── requirements.txt        # ✨ UPDATED: Latest packages
└── .env                    # Optional: API keys (create this)
```

## 🔧 Installation & Setup

### Step 1: Update Dependencies

```bash
cd /home/yaswanth/programming/PinnacleAi/python/chat2sql
source venv/bin/activate

# Upgrade all packages
pip install --upgrade -r requirements.txt
```

This will install:
- Latest langchain packages (v0.2+) with `bind_tools` support
- `httpx` for API requests
- `google-generativeai` for direct Gemini API access

### Step 2: (Optional) Create .env File

Create `.env` in the project root:

```bash
# .env file
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

This way you don't need to enter API keys in the UI every time.

### Step 3: Run the App

```bash
python app.py
```

## 🎮 How to Use

### Configure Models (with dynamic fetching):

1. Type `/models`
2. Select provider (e.g., "Google Gemini")
3. Enter your API key (or it loads from config/.env)
4. **Wait a moment** - Models are fetched from the API
5. You'll see "✓ 8 models available" (or however many)
6. **All available models appear** - including experimental ones!
7. Select your model (e.g., `gemini-2.0-flash-exp`)
8. Click "✓ Save"

### Refresh Models:

If new models are released:
1. Open `/models`
2. Click "🔄 Refresh Models"
3. Models re-fetch from API with your current key
4. New models appear!

### Connect to Database:

```
/db
```

Enter your PostgreSQL credentials and test connection.

### Start Chatting:

```
What tables are in my database?
Show me the schema for users table
Find the top 10 customers
```

## 🐛 Error Solutions

### "error creating agent: bind_tools"

**Solution:**
```bash
pip install --upgrade langchain-google-genai langchain-core langgraph
```

The old v0.0.x packages don't have `bind_tools`. Upgrade to v1.0+.

### "No models available"

**Causes & Solutions:**

1. **Invalid API key**
   - Check your API key is correct
   - Google: https://makersuite.google.com/app/apikey
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/

2. **Network issue**
   - Check internet connection
   - App falls back to known models automatically

3. **Provider API down**
   - App will use fallback models
   - Click "🔄 Refresh Models" to retry

### Still can't type in input box?

This is usually a terminal issue:

```bash
# Try different terminal
gnome-terminal -- python app.py

# Or use textual dev mode
textual run --dev app.py

# Check terminal type
echo $TERM  # Should be xterm-256color
```

## 📊 Comparison

### Before:
- ❌ Hardcoded model list (outdated)
- ❌ Old langchain (bind_tools error)
- ❌ No config persistence
- ❌ Re-enter API keys every time
- ❌ Limited models
- ❌ "error creating agent"

### After:
- ✅ Dynamic model fetching from APIs
- ✅ Latest langchain (v0.2+)
- ✅ Persistent config (~/.chat2sql)
- ✅ Auto-loads saved keys
- ✅ ALL available models (including experimental)
- ✅ Agent creation works perfectly!

## 🔍 Technical Details

### How Model Fetching Works:

1. User opens `/models` modal
2. Modal calls `ModelFetcher.fetch_all_models(provider, api_key)`
3. For Google:
   - Uses `google.generativeai.list_models()` with API key
   - Filters for models with `generateContent` capability
   - Returns all available Gemini models
4. For OpenAI:
   - Calls `https://api.openai.com/v1/models` with API key
   - Filters for GPT models
   - Returns available GPT-4 and GPT-3.5 models
5. For Anthropic:
   - No public models API
   - Returns known Claude 3.5 models
6. If API fetch fails:
   - Falls back to `FALLBACK_MODELS` dict
   - Always shows some models

### Config Storage:

Config stored in: `~/.chat2sql/config.json`

```json
{
  "google_api_key": "your-key",
  "last_provider": "google",
  "last_model_google": "gemini-2.0-flash-exp",
  "last_model_openai": "gpt-4o-mini",
  "db_connection": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "user": "postgres"
  }
}
```

Passwords are NOT stored in config.

## 🧪 Testing

### Test dynamic model fetching:

```bash
# Enter Python REPL
python

# Test model fetching
import asyncio
from api_models import ModelFetcher

# Fetch Google models
models = asyncio.run(ModelFetcher.fetch_google_models("your-api-key"))
print(models)
# Should print: ['gemini-2.0-flash-exp', 'gemini-1.5-pro', ...]
```

### Test config:

```bash
python

from config import get_config

config = get_config()
config.set_api_key("google", "test-key")
print(config.get_api_key("google"))
# Should print: test-key

# Check config file
# cat ~/.chat2sql/config.json
```

### Test agent creation:

```bash
python app.py

# In the app:
/models
# Select Google
# Enter valid API key
# Select gemini-2.0-flash-exp
# Click Save

# Should see: "✓ LLM configured: google / gemini-2.0-flash-exp"
# NOT: "error creating agent"
```

## ✅ Success Checklist

- [x] Updated langchain packages to v0.2+
- [x] Created api_models.py for dynamic fetching
- [x] Created config.py for persistent storage
- [x] Updated modals.py to fetch models dynamically
- [x] Added "Refresh Models" button
- [x] Configured auto-save/auto-load for API keys
- [x] Configured remember last provider/model
- [x] Tested agent creation - works!
- [x] Input box more visible
- [x] Mouse support enabled

## 🎯 Try These Commands

```bash
# Run the app
python app.py

# Configure with Gemini 2.0
/models
# Select Google → Enter API key → Select gemini-2.0-flash-exp → Save

# Connect database
/db
# Enter credentials → Test Connection → Connect

# Ask questions
What tables are in the database?
Show me the users table schema
Count rows in the orders table
```

## 💡 Pro Tips

1. **Use .env file** - Store API keys there, never enter them again
2. **Refresh models monthly** - Click "🔄 Refresh Models" to see new releases
3. **Try experimental models** - Like `gemini-2.0-flash-thinking-exp`
4. **Switch providers easily** - Config remembers your API key for each
5. **Check ~/.chat2sql/config.json** - See all saved settings

## 🚨 Important Notes

- API keys are saved in `~/.chat2sql/config.json` (plain text)
- For production, use `.env` file with proper permissions
- Database passwords are NOT saved
- Model lists update when you open `/models`
- Fallback models ensure app always works

## 📚 Module Documentation

### api_models.py

```python
class ModelFetcher:
    @staticmethod
    async def fetch_google_models(api_key: Optional[str]) -> List[str]:
        """Fetch available Gemini models from Google API"""

    @staticmethod
    async def fetch_openai_models(api_key: Optional[str]) -> List[str]:
        """Fetch available OpenAI models"""

    @staticmethod
    async def fetch_anthropic_models(api_key: Optional[str]) -> List[str]:
        """Get Anthropic models (hardcoded, no API endpoint)"""

    @staticmethod
    async def fetch_all_models(provider: str, api_key: Optional[str]) -> List[str]:
        """Fetch models for any provider"""

def get_fallback_models(provider: str) -> List[str]:
    """Get fallback models if API fetch fails"""
```

### config.py

```python
class Config:
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider"""

    def set_api_key(self, provider: str, api_key: str):
        """Save API key"""

    def get_last_provider() -> Optional[str]:
        """Get last used provider"""

    def set_last_provider(provider: str):
        """Save last used provider"""

    def get_last_model(provider: str) -> Optional[str]:
        """Get last used model for provider"""

    def set_last_model(provider: str, model: str):
        """Save last used model"""

def get_config() -> Config:
    """Get global config instance"""
```

## 🎊 Summary

This update transforms the app from hardcoded models to **dynamic, API-driven model selection** while fixing the critical `bind_tools` error. You can now see ALL available models including the very latest experimental releases, and your settings persist across sessions!

**Everything is now working perfectly!** 🚀
