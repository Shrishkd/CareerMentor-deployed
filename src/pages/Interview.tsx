// src/pages/Interview.tsx
import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";
import Editor from "@monaco-editor/react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const JUDGE0_URL = "https://judge0-ce.p.rapidapi.com/submissions";

async function safeFetch(url: string, options: RequestInit = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Stricter programming question detector:
 * - Returns true if explicit language names are present OR
 * - Contains strong verbs like implement/write/solve/build
 */
function isProgrammingQuestion(q: string) {
  if (!q) return false;
  const lower = q.toLowerCase();

  // language names (strong signal)
  const langs = ["python", "c\\+\\+", "cpp", "java", "javascript", "js", "ruby", "go", "golang", "c#"];
  for (const l of langs) {
    const re = new RegExp(`\\b${l}\\b`, "i");
    if (re.test(q)) return true;
  }

  // strong coding verbs (require ~coding task)
  const strongVerbs = /\b(implement|write|solve|create|build|produce|construct|complete|program|code)\b/i;
  if (strongVerbs.test(q)) return true;

  // otherwise, do not treat as programming question
  return false;
}

const Interview: React.FC = () => {
  const navigate = useNavigate();

  const [sessionData, setSessionData] = useState<any | null>(() => {
    try {
      const raw = localStorage.getItem("interview_session");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  const [currentQuestion, setCurrentQuestion] = useState<number>(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // audio recording
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const [audioChunks, setAudioChunks] = useState<BlobPart[]>([]);

  // code editor
  const [codeAnswer, setCodeAnswer] = useState<string>("");
  const [language, setLanguage] = useState<string>("python");
  const [judgeResult, setJudgeResult] = useState<string>("");

  // TTS toggle
  const [ttsEnabled, setTtsEnabled] = useState<boolean>(true);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (!sessionData) {
      toast({
        title: "No interview session",
        description: "Please upload a resume first.",
      });
      navigate("/resume-upload");
    }
  }, [sessionData, navigate]);

  useEffect(() => {
    if (!sessionData) return;
    const q = sessionData.questions?.[currentQuestion];
    if (!q) return;

    // stop prior TTS
    if ("speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {}
      if (ttsEnabled) {
        const u = new SpeechSynthesisUtterance(q);
        u.lang = "en-US";
        u.rate = 1.0;
        utterRef.current = u;
        try {
          window.speechSynthesis.speak(u);
        } catch (err) {
          console.warn("TTS speak error:", err);
        }
      }
    }

    setCodeAnswer("");
    setJudgeResult("");

    const lower = q.toLowerCase();
    if (lower.includes("python")) setLanguage("python");
    else if (lower.includes("c++") || lower.includes("cpp")) setLanguage("cpp");
    else if (lower.includes("java")) setLanguage("java");
    else if (lower.includes("javascript") || lower.includes("js")) setLanguage("javascript");
    else setLanguage("python");
  }, [currentQuestion, sessionData, ttsEnabled]);

  // ---------- AUDIO RECORDING ----------
  const startRecording = async () => {
    if (!sessionData) {
      toast({ title: "Missing session", description: "Upload resume first." });
      return;
    }

    try {
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    } catch {}

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      audioStreamRef.current = stream;

      let options: MediaRecorderOptions = {};
      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) options = { mimeType: "audio/webm;codecs=opus" };
      else if (MediaRecorder.isTypeSupported("audio/webm")) options = { mimeType: "audio/webm" };
      else if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) options = { mimeType: "audio/ogg;codecs=opus" };

      const recorder = new MediaRecorder(stream, options);
      const localChunks: BlobPart[] = [];

      recorder.ondataavailable = (ev: BlobEvent) => {
        if (ev.data && ev.data.size > 0) {
          localChunks.push(ev.data);
          setAudioChunks((prev) => [...prev, ev.data]);
        }
      };

      recorder.onstop = async () => {
        if (localChunks.length > 0) {
          const blob = new Blob(localChunks, { type: localChunks[0] instanceof Blob ? (localChunks[0] as Blob).type : "audio/webm" });
          await submitAudio(blob);
        }
        try {
          stream.getTracks().forEach((t) => t.stop());
        } catch {}
        audioStreamRef.current = null;
        setMediaRecorder(null);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setAudioChunks([]);
      toast({ title: "Recording started", description: "Speak your answer clearly." });
    } catch (err) {
      console.error("Recording failed:", err);
      toast({ title: "Recording failed", description: "Allow microphone access and try again.", variant: "destructive" });
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      toast({ title: "Recording stopped", description: "Processing your answer..." });
    }
  };

  const submitAudio = async (audioBlob: Blob) => {
    if (!sessionData) return;
    setIsSubmitting(true);

    try {
      const form = new FormData();
      form.append("session_id", sessionData.session_id);
      form.append("question_index", String(currentQuestion));
      const ext = audioBlob.type.includes("ogg") ? "ogg" : audioBlob.type.includes("wav") ? "wav" : "webm";
      form.append("audio", audioBlob, `answer.${ext}`);

      const res = await fetch(`${API_BASE}/api/submit-answer`, { method: "POST", body: form });
      const data = await res.json();

      if (res.ok && data && data.evaluation) {
        toast({ title: "Answer evaluated", description: `Score: ${data.evaluation.overall_score ?? "N/A"}/100` });
        setAnswers((prev) => [...prev, data.transcript || ""]);
        setEvaluations((prev) => [...prev, data.evaluation]);

        if (currentQuestion < (sessionData.questions?.length || 0) - 1) {
          setCurrentQuestion((q) => q + 1);
        } else {
          await finishInterview();
        }
      } else {
        console.error("submit-audio invalid response:", data);
        throw new Error(data?.error || "Invalid server response");
      }
    } catch (err) {
      console.error("Audio submission failed:", err);
      toast({ title: "Submission failed", description: err instanceof Error ? err.message : String(err), variant: "destructive" });
    } finally {
      setIsSubmitting(false);
      setAudioChunks([]);
    }
  };

  // ---------- CODE (MONACO) + JUDGE0 ----------
  const runCode = async () => {
    if (!codeAnswer.trim()) {
      toast({ title: "No code", description: "Write code in the editor before running.", variant: "destructive" });
      return;
    }
    setJudgeResult("Running...");
    try {
      const langMap: Record<string, number> = { python: 71, cpp: 54, java: 62, javascript: 63 };
      const language_id = langMap[language] ?? 71;
      const body = {
        source_code: codeAnswer,
        language_id,
      };
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
        "X-RapidAPI-Key": import.meta.env.VITE_RAPIDAPI_KEY || ""
      };

      const url = `${JUDGE0_URL}?base64_encoded=false&wait=true`;
      const res = await axios.post(url, body, { headers });
      const out = res.data;
      if (out.stderr) setJudgeResult(`❌ Error:\n${out.stderr}`);
      else if (out.compile_output) setJudgeResult(`❌ Compile Error:\n${out.compile_output}`);
      else setJudgeResult(`✅ Output:\n${out.stdout || "No output"}`);
    } catch (err) {
      console.error("Judge0 error:", err);
      setJudgeResult(`❌ Judge0 error: ${(err as Error).message}`);
    }
  };

  const submitCodeAnswer = async () => {
    if (!sessionData) return;
    if (!codeAnswer.trim()) {
      toast({ title: "Empty", description: "Type your code before submitting.", variant: "destructive" });
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        session_id: sessionData.session_id,
        question_index: currentQuestion,
        answer: codeAnswer,
        type: "code",
      };
      const res = await fetch(`${API_BASE}/api/submit-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data && data.evaluation) {
        toast({ title: "Code evaluated", description: `Score: ${data.evaluation.overall_score ?? "N/A"}/100` });
        setAnswers((prev) => [...prev, codeAnswer]);
        setEvaluations((prev) => [...prev, data.evaluation]);
        if (currentQuestion < (sessionData.questions?.length || 0) - 1) {
          setCurrentQuestion((q) => q + 1);
        } else {
          await finishInterview();
        }
      } else {
        throw new Error(data?.error || "Invalid response from server");
      }
    } catch (err) {
      console.error("submitCodeAnswer failed:", err);
      toast({ title: "Submit failed", description: err instanceof Error ? err.message : String(err), variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit typed/text answer (non-empty)
  const submitTextAnswer = async (text: string) => {
    if (!sessionData) return;
    setIsSubmitting(true);
    try {
      const payload = { session_id: sessionData.session_id, question_index: currentQuestion, answer: text, type: "text" };
      const res = await fetch(`${API_BASE}/api/submit-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data && data.evaluation) {
        toast({ title: "Answer evaluated", description: `Score: ${data.evaluation.overall_score ?? "N/A"}/100` });
        setAnswers((prev) => [...prev, text]);
        setEvaluations((prev) => [...prev, data.evaluation]);
        if (currentQuestion < (sessionData.questions?.length || 0) - 1) {
          setCurrentQuestion((q) => q + 1);
        } else {
          await finishInterview();
        }
      } else {
        throw new Error(data?.error || "Invalid response from server");
      }
    } catch (err) {
      console.error("submitTextAnswer failed:", err);
      toast({ title: "Submit failed", description: (err as Error).message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Skip current question (submit as SKIPPED)
  const skipQuestion = async () => {
    if (!sessionData) return;
    setIsSubmitting(true);
    try {
      const payload = { session_id: sessionData.session_id, question_index: currentQuestion, answer: "SKIPPED", type: "text" };
      const res = await fetch(`${API_BASE}/api/submit-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data && data.evaluation) {
        // treat as answered with fallback evaluation
        setAnswers((prev) => [...prev, "SKIPPED"]);
        setEvaluations((prev) => [...prev, data.evaluation]);
      } else {
        // fallback local skip (if backend failed)
        setAnswers((prev) => [...prev, "SKIPPED"]);
        setEvaluations((prev) => [...prev, { overall_score: 0, detailed_feedback: "Skipped" }]);
      }

      if (currentQuestion < (sessionData.questions?.length || 0) - 1) {
        setCurrentQuestion((q) => q + 1);
      } else {
        await finishInterview();
      }
    } catch (err) {
      console.error("skipQuestion failed:", err);
      toast({ title: "Skip failed", description: (err as Error).message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  // ---------- Monitoring / Finish ----------
  const startMonitoring = async (durationSec = 180) => {
    if (!sessionData) return;
    try {
      await safeFetch(`${API_BASE}/api/start-monitoring`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionData.session_id, duration: durationSec }),
      });
      toast({ title: "Monitoring started", description: "Server-side camera monitoring started." });
    } catch (err) {
      console.error("startMonitoring failed:", err);
      toast({ title: "Monitoring failed", description: (err as Error).message, variant: "destructive" });
    }
  };

  const finishInterview = async () => {
    if (!sessionData) return;
    try {
      toast({ title: "Generating report", description: "Please wait..." });
      const data = await safeFetch(`${API_BASE}/api/generate-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionData.session_id }),
      });

      localStorage.setItem(
        "interview_results",
        JSON.stringify({
          ...data,
          session_id: sessionData.session_id,
          questions: sessionData.questions,
          answers,
          evaluations,
        })
      );

      toast({ title: "Interview complete", description: "Redirecting to results..." });
      setTimeout(() => navigate("/interview-results"), 1200);
    } catch (err) {
      console.error("finishInterview failed:", err);
      toast({ title: "Report generation failed", description: (err as Error).message, variant: "destructive" });
    }
  };

  // ---------- Render ----------
  if (!sessionData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading interview session...</p>
        </div>
      </div>
    );
  }

  const total = sessionData.questions?.length || 0;
  const progressPercentage = total ? (((currentQuestion + 1) / total) * 100) : 0;
  const questionText = sessionData.questions[currentQuestion] ?? "";
  const programQ = isProgrammingQuestion(questionText);

  return (
    <div className="min-h-screen bg-background py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="text-center mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-4">AI Interview Session</h1>
          <div className="flex items-center justify-center space-x-6 text-lg">
            <span className="text-muted-foreground">Question {currentQuestion + 1} of {total}</span>
            <div className="bg-primary/10 px-4 py-2 rounded-full">
              <span className="text-primary font-semibold">{Math.round(progressPercentage)}% Complete</span>
            </div>
          </div>
        </motion.div>

        <div className="mb-8">
          <div className="bg-muted rounded-full h-3">
            <div className="bg-gradient-to-r from-primary to-accent h-3 rounded-full transition-all duration-500" style={{ width: `${progressPercentage}%` }} />
          </div>
        </div>

        <Card className="mb-8">
          <CardContent className="p-8">
            <h2 className="text-2xl font-semibold text-foreground mb-6">{questionText}</h2>

            <div className="mb-6">
              <p className="text-sm text-muted-foreground">💡 Tip: For coding questions use the editor below and run your code. For others, record your voice.</p>
            </div>

            {programQ ? (
              <div>
                <div className="mb-3 flex items-center gap-3">
                  <label className="text-sm">Language</label>
                  <select value={language} onChange={(e) => setLanguage(e.target.value)} className="p-1 rounded border">
                    <option value="python">Python</option>
                    <option value="cpp">C++</option>
                    <option value="java">Java</option>
                    <option value="javascript">JavaScript</option>
                  </select>

                  <Button onClick={runCode} disabled={!codeAnswer.trim()}>Run Code</Button>
                  <Button onClick={submitCodeAnswer} disabled={!codeAnswer.trim() || isSubmitting}>Submit Code</Button>
                  <Button variant="ghost" onClick={skipQuestion} disabled={isSubmitting}>Skip</Button>
                </div>

                <Editor
                  height="360px"
                  defaultLanguage={language === "cpp" ? "cpp" : language}
                  language={language === "cpp" ? "cpp" : language}
                  value={codeAnswer}
                  onChange={(v) => setCodeAnswer(v ?? "")}
                  theme="vs-dark"
                  options={{ minimap: { enabled: false }, fontSize: 13 }}
                />

                {judgeResult && (
                  <pre className="bg-black text-white p-3 mt-3 rounded text-sm whitespace-pre-wrap">
                    {judgeResult}
                  </pre>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-4">
                {!isRecording ? (
                  <Button onClick={startRecording} disabled={isSubmitting}>
                    Start Recording
                  </Button>
                ) : (
                  <Button variant="destructive" onClick={stopRecording} disabled={isSubmitting}>
                    Stop Recording
                  </Button>
                )}

                <Button onClick={() => startMonitoring(180)} disabled={isRecording || isSubmitting}>
                  Start Monitoring (Server)
                </Button>

                <Button onClick={skipQuestion} disabled={isSubmitting}>
                  Skip Question
                </Button>

                <Button onClick={finishInterview} disabled={isRecording || isSubmitting}>
                  Finish Interview
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="text-sm text-muted-foreground mt-4">
          <p>Answers recorded: {answers.length} • Evaluations: {evaluations.length}</p>

          <div className="mt-3 flex items-center gap-3">
            <label className="text-sm">Read questions aloud:</label>
            <input type="checkbox" checked={ttsEnabled} onChange={(e) => setTtsEnabled(e.target.checked)} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Interview;
