{% macro lag_months(date_expr, n_months) %}
    /*
      Returns the first day of the month that is n_months before date_expr.

      BigQuery syntax:
          date_trunc(date_sub(<date>, interval N month), month)

      Usage:
          {{ lag_months('t.month', 3) }}
    */
    date_trunc(date_sub({{ date_expr }}, interval {{ n_months }} month), month)
{% endmacro %}
