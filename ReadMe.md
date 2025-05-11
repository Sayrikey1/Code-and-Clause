⚖️🤖 Code\&Clause: AI Assistant for Nigerian Tech Laws & Policies 🇳🇬

## 🧠 Overview

**Code\&Clause** is an AI-powered assistant designed to help users navigate and understand **Nigeria's technology laws and policies**. 📜 Built using data scraped from the [NITDA](https://nitda.gov.ng/) website, this project leverages advanced **Language Models** and **Retrieval-Augmented Generation (RAG)** along with the **Google Gemini API** to provide accurate, up-to-date guidance on:

* 🛡️ Regulatory compliance
* 🏛️ IT project clearance
* 🌐 Digital governance in Nigeria

## ✨ Features

🔹 **💬 Conversational AI** – Chat with a bot trained on Nigerian tech laws & policies
🔹 **📂 Document Search** – Upload PDFs for instant search, analysis, and summarization
🔹 **🎙️ Voice Input** – Ask questions with your voice
🔹 **🔐 User Authentication** – Secure sign-up & login for a personalized experience
🔹 **📚 Policy Database** – Indexed content from NITDA for lightning-fast results

## ⚙️ How It Works

1. 🗂️ **Data Collection**: Publicly available policy docs from [NITDA](https://nitda.gov.ng/)
2. 🧠 **Embedding & Indexing**: Using [`sentence-transformers/all-mpnet-base-v2`](https://huggingface.co/sentence-transformers/all-mpnet-base-v2) for semantic search
3. 🪄 **RAG Pipeline**: Queries → Matching content → Summarized by generative AI ([Google Gemini API](https://ai.google.dev/gemini-api/docs))
4. 🖥️ **Frontend (Streamlit)**: Intuitive interface supporting both text and audio input

## 🚀 Getting Started

### 🧰 Prerequisites

* 🐍 Python 3.10+
* 📦 [pip](https://pip.pypa.io/en/stable/)
* 🔑 [Google Gemini API Key](https://ai.google.dev/gemini-api/docs)
* 🤗 HuggingFace Hub Token

### 🛠️ Installation

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-org/code-and-clause.git
   cd code-and-clause
   ```

2. **Set up environment variables**

   * Copy `.env.example` → `.env` and fill in your API keys

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Download & cache models**

   * Place `sentence-transformers/all-mpnet-base-v2` in the `cached_models/` folder

5. **Run the backend (FastAPI)**

   ```bash
   python main.py
   ```

6. **Run the frontend (Streamlit)**

   ```bash
   cd frontend
   streamlit run app.py
   ```

## 🧪 Usage

💡 **Ask Questions**:
Type or speak your question about Nigerian tech policies.

📤 **Upload Documents**:
Submit PDFs and Images to get summaries and insights.

📜 **Review History**:
View your past chats and uploads.

## 🗂️ Project Structure

```
.
├── main.py                # Backend (FastAPI)
├── frontend/              # Streamlit app
├── rag/                   # Retrieval engine
├── models/                # DB models
├── routers/               # API endpoints
├── config/                # Settings & DB config
├── dependencies/          # Auth & error handling
├── cached_models/         # Pre-loaded models
└── ...
```

## 📸 Images

Here's a glimpse of what you'll see when using Code\&Clause:

| 📷 Chat Interface        | 📑 Document Upload       | 📊 Summary View          |
| ------------------------ | ------------------------ | ------------------------ |
| *(Add screenshots here)* | *(Add screenshots here)* | *(Add screenshots here)* |

> 🖼️ *To add images, simply place them in a folder (e.g., `/images`) and link them with markdown like `![Chatbot Screenshot](images/chat.png)`.*

## 📡 Data Source

All documents and policy data are directly scraped and updated from the [NITDA](https://nitda.gov.ng/) website.

## 👥 Authors

* Developed by [Sayrikey](https://github.com/Sayrikey1)
* Built with ❤️ by the **Code\&Clause Team**

## 📄 License

Licensed under the **Apache 2.0 License**.
See `LICENSE` for more info.

---

📬 *For questions, suggestions, or contributions, feel free to open an issue or a pull request!*
