import { supabase } from "./supabase";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, formData } = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = {};
  if (session) headers.Authorization = `Bearer ${session.access_token}`;

  let payload;
  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${BASE}/api${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError(
      "Can't reach the HireOrHigher API — is the backend running?",
      0,
    );
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
  }
  return data;
}

export const api = {
  uploadResume(file) {
    const formData = new FormData();
    formData.append("file", file);
    return request("/resumes", { method: "POST", formData });
  },
  listResumes: () => request("/resumes"),
  getOverview: (resumeId) => request(`/resumes/${resumeId}/overview`),
  createGapReport: (resumeId, jobDescription) =>
    request("/gap-reports", {
      method: "POST",
      body: { resume_id: resumeId, job_description: jobDescription },
    }),
  createInterviewSet: (resumeId, jdId) =>
    request("/interview-sets", {
      method: "POST",
      body: { resume_id: resumeId, jd_id: jdId },
    }),
  createProfileDraft: (resumeId) =>
    request("/profile-drafts", {
      method: "POST",
      body: { resume_id: resumeId },
    }),
};
