# Airflow

**What it is:** The reference batch-scheduling orchestrator — the source of "data interval" as the correct mental model for scheduled runs, and a well-documented cautionary tale on timezone/DST scheduling correctness.
**Axis:** workflow.
**Depth:** medium.

## Products & surfaces

| Product | What it is |
|---|---|
| **Airflow scheduler** | Evaluates DAG schedules, creates DAG runs. |
| **Timetables** | Pluggable schedule logic (cron, custom Python, dataset-triggered) introduced to replace bare cron/timedelta. |
| **Catchup / backfill** | Two distinct mechanisms for running historical intervals. |

## Notable features

| Feature | What it does | Steal? |
|---|---|---|
| Data interval (`data_interval_start`/`end`) | Each run owns the time range it covers, not "now" | yes |
| Run fires after interval closes | Guarantees the data for that interval is complete before execution | yes |
| Catchup | Auto-runs every missed interval since the last run | yes, default false |
| Backfill | On-demand re-run of an arbitrary historical range | yes |
| Timetables | Pluggable schedule logic beyond cron/timedelta (irregular, dataset-triggered, holes) | yes |
| Timezone/DST correctness | A specific, repeatedly-hit class of scheduler bugs | cautionary |

## Worth stealing

### A run is parameterized by the period it covers, not by "now"

The core model: every DAG run owns a `[data_interval_start, data_interval_end)` window — *"the specific time range that a DAG run is responsible for processing."* Critically, **the run fires *after* the interval closes**, not at the start of it: a daily run covering `2024-01-01 00:00` to `2024-01-02 00:00` actually executes at `2024-01-02 00:00`, once the day's data is guaranteed complete. (Airflow 3 changed default behavior for trigger-based timetables, where `data_interval_start` and `data_interval_end` collapse to the same trigger timestamp — worth checking which timetable type is in play before assuming the classic offset-window semantics hold.)

**This is the design point worth stealing wholesale: a scheduled run is parameterized by the period it covers, not by wall-clock "now."** That distinction is what makes backfill coherent rather than ad hoc — re-running "the run for 2024-01-01" is a well-defined, idempotent operation (same interval, same inputs, deterministic outputs) precisely because the interval, not the execution time, is the run's identity. A scheduler that instead runs "now, processing whatever's new" has no clean way to re-run a specific historical period — there's no stable handle for "that one" beyond "whenever it happened to execute."

### Catchup vs. backfill — two distinct mechanisms, one dangerous by default

**Catchup**: when a scheduler resumes (after being paused, or after downtime), it *"will run any past scheduled intervals that have not been run"* — by default, **catchup is `True`**, meaning every missed interval since the last run gets auto-scheduled. **Backfill**: an explicit, on-demand re-run of a chosen historical range (e.g., after fixing a bug or adding a new task to an existing DAG). These solve different problems — catchup is "don't silently skip runs the scheduler missed," backfill is "deliberately reprocess history" — but Airflow's own default has burned users repeatedly: **default-true catchup after any nontrivial downtime produces a thundering herd** of every missed interval firing at once, unless the operator remembered to set `catchup=False`. The actionable lesson: **default catchup to false**; make "auto-run everything I missed" an explicit opt-in, not the surprise behavior after an outage.

### Timetables — a schedule is more than a cron string

Airflow's Timetable abstraction (introduced 2.2, superseding bare cron/timedelta) exists because real schedules often aren't expressible as a fixed interval: *"task runs that occur at different times each day,"* *"data intervals with 'holes' between intervals,"* or schedules driven by an arbitrary-but-predictable external list (sporting events, campaign dates). A custom timetable is a plugin class implementing `next_dagrun_info` and `infer_manual_data_interval`, with the hard requirement that **every datetime returned must be timezone-aware**. The transferable point: treating "when does this run next" as a pluggable interface rather than a single cron-string field is what lets a scheduler support the long tail of real-world schedule shapes (dataset-arrival-triggered, business-calendar-driven, irregular-but-known) without special-casing each one into the core engine.

## Worth avoiding

**Airflow's own history is a specific, repeated case study in getting timezone/DST wrong**, worth treating as a checklist of failure modes to test against directly, not just a general warning:
- Cron schedules with a **non-trivial hours section** (a range like `0 7-8 * * *`, or multiple values like `0 7,9 * * *`) computed the wrong first execution immediately after a DST transition.
- A **scheduler crash** (`AssertionError: next schedule shouldn't be earlier`) was triggered by a recurring cron timetable crossing a DST boundary.
- DAGs in `Europe/Brussels` **stopped scheduling entirely** around the October DST transition, with the scheduler oscillating between conflicting "next run" computations.
- `timedelta`/`relativedelta`-based schedules (as opposed to cron) respect DST for the DAG's *start date* but **do not adjust for DST on subsequent runs** — a subtly different, easy-to-miss bug class from the cron-based ones.

Airflow's own remediation guidance is the useful summary: use timezone-aware datetimes everywhere (they recommend Pendulum specifically), and **explicitly test schedules across DST boundaries** — don't assume a schedule that's correct in July stays correct in November. **Get timezone-correct scheduling right once, centrally**, in the scheduling primitive itself, rather than leaving every DAG/workflow author to independently avoid these bugs.

## Facts & figures

- Timetables introduced in Airflow 2.2, replacing bare cron-expression/timedelta scheduling as the extensibility point.
- Default `catchup` is `True` unless explicitly set to `False` per-DAG or via `catchup_by_default=False` globally.

## Sources

- [Airflow Data Intervals: A Deep Dive](https://towardsdatascience.com/airflow-data-intervals-a-deep-dive-15d0ccfb0661/) · [Dag Runs — Airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)
- [Timetables — Airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/timetable.html) · [Customizing Dag Scheduling with Timetables](https://airflow.apache.org/docs/apache-airflow/stable/howto/timetable.html)
- [Airflow Catchup & Backfill — Demystified](https://medium.com/nerd-for-tech/airflow-catchup-backfill-demystified-355def1b6f92) · [How to prevent Airflow from backfilling old DAG runs](https://mikulskibartosz.name/prevent-airflow-backfilling)
- [Time Zones — Airflow docs](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/timezone.html) · [Incorrect DAG scheduling after DST (#7999)](https://github.com/apache/airflow/issues/7999) · [DST scheduler crash (#30088)](https://github.com/apache/airflow/issues/30088) · [Dag blocked on winter time change (#35558)](https://github.com/apache/airflow/issues/35558)
