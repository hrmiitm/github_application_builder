# 🚀 GitHub Application Builder API

**Build and update static web applications automatically — deployed directly to GitHub Pages with AI assistance.**

## ✨ Key Features

* 🤖 **Dynamic LLM Model** – llm model can be dynamically change just by changing environment variable
* 🌐 **DuckDuckGo Search Tool** – Smart, contextual web lookups during build.
* 📎 **Attachment Handling** – Accepts and processes any Base64 media type (images, docs, audio).
* ⚙️ **GitHub Automation** – Creates repositories, commits files, and enables GitHub Pages.
* 🔁 **Smart Updates** – Can revise or extend existing GitHub-hosted apps while preserving prior functionality.

---

## 🧰 Tech Stack

* **FastAPI** – API framework
* **Pydantic AI** – LLM orchestration
* **PyGithub** – GitHub integration
* **DuckDuckGo Tool** – Web context fetching

---

---

## ⚙️ Setup

```bash
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
# or
uv pip install "fastapi[standard]" pydantic-ai PyGithub "pydantic-ai-slim[duckduckgo]"
```

---

## 🔑 Environment Variables

> Works with **OpenAI**, **Gemini**, **Claude**, or any **Ollama** model.

```bash
# 🧠 AI Model Configuration
export AIMODEL_NAME="openai:gpt-5-nano"
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_BASE_URL="https://aipipe.org/openai/v1"

# 🌐 GitHub Access
export GITHUB_ACCESS_TOKEN="your-github-token"

# 🔒 Form Secret
export GFORM_SECRET="your-secret-key"
```

---

## ▶️ Run the API
> You can also containerize using the included **Dockerfile**.  
```bash
uvicorn src.main:app --host 0.0.0.0 --port 7860
```

---

## 📡 Endpoints

### **POST `/task`**

Create or update a GitHub Pages web app automatically.

  | Field                 | Type    | Required        | Description                                                        |
  | --------------------- | ------- | --------------- | ------------------------------------------------------------------ |
  | `task`                | string  | ✅ (first round) | Prompt or instructions for what the web app should do or look like |
  | `evaluation_url`      | string  | ✅               | Webhook URL to receive build/evaluation outcome                    |
  | `secret`              | string  | ✅               | Must match your `GFORM_SECRET` for authentication                  |
  | Other optional fields | various | ❌               | E.g. attachments (Base64), style hints, context links, etc.        |

---

## 🧪 Testing

Test scripts (in `test/`) simulate and validate core flows:

* `createrepo.py` — test repository creation
* `enablepages.py` — test enabling GitHub Pages
* `buildappagent.py` — end-to-end build
* `updateappagent.py` — incremental updates
* `getallfilesurl.py` / `createfile.py` / `pydantic_document.py` — utility / formatting tests

To run all tests:

```bash
python -m test.enablepages
# or invoke individual scripts
```
   
---
