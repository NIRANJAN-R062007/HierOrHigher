import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ErrorState from "../components/dashboard/ErrorState";
import GapSection from "../components/dashboard/GapSection";
import HistoryModal from "../components/dashboard/HistoryModal";
import InterviewSection from "../components/dashboard/InterviewSection";
import ProfileSection from "../components/dashboard/ProfileSection";
import ResumeSwitcher from "../components/dashboard/ResumeSwitcher";
import ScoreSection from "../components/dashboard/ScoreSection";
import Sidebar from "../components/dashboard/Sidebar";
import { SkeletonCard } from "../components/dashboard/Skeleton";
import UploadPanel from "../components/dashboard/UploadPanel";
import { useAuth } from "../context/AuthContext";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { api } from "../lib/api";

/**
 * The working dashboard: a sidebar stepper down the four module sections plus
 * a History panel, with all results for the active resume as connected
 * sections in the main column. Persisted results load on boot, so nothing
 * re-processes on reload.
 */
export default function Dashboard() {
  const { user, signOut } = useAuth();
  const [booting, setBooting] = useState(true);
  const [bootError, setBootError] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  const [resumes, setResumes] = useState([]);
  const [resume, setResume] = useState(null);
  const [gap, setGap] = useState(null);
  const [interviewSet, setInterviewSet] = useState(null);
  const [profileDraft, setProfileDraft] = useState(null);
  const [jdText, setJdText] = useState("");
  const [lastFile, setLastFile] = useState(null);

  const applyOverview = useCallback((overview) => {
    setResume(overview.resume);
    setGap(overview.gap_report);
    setInterviewSet(overview.interview_set);
    setProfileDraft(overview.profile_draft);
    setJdText(overview.job_description_text || "");
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const listing = await api.listResumes();
        setResumes(listing);
        if (listing.length > 0) {
          applyOverview(await api.getOverview(listing[0].id));
        }
      } catch (err) {
        setBootError(err.message);
      }
      setBooting(false);
    })();
  }, [applyOverview]);

  const switchResume = useAsyncAction(async (resumeId) => {
    if (resumeId === resume?.resume_id) return;
    applyOverview(await api.getOverview(resumeId));
  });

  const upload = useAsyncAction(async (file) => {
    const result = await api.uploadResume(file);
    if (result.cached) {
      // Identical file re-uploaded: restore everything already computed.
      applyOverview(await api.getOverview(result.resume_id));
      setResume(result);
    } else {
      setResume(result);
      setGap(null);
      setInterviewSet(null);
      setProfileDraft(null);
      setJdText("");
    }
    setResumes(await api.listResumes());
  });

  const gapAction = useAsyncAction(async () => {
    const result = await api.createGapReport(resume.resume_id, jdText);
    if (!gap || gap.gap_report_id !== result.gap_report_id) {
      setInterviewSet(null);
    }
    setGap(result);
  });

  const interviewAction = useAsyncAction(async () => {
    setInterviewSet(await api.createInterviewSet(resume.resume_id, gap.jd_id));
  });

  const profileAction = useAsyncAction(async () => {
    setProfileDraft(await api.createProfileDraft(resume.resume_id));
  });

  const sections = [
    { id: "resume-score", label: "Resume score", ready: Boolean(resume) },
    { id: "gap-map", label: "Gap map", ready: Boolean(gap) },
    { id: "interview", label: "Mock interview", ready: Boolean(interviewSet) },
    { id: "profile", label: "Profile drafts", ready: Boolean(profileDraft) },
  ];

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-800">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="font-display text-lg font-semibold text-paper-50">
            Hire<span className="text-gold-400">Or</span>Higher
          </Link>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-paper-200/70 sm:block">{user?.email}</span>
            <button
              type="button"
              onClick={signOut}
              className="rounded-full border border-ink-700 px-4 py-1.5 text-sm font-medium text-paper-200 transition-colors hover:border-ink-500 active:scale-95"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl flex-col px-5 pb-24 sm:px-8 lg:flex-row lg:gap-10">
        <Sidebar
          sections={sections}
          onOpenHistory={() => resume && setHistoryOpen(true)}
        />

        <main className="min-w-0 flex-1 space-y-12 pt-8">
          {booting ? (
            <div className="space-y-6" aria-label="Loading your results">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : (
            <>
              {bootError && (
                <ErrorState
                  message={bootError}
                  onRetry={() => window.location.reload()}
                />
              )}

              <ResumeSwitcher
                resumes={resumes}
                activeId={resume?.resume_id}
                onSelect={switchResume.run}
                busy={switchResume.loading}
              />
              {switchResume.error && <ErrorState message={switchResume.error} />}

              <UploadPanel
                resume={resume}
                uploading={upload.loading}
                error={upload.error}
                onUpload={(file) => {
                  setLastFile(file);
                  upload.run(file);
                }}
                onRetry={lastFile ? () => upload.run(lastFile) : null}
              />

              <section id="resume-score" aria-labelledby="resume-score-h" className="scroll-mt-20">
                <h2 id="resume-score-h" className="font-display text-2xl font-semibold text-paper-50">
                  1 · Resume score
                </h2>
                <p className="mb-4 mt-1 text-sm text-paper-200/70">
                  How screening software and humans each read your resume.
                </p>
                <ScoreSection resume={resume} />
              </section>

              <section id="gap-map" aria-labelledby="gap-map-h" className="scroll-mt-20">
                <h2 id="gap-map-h" className="font-display text-2xl font-semibold text-paper-50">
                  2 · Gap map
                </h2>
                <p className="mb-4 mt-1 text-sm text-paper-200/70">
                  What the target job wants vs. what your resume already proves.
                </p>
                <GapSection
                  resume={resume}
                  gap={gap}
                  jdText={jdText}
                  onJdTextChange={setJdText}
                  running={gapAction.loading}
                  error={gapAction.error}
                  onRun={gapAction.run}
                />
              </section>

              <section id="interview" aria-labelledby="interview-h" className="scroll-mt-20">
                <h2 id="interview-h" className="font-display text-2xl font-semibold text-paper-50">
                  3 · Mock interview
                </h2>
                <p className="mb-4 mt-1 text-sm text-paper-200/70">
                  Questions built from your resume, the role, and your gaps.
                </p>
                <InterviewSection
                  gap={gap}
                  interviewSet={interviewSet}
                  running={interviewAction.loading}
                  error={interviewAction.error}
                  onGenerate={interviewAction.run}
                />
              </section>

              <section id="profile" aria-labelledby="profile-h" className="scroll-mt-20">
                <h2 id="profile-h" className="font-display text-2xl font-semibold text-paper-50">
                  4 · Profile drafts
                </h2>
                <p className="mb-4 mt-1 text-sm text-paper-200/70">
                  Your achievements, rewritten for LinkedIn — in two tones.
                </p>
                <ProfileSection
                  resume={resume}
                  profileDraft={profileDraft}
                  running={profileAction.loading}
                  error={profileAction.error}
                  onGenerate={profileAction.run}
                />
              </section>
            </>
          )}
        </main>
      </div>

      {historyOpen && resume && (
        <HistoryModal
          resumeId={resume.resume_id}
          resumes={resumes}
          activeResumeId={resume.resume_id}
          onSwitchResume={switchResume.run}
          onClose={() => setHistoryOpen(false)}
        />
      )}
    </div>
  );
}
