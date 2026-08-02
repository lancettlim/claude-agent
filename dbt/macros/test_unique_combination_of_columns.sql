{#
  Backlog #42: most marts' real primary key is a composite of two or three
  columns (e.g. pokemon_usage_summary's (pokemon_key, event_tier),
  pokemon_team_core_usage's (pokemon_key, partner_pokemon_key)), which
  dbt's built-in `unique` generic test can't check -- it only accepts a
  single column_name. This is the standard `unique_combination_of_columns`
  pattern (the same one dbt-utils ships, reimplemented here rather than
  adding a package dependency for one macro): fails on any group of
  `combination_of_columns` values that appears more than once.
#}

{% test unique_combination_of_columns(model, combination_of_columns) %}

with validation as (
    select
        {{ combination_of_columns | join(', ') }},
        count(*) as row_count
    from {{ model }}
    group by {{ combination_of_columns | join(', ') }}
)

select *
from validation
where row_count > 1

{% endtest %}
