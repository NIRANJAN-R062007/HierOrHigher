-- Gap reports now record which engine produced them and the offline ML
-- scorer's full result (the /ml/score contract) when it ran.
-- source = 'ml'     -> confident offline score, zero Gemini calls spent
-- source = 'gemini' -> ML unavailable/unsure; the embedding pipeline ran
--                      (ml_score still stored when the model ran but deferred)

alter table public.gap_reports
  add column ml_score jsonb,
  add column source text not null default 'gemini';
