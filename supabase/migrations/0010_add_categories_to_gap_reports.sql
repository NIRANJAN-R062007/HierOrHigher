-- Gap reports can now carry a per-category breakdown of matched/missing
-- requirements — the data behind the dashboard's skill-gap radar chart.
-- Nullable: reports written before this (and any where the model returned
-- no categories) simply render the flat matched/missing view instead.
-- Shape: { "<category>": { "matched": [...], "missing": [...] }, ... }

alter table public.gap_reports
  add column categories jsonb;
