{#
  Backlog #40: every existing gate is a ratio (coverage/null-rate) or a
  duplicate count, so a source silently dropping from e.g. 106,000 rows to
  500 passes all of them -- #36 only catches the *total* zero-row outage
  case. This generic test compares a source's latest snapshot_date's row
  count against its immediately preceding snapshot_date's row count (using
  the append-only staging history backlog #1/#2 shipped) and fails if it
  drops below min_ratio of that baseline.

  Applied at the source (table) level in dbt/models/staging/_sources.yml,
  so `model` resolves to the raw staging relation -- extracted_at_utc is a
  plain column there (see data/staging/*.schema.json), not the
  snapshot_date dimension stg_*.sql derives from it, hence the cast here.

  Fewer than two distinct snapshot_date values (a fresh clone, or a source
  that has only ever been extracted once) means there is no baseline to
  compare against yet -- that's a legitimate state, not an anomaly, so it
  passes rather than failing vacuously in the #36 sense (that fix was about
  a *present but empty* snapshot, not an *absent* history).
#}

{% test row_count_anomaly(model, min_ratio=0.5) %}

{% set error_bps = (min_ratio * 10000) | round | int %}

{{ config(fail_calc='min(ratio_bps)', error_if='<' ~ error_bps, warn_if='<' ~ error_bps) }}

with counts as (
    select
        cast(extracted_at_utc as date) as snapshot_date,
        count(*) as row_count
    from {{ model }}
    group by 1
),

ranked as (
    select
        row_count,
        row_number() over (order by snapshot_date desc) as rn
    from counts
)

select
    case
        when (select count(*) from ranked) < 2 then 10000
        when (select row_count from ranked where rn = 2) = 0 then 10000
        else round(
            (select row_count from ranked where rn = 1)::double
            / (select row_count from ranked where rn = 2) * 10000
        )::integer
    end as ratio_bps

{% endtest %}
