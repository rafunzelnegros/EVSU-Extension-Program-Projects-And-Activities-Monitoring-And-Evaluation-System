from django.utils import timezone
from .models import PPA, Unit


def quarter_for_date(d):
    return ((d.month - 1) // 3) + 1 if d else None


def forecast_projects(year=None):
    """Forecast cumulative project starts with a simple least-squares linear trend.

    For the current year, only quarters that have already started are used to fit the
    trend, so future zeroes do not artificially pull the forecast down. This is an
    explainable planning forecast, not an AI certainty or a performance score.
    """
    year = year or timezone.localdate().year
    today = timezone.localdate()
    observed_q = ((today.month - 1) // 3) + 1 if year == today.year else 4
    if year > today.year:
        observed_q = 0

    results = []
    for unit in Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE):
        starts = [0, 0, 0, 0]
        for project in PPA.objects.filter(
            ppa_type=PPA.PROJECT,
            workflow_status=PPA.SAVED,
            unit=unit,
            start_date__year=year,
        ):
            q = quarter_for_date(project.start_date)
            if q:
                starts[q - 1] += 1

        cumulative = []
        running = 0
        for count in starts:
            running += count
            cumulative.append(running)

        fit_q = max(1, observed_q)
        xs = list(range(1, fit_q + 1))
        ys = cumulative[:fit_q]

        if observed_q == 0 or not ys or max(ys) == 0:
            slope = 0.0
            intercept = 0.0
        elif len(xs) == 1:
            # With one observed quarter, use the current cumulative count as a
            # cautious per-quarter pace instead of pretending to have a fitted line.
            slope = float(ys[0])
            intercept = 0.0
        else:
            xm = sum(xs) / len(xs)
            ym = sum(ys) / len(ys)
            denom = sum((x - xm) ** 2 for x in xs) or 1
            slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denom
            intercept = ym - slope * xm

        last_actual = cumulative[observed_q - 1] if observed_q else 0
        plot_values = []
        for q in range(1, 5):
            if observed_q and q <= observed_q:
                value = cumulative[q - 1]
            else:
                value = max(last_actual, round(intercept + slope * q))
            plot_values.append(max(0, int(value)))

        next_q = min(4, observed_q + 1) if observed_q else 1
        quarter_forecast = plot_values[next_q - 1]
        year_forecast = plot_values[3]

        results.append({
            'unit': unit,
            'actual': last_actual,
            'quarter_forecast': quarter_forecast,
            'year_forecast': year_forecast,
            'starts': starts,
            'cumulative': cumulative,
            'plot_values': plot_values,
            'observed_quarter': observed_q,
            'slope': round(slope, 3),
        })

    results.sort(key=lambda row: (-row['year_forecast'], -row['actual'], row['unit'].name))
    return results
