"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { JobActionOptions, JobActionResponse } from "@/components/job-action-types";

export function useJobAction() {
  const router = useRouter();
  const [result, setResult] = useState("");
  const [summary, setSummary] = useState("");
  const [pending, startTransition] = useTransition();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

  function runJobAction<T extends JobActionResponse>(options: JobActionOptions<T>) {
    startTransition(async () => {
      const response = await fetch(`${apiUrl}${options.path}`, options.init);
      const payload = (await response.json()) as T;
      setSummary(options.summarize(payload));
      setResult(JSON.stringify(payload, null, 2));
      router.refresh();
    });
  }

  return {
    pending,
    result,
    summary,
    runJobAction,
  };
}
