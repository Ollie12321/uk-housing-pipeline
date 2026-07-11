{% macro is_incremental_safe(date_column, this_model) %}
    /*
      Returns a date expression for the start of the earliest month that needs
      reprocessing when running in incremental mode.

      We go back one full month from the maximum already-loaded month to handle
      late-arriving data (transactions registered weeks after their legal date).

      Usage in models:
          where {{ date_column }} >= {{ is_incremental_safe('transaction_month', this) }}
    */
    (
        select date_trunc(
            date_sub(max({{ date_column }}), interval 1 month),
            month
        )
        from {{ this_model }}
    )
{% endmacro %}
