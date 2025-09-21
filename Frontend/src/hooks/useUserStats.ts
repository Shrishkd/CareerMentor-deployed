import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

// Simple in-memory cache
let cachedStats: any = null;

export const useUserStats = (userId: string | null) => {
  const [stats, setStats] = useState<any>(
    cachedStats || {
      interviewsCompleted: 0,
      averageScore: 0,
      atsScore: 0,
      recentInterviews: [],
    }
  );
  const [loading, setLoading] = useState(!cachedStats);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    const fetchStats = async () => {
      try {
        setLoading(true);
        setError(null);

        // fetch stats from DB
        const { data, error } = await supabase
          .from("user_stats")
          .select("*")
          .eq("user_id", userId)
          .single();

        if (error) throw error;

        const result = {
          interviewsCompleted: data?.interviews_completed || 0,
          averageScore: data?.average_score || 0,
          atsScore: data?.ats_score || 0,
          recentInterviews: data?.recent_interviews || [],
        };

        cachedStats = result;
        setStats(result);
      } catch (err: any) {
        setError(err.message || "Failed to load stats");
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [userId]);

  return { stats, loading, error };
};
