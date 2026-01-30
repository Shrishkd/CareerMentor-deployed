# 🚀 Career Mentor - AI-Powered Interview Web App

**Career Mentor** is an AI-driven interview analysis platform that helps candidates practice real interviews and receive instant, detailed feedback. The system leverages **Generative AI**, **Speech Recognition**, and **Behavioral Analysis** to simulate an intelligent interviewer that not only asks domain-relevant questions but also evaluates user responses, expressions, and engagement.

---

## 🎯 Project Overview

Career Mentor provides a complete mock-interview experience by:

* Analyzing the candidate's **resume** to generate tailored questions.
* Conducting a live **AI-powered interview** with voice and code-based responses.
* Monitoring user activity using **camera tracking** for focus & attention.
* Generating an **AI-evaluated performance report** with insights, scores, and improvement suggestions.

---

## 🧠 Key Features

### 🧾 Resume-based Question Generation

* Upload your resume in PDF format.
* Backend AI (Gemini API) extracts key skills and generates relevant interview questions.

### 🎤 AI Interview Assistant

* Conducts interviews using Text-to-Speech (TTS) and listens via Speech-to-Text (Whisper STT).
* Evaluates voice answers based on **clarity**, **content**, and **relevance**.

### 💻 Coding Round Simulation

* Integrated **Monaco Editor IDE** for programming questions.
* Supports code execution and compilation using **Judge0 API**.

### 🎥 Live Monitoring System

* Uses camera monitoring (via OpenCV) to analyze user engagement.
* Detects distractions, gaze direction, and movements.

### 📊 Comprehensive Report Generation

* Automatically generates a **detailed interview report** (PDF) containing:

  * Technical and behavioral analysis.
  * Individual question-wise feedback.
  * Visual performance graphs.
  * Overall score and hiring recommendation.

### ☁️ Supabase Integration

* Securely stores resumes, audio responses, and reports.
* Generates signed URLs for private access.

---

## 🏗️ Tech Stack

| Layer                  | Technology                                              |
| ---------------------- | ------------------------------------------------------- |
| **Frontend**           | React + TypeScript + Vite + TailwindCSS + Framer Motion |
| **Backend**            | Flask (Python)                                          |
| **AI/ML**              | Google Gemini API, OpenAI Whisper, SpeechRecognition    |
| **Database & Storage** | Supabase (Postgres + Storage)                           |
| **Code Execution**     | Judge0 API                                              |
| **Deployment**         | Render (Frontend + Backend)                             |

---

## ⚙️ Project Structure

```
Career_Mentor/
├── Backend/
│   ├── backend_api.py       # Flask API with Supabase integration
│   ├── exp2.py              # AI logic for question generation & evaluation
│   ├── livevid1.py          # Camera monitoring module
│   ├── requirements.txt
│   └── .env                 # Environment variables (Google, RapidAPI, Supabase)
│
├── Frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ResumeUpload.tsx
│   │   │   ├── Interview.tsx
│   │   │   ├── InterviewResults.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── index.html
│   └── package.json
│   
│
└── README.md
```
---
## 📸 Screenshot
<img width="1896" height="987" alt="home" src="https://github.com/user-attachments/assets/d82498c7-6f77-49b4-903a-2dc07a67fafe" />

<img width="1917" height="984" alt="upload" src="https://github.com/user-attachments/assets/3cf1f323-ac1a-49df-bdef-d90154ca46ec" />

<img width="1919" height="970" alt="Q1" src="https://github.com/user-attachments/assets/e4a20798-03a0-4448-8c34-37f09e28069e" />

<img width="1912" height="990" alt="conding qn" src="https://github.com/user-attachments/assets/754e458b-28bb-4b51-9d9e-a19e0e95064b" />

<img width="995" height="918" alt="Performance overview Graph" src="https://github.com/user-attachments/assets/b90e21bc-8149-41da-a82b-1eeb146e8b10" />

<img width="1001" height="735" alt="Detailed qn analysis" src="https://github.com/user-attachments/assets/ced5fb63-9029-460b-9285-6e7afcccb7c5" />

<img width="844" height="222" alt="Camera report" src="https://github.com/user-attachments/assets/8c73ba0c-3dcb-4e75-ba2d-f88b2f3443aa" />

<img width="1280" height="720" alt="user pic 1" src="https://github.com/user-attachments/assets/73373228-d774-4860-b1d1-8d92c27ee9fe" />

<img width="1280" height="720" alt="user oic 2" src="https://github.com/user-attachments/assets/0c95d67d-bb1a-4239-84de-3addec0c440f" />






---
## Link
https://careermentor-ajvl.onrender.com
---

## 🚀 Deployment Guide

### 🟢 Backend on Render

1. Push repo to GitHub.
2. Create new **Web Service** on Render.
3. Root directory → `Backend`
4. Build Command:

   ```bash
   pip install -r requirements.txt
   ```
5. Start Command:

   ```bash
   gunicorn backend_api:app --bind 0.0.0.0:$PORT
   ```
6. Add environment variables in Render Dashboard (as above).

### 🟣 Frontend on Render

1. Create new **Static Site** on Render.
2. Root directory → `Frontend`
3. Build Command:

   ```bash
   npm install && npm run build
   ```
4. Publish Directory: `dist`
5. Add environment variables (starting with `VITE_`).

---

## 📁 Data Flow Summary

```
User → Upload Resume → Backend (exp2.py) → Generate Questions
     ↓
Frontend Interview Page → AI Interview (Voice + Code)
     ↓
Backend (Whisper + Gemini) → Evaluate Answers
     ↓
Generate Final PDF Report → Upload to Supabase
     ↓
Frontend → Displays Report & Download Link
```

---

## 🧩 Future Improvements

* Real-time behavioral emotion tracking using DeepFace.
* Multi-round interview scheduling.
* Recruiter dashboard for candidate comparison.
* Integration with LinkedIn for resume import.
* GPT-powered career recommendations.

---

## 👨‍💻 Author

**Shrish [https://shrish-portfolio.netlify.app]**


---

## 🪪 License

This project is licensed under the MIT License - feel free to modify and build upon it for learning or open development.

---

## 💬 Feedback & Contributions

If you’d like to improve Career Mentor or integrate your own AI models — pull requests and discussions are welcome!

> ⭐ Don’t forget to star the repository if you find it helpful!




