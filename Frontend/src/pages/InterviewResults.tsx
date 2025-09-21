import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend
} from "recharts";

interface Evaluation {
  overall_score: number;
  category_scores?: Record<string, number>;
  strengths?: string[];
  weaknesses?: string[];
  detailed_feedback?: string;
  detailed_explanation?: string;
}

interface FinalAssessment {
  final_recommendation: string;
  confidence_level: number;
  overall_assessment: string;
  key_strengths: string[];
  development_areas: string[];
  technical_level: string;
  communication_rating: number;
  problem_solving_rating: number;
  role_fit: string;
  next_steps: string;
}

const InterviewResults: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { sessionId } = location.state || {};

  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [finalAssessment, setFinalAssessment] = useState<FinalAssessment | null>(null);
  const [reportPath, setReportPath] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      navigate("/");
      return;
    }

    const fetchReport = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/generate-report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });
        if (!res.ok) throw new Error("Failed to generate report");
        const data = await res.json();

        setEvaluations(data.evaluations || []);
        if (data.final_assessment) setFinalAssessment(data.final_assessment);
        if (data.report_path) setReportPath(data.report_path);
      } catch (err) {
        console.error("❌ Failed to fetch report:", err);
      }
    };

    fetchReport();
  }, [sessionId, navigate]);

  // Data for line chart
  const scoreData = evaluations.map((ev, idx) => ({
    name: `Q${idx + 1}`,
    score: ev.overall_score || 0,
  }));

  // Data for bar chart (category breakdown of first question)
  const categoryData =
    evaluations.length > 0 && evaluations[0].category_scores
      ? Object.entries(evaluations[0].category_scores).map(([cat, val]) => ({
          category: cat,
          score: val,
        }))
      : [];

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Interview Results</h1>

      {/* Final Assessment */}
      {finalAssessment && (
        <div className="mb-8 p-6 border rounded-lg shadow bg-white">
          <h2 className="text-2xl font-semibold mb-4">Final Assessment</h2>
          <p><strong>Recommendation:</strong> {finalAssessment.final_recommendation}</p>
          <p><strong>Confidence:</strong> {finalAssessment.confidence_level}/10</p>
          <p><strong>Technical Level:</strong> {finalAssessment.technical_level}</p>
          <p><strong>Communication:</strong> {finalAssessment.communication_rating}/10</p>
          <p><strong>Problem Solving:</strong> {finalAssessment.problem_solving_rating}/10</p>
          <p className="mt-2">{finalAssessment.overall_assessment}</p>
        </div>
      )}

      {/* Graphs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
        {/* Line chart - Scores per question */}
        <div className="p-4 border rounded-lg shadow bg-white">
          <h3 className="text-lg font-semibold mb-2">Scores per Question</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={scoreData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#2E86AB" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Bar chart - Category breakdown */}
        <div className="p-4 border rounded-lg shadow bg-white">
          <h3 className="text-lg font-semibold mb-2">Category Breakdown (Q1)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={categoryData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="category" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="score" fill="#A23B72" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Evaluations */}
      <h2 className="text-xl font-semibold mb-4">Detailed Question Evaluations</h2>
      <div className="space-y-6">
        {evaluations.map((ev, idx) => (
          <div key={idx} className="p-4 border rounded-lg shadow bg-white">
            <h3 className="font-bold">Question {idx + 1}</h3>
            <p><strong>Score:</strong> {ev.overall_score}/100</p>
            <p><strong>Strengths:</strong> {ev.strengths?.join(", ") || "N/A"}</p>
            <p><strong>Weaknesses:</strong> {ev.weaknesses?.join(", ") || "N/A"}</p>
            <p><strong>Feedback:</strong> {ev.detailed_feedback || "No feedback"}</p>
          </div>
        ))}
      </div>

      {/* Download Report */}
      {reportPath && (
        <div className="mt-8">
          <a
            href={`http://localhost:8000/api/download-report/${sessionId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700"
          >
            📄 Download Full Report (PDF)
          </a>
        </div>
      )}

      <button
        onClick={() => navigate("/")}
        className="mt-6 bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-800"
      >
        Go Home
      </button>
    </div>
  );
};

export default InterviewResults;
