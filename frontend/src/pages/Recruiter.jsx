import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ErrorState from "../components/dashboard/ErrorState";
import { SkeletonCard } from "../components/dashboard/Skeleton";
import PostingForm from "../components/recruiter/PostingForm";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

const STATUS_TONES = {
  open: "border-emerald-500/30 bg-emerald-900/40 text-emerald-300",
  draft: "border-ink-600 bg-ink-700 text-paper-200/70",
  closed: "border-red-500/30 bg-red-900/40 text-red-300",
};

function StatusPill({ status }) {
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_TONES[status]}`}
    >
      {status}
    </span>
  );
}

/** The apply link, shown in full so it can be copied and pasted anywhere. */
function ApplyLink({ postingId, live }) {
  const [copied, setCopied] = useState(false);
  const url = `${window.location.origin}/apply/${postingId}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <code
        className={`truncate rounded-lg bg-ink-900 px-3 py-1.5 text-xs ${
          live ? "text-paper-200/80" : "text-paper-200/40 line-through"
        }`}
      >
        {url}
      </code>
      <button
        type="button"
        onClick={copy}
        className="rounded-full border border-ink-700 px-3 py-1.5 text-xs font-medium text-paper-200 transition-colors hover:border-ink-500"
      >
        {copied ? "Copied" : "Copy link"}
      </button>
      {!live && (
        <span className="text-xs text-paper-200/50">
          Only an open posting accepts applications.
        </span>
      )}
    </div>
  );
}

function CreateOrgCard({ onCreate, error, busy }) {
  const [name, setName] = useState("");

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (name.trim().length >= 2) onCreate(name.trim());
      }}
      className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card"
    >
      <h2 className="font-display text-lg font-semibold text-paper-50">
        Create your organization
      </h2>
      <p className="mt-1 text-sm text-paper-200/70">
        Your postings, applicants, and teammates all live inside it. Nothing is
        ever shared with another organization.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <input
          type="text"
          required
          minLength={2}
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Acme Talent"
          className="min-w-56 flex-1 rounded-xl border border-ink-700 bg-ink-900 px-4 py-2.5 text-sm text-paper-50 placeholder-paper-200/40 transition-colors focus:border-gold-500"
        />
        <button
          type="submit"
          disabled={busy || name.trim().length < 2}
          className="rounded-full bg-gold-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Creating…" : "Create"}
        </button>
      </div>
      {error && (
        <div className="mt-4">
          <ErrorState message={error} />
        </div>
      )}
    </form>
  );
}

function TeamPanel({ org }) {
  const [members, setMembers] = useState([]);
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    api
      .listOrgMembers(org.id)
      .then((rows) => live && setMembers(rows))
      .catch((err) => live && setError(err.message));
    return () => {
      live = false;
    };
  }, [org.id]);

  async function invite(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const member = await api.inviteOrgMember(org.id, email.trim());
      setMembers((current) =>
        current.some((m) => m.id === member.id) ? current : [...current, member],
      );
      setEmail("");
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  return (
    <section className="rounded-2xl border border-ink-700 bg-ink-800 p-6 shadow-card">
      <h2 className="font-display text-lg font-semibold text-paper-50">Team</h2>
      <ul className="mt-3 space-y-2">
        {members.map((member) => (
          <li
            key={member.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-ink-900 px-4 py-2.5"
          >
            <span className="text-sm text-paper-200">{member.email}</span>
            <span className="flex items-center gap-2 text-xs">
              <span className="capitalize text-paper-200/60">{member.role}</span>
              {member.pending && (
                <span className="rounded-full border border-gold-500/30 bg-gold-500/10 px-2 py-0.5 text-gold-300">
                  Invite pending
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>

      {org.role === "admin" && (
        <form onSubmit={invite} className="mt-4 flex flex-wrap gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="teammate@company.com"
            className="min-w-52 flex-1 rounded-xl border border-ink-700 bg-ink-900 px-4 py-2 text-sm text-paper-50 placeholder-paper-200/40 transition-colors focus:border-gold-500"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-full border border-ink-600 px-5 py-2 text-sm font-medium text-paper-200 transition-colors hover:border-gold-500 hover:text-gold-300 disabled:opacity-40"
          >
            {busy ? "Inviting…" : "Invite"}
          </button>
        </form>
      )}
      <p className="mt-3 text-xs text-paper-200/50">
        Invites are claimed when that address signs in — no account is created
        for them here.
      </p>
      {error && (
        <div className="mt-3">
          <ErrorState message={error} />
        </div>
      )}
    </section>
  );
}

/**
 * The recruiter console: pick an org, manage its team, and run its postings.
 *
 * Deliberately separate from the student-facing dashboard — this side is an
 * internal hiring tool, not a marketplace. Candidates have no account here and
 * are only ever visible on the posting they applied to.
 */
export default function Recruiter() {
  const { signOut } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [orgs, setOrgs] = useState([]);
  const [activeOrgId, setActiveOrgId] = useState(null);
  const [postings, setPostings] = useState([]);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState(null);

  const activeOrg = orgs.find((org) => org.id === activeOrgId) ?? null;

  useEffect(() => {
    (async () => {
      try {
        const rows = await api.listOrganizations();
        setOrgs(rows);
        setActiveOrgId(rows[0]?.id ?? null);
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    })();
  }, []);

  const loadPostings = useCallback(async (orgId) => {
    if (!orgId) return;
    try {
      setPostings(await api.listJobPostings(orgId));
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    loadPostings(activeOrgId);
  }, [activeOrgId, loadPostings]);

  async function createOrg(name) {
    setBusy(true);
    setFormError(null);
    try {
      const org = await api.createOrganization(name);
      setOrgs((current) => [...current, org]);
      setActiveOrgId(org.id);
    } catch (err) {
      setFormError(err.message);
    }
    setBusy(false);
  }

  async function savePosting(values) {
    setBusy(true);
    setFormError(null);
    try {
      if (editing) {
        await api.updateJobPosting(editing.id, values);
      } else {
        await api.createJobPosting(activeOrgId, values);
      }
      await loadPostings(activeOrgId);
      setCreating(false);
      setEditing(null);
    } catch (err) {
      setFormError(err.message);
    }
    setBusy(false);
  }

  async function setStatus(posting, status) {
    try {
      await api.updateJobPosting(posting.id, { status });
      await loadPostings(activeOrgId);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen bg-ink-950">
      <header className="border-b border-ink-800">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-5 sm:px-8">
          <Link to="/" className="font-display text-lg font-semibold text-paper-50">
            Hire<span className="text-gold-400">Or</span>Higher
          </Link>
          <div className="flex items-center gap-4">
            <Link
              to="/dashboard"
              className="text-sm font-medium text-paper-200 transition-colors hover:text-paper-50"
            >
              My dashboard
            </Link>
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

      <main className="mx-auto max-w-5xl px-5 pb-24 pt-10 sm:px-8">
        <h1 className="font-display text-3xl font-semibold text-paper-50">Hiring</h1>
        <p className="mb-8 mt-1 text-sm text-paper-200/70">
          Post a role, share its apply link, and screen everyone who applies —
          ranked against the description you wrote.
        </p>

        {loading ? (
          <SkeletonCard />
        ) : error ? (
          <ErrorState message={error} onRetry={() => window.location.reload()} />
        ) : orgs.length === 0 ? (
          <CreateOrgCard onCreate={createOrg} error={formError} busy={busy} />
        ) : (
          <div className="space-y-8">
            {orgs.length > 1 && (
              <div className="flex flex-wrap gap-2">
                {orgs.map((org) => (
                  <button
                    key={org.id}
                    type="button"
                    onClick={() => setActiveOrgId(org.id)}
                    className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
                      org.id === activeOrgId
                        ? "border-gold-500 bg-gold-500/10 text-gold-300"
                        : "border-ink-700 text-paper-200/70 hover:border-ink-500"
                    }`}
                  >
                    {org.name}
                  </button>
                ))}
              </div>
            )}

            <section>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-display text-xl font-semibold text-paper-50">
                  {activeOrg?.name} · postings
                </h2>
                {!creating && !editing && (
                  <button
                    type="button"
                    onClick={() => {
                      setCreating(true);
                      setFormError(null);
                    }}
                    className="rounded-full bg-gold-500 px-5 py-2 text-sm font-semibold text-ink-950 transition-all hover:bg-gold-400 active:scale-95"
                  >
                    New posting
                  </button>
                )}
              </div>

              {(creating || editing) && (
                <div className="mt-4">
                  <PostingForm
                    posting={editing}
                    submitting={busy}
                    error={formError}
                    onSubmit={savePosting}
                    onCancel={() => {
                      setCreating(false);
                      setEditing(null);
                      setFormError(null);
                    }}
                  />
                </div>
              )}

              {postings.length === 0 && !creating ? (
                <p className="mt-4 rounded-2xl border border-ink-700 bg-ink-800 p-8 text-center text-sm text-paper-200/70 shadow-card">
                  No postings yet. Create one to get a public apply link you can
                  share.
                </p>
              ) : (
                <ul className="mt-4 space-y-4">
                  {postings.map((posting) => (
                    <li
                      key={posting.id}
                      className="rounded-2xl border border-ink-700 bg-ink-800 p-5 shadow-card"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <h3 className="font-display text-lg font-semibold text-paper-50">
                            {posting.title}
                          </h3>
                          <StatusPill status={posting.status} />
                        </div>
                        <Link
                          to={`/hiring/postings/${posting.id}`}
                          className="text-sm font-semibold text-gold-400 transition-colors hover:text-gold-300"
                        >
                          {posting.application_count}{" "}
                          {posting.application_count === 1
                            ? "applicant"
                            : "applicants"}{" "}
                          →
                        </Link>
                      </div>

                      <ApplyLink
                        postingId={posting.id}
                        live={posting.status === "open"}
                      />

                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setEditing(posting);
                            setCreating(false);
                            setFormError(null);
                          }}
                          className="rounded-full border border-ink-700 px-4 py-1.5 text-xs font-medium text-paper-200 transition-colors hover:border-ink-500"
                        >
                          Edit
                        </button>
                        {posting.status !== "open" && (
                          <button
                            type="button"
                            onClick={() => setStatus(posting, "open")}
                            className="rounded-full border border-ink-700 px-4 py-1.5 text-xs font-medium text-emerald-300 transition-colors hover:border-emerald-500/50"
                          >
                            Open
                          </button>
                        )}
                        {posting.status === "open" && (
                          <button
                            type="button"
                            onClick={() => setStatus(posting, "closed")}
                            className="rounded-full border border-ink-700 px-4 py-1.5 text-xs font-medium text-red-300 transition-colors hover:border-red-500/50"
                          >
                            Close
                          </button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {activeOrg && <TeamPanel org={activeOrg} />}
          </div>
        )}
      </main>
    </div>
  );
}
