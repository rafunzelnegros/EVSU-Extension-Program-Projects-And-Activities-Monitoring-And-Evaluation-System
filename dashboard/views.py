from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Max
from django.http import HttpResponseForbidden, FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .models import *
from .forms import *

UNIT_FIELDS = {
    'SAAD': 'saad', 'SAS': 'sas', 'SAME': 'same', 'SOT': 'sot', 'SOE': 'soe', 'SOED': 'soed',
    'BURAUEN': 'burauen', 'CARIGARA': 'carigara', 'DULAG': 'dulag', 'ORMOC': 'ormoc', 'TANAUAN': 'tanauan'
}


def prof(user):
    try:
        return user.profile
    except Exception:
        return None


def role(user):
    if user.is_superuser:
        return 'DIRECTOR'
    profile = prof(user)
    return profile.role if profile else ''


def is_director(user):
    return role(user) == 'DIRECTOR'


def is_manager(user):
    return role(user) in ('DIRECTOR', 'ADMIN')


def unit_for(user):
    profile = prof(user)
    return profile.unit if profile else ''


def log(user, action, details=''):
    ActivityLog.objects.create(actor=user, action=action, details=details)


def current_quarter():
    return ((timezone.localdate().month - 1) // 3) + 1


def allowed_q(user, quarter):
    return is_director(user) or quarter <= current_quarter()


def parse_number(value, percentage=False):
    raw = (value or '').strip()
    if raw == '':
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ValueError('Only numerical values are allowed.')
    if value < 0:
        raise ValueError('Values cannot be negative.')
    if not percentage and value != value.to_integral_value():
        raise ValueError('This indicator accepts whole numbers only.')
    return value


def scoped_ppas(user):
    qs = ExtensionPPA.objects.all()
    if not is_manager(user):
        unit = unit_for(user)
        qs = qs.filter(implementing_unit=unit) if unit else qs.none()
    return qs


def scoped_partnerships(user):
    qs = Partnership.objects.all()
    if not is_manager(user):
        qs = qs.filter(created_by=user)
    return qs


def notify(user, title, message, link=''):
    Notification.objects.create(user=user, title=title, message=message, link=link)


def taep_rows(report, user):
    director_mode = (report.unit == '') if report else is_director(user)
    unit = '' if director_mode else (report.unit if report else unit_for(user))
    units = UNITS if director_mode else [(unit, dict(UNITS).get(unit, unit))]
    output = []

    for indicator in ExtensionIndicator.objects.filter(active=True).order_by('order'):
        quarters = []
        for q in range(1, 5):
            entry = report.quarter_entries.filter(indicator=indicator, quarter=q).first() if report else None
            values = {code: (getattr(entry, UNIT_FIELDS[code]) if entry else None) for code, _ in units}
            quarters.append({
                'q': q,
                'entry': entry,
                'target': entry.target if entry else None,
                'vals': values,
                'total': entry.total if entry else 0,
                'locked': not allowed_q(user, q),
            })
        meta = report.indicator_meta.filter(indicator=indicator).first() if report else None
        target_total = sum((q['target'] or 0) for q in quarters)
        accomplishment_total = sum((sum((v or 0) for v in q['vals'].values())) for q in quarters)
        output.append({
            'indicator': indicator, 'quarters': quarters, 'meta': meta,
            'target_total': target_total, 'accomplishment_total': accomplishment_total,
        })
    return output, units, director_mode


def save_taep(request, report):
    rows, units, _ = taep_rows(report, request.user)
    for row in rows:
        indicator = row['indicator']
        meta, _ = TaepIndicatorMeta.objects.get_or_create(report=report, indicator=indicator)
        meta.remarks = request.POST.get(f'remarks_{indicator.pk}', '').strip()
        uploaded = request.FILES.get(f'mov_{indicator.pk}')
        if uploaded:
            meta.mov_pdf = uploaded
            meta.uploaded_by = request.user
        meta.full_clean()
        meta.save()

        for q in range(1, 5):
            entry, _ = TaepQuarterEntry.objects.get_or_create(report=report, indicator=indicator, quarter=q)
            if allowed_q(request.user, q):
                entry.target = parse_number(request.POST.get(f'target_{indicator.pk}_{q}'), indicator.is_percentage)
                for code, _label in units:
                    value = parse_number(request.POST.get(f'value_{indicator.pk}_{q}_{code}'), indicator.is_percentage)
                    setattr(entry, UNIT_FIELDS[code], value)
            entry.save()


@login_required
def dashboard(request):
    ppas = scoped_ppas(request.user)
    programs = ppas.filter(type='PROGRAM')
    projects = ppas.filter(type='PROJECT')

    status = {
        'programs': {
            'approved': programs.filter(approved=True).count(),
            'board': programs.filter(board_confirmed=True).count(),
            'ongoing': programs.filter(status='ONGOING').count(),
            'inactive': programs.filter(status='INACTIVE').count(),
            'terminated': programs.filter(status='TERMINATED').count(),
        },
        'projects': {
            'approved': projects.filter(approved=True).count(),
            'board': projects.filter(board_confirmed=True).count(),
            'ongoing': projects.filter(status='ONGOING').count(),
            'inactive': projects.filter(status='INACTIVE').count(),
            'terminated': projects.filter(status='TERMINATED').count(),
        },
    }

    chart_values = {
        'approved': status['programs']['approved'] + status['projects']['approved'],
        'board': status['programs']['board'] + status['projects']['board'],
        'ongoing': status['programs']['ongoing'] + status['projects']['ongoing'],
        'inactive': status['programs']['inactive'] + status['projects']['inactive'],
        'terminated': status['programs']['terminated'] + status['projects']['terminated'],
    }
    chart_sum = sum(chart_values.values())
    chart_colors = {
        'approved': '#7b1830',
        'board': '#e5a900',
        'ongoing': '#a34a5d',
        'terminated': '#5b1020',
        'inactive': '#b9a99f',
    }
    chart_labels = {
        'approved': 'Approved',
        'board': 'Board Confirmed',
        'ongoing': 'On-going',
        'terminated': 'Terminated',
        'inactive': 'Inactive',
    }
    chart_segments = []
    offset = Decimal('0')
    for key in ['approved', 'board', 'ongoing', 'terminated', 'inactive']:
        value = chart_values[key]
        pct = (Decimal(value) / Decimal(chart_sum) * Decimal('100')) if chart_sum else Decimal('0')
        chart_segments.append({
            'key': key,
            'label': chart_labels[key],
            'value': value,
            'pct': round(pct, 4),
            'rest': round(Decimal('100') - pct, 4),
            'offset': round(offset, 4),
            'color': chart_colors[key],
        })
        offset += pct

    partnerships_qs = scoped_partnerships(request.user)
    counts = {
        'internal': ppas.filter(internally_assessed=True).count(),
        'external': ppas.filter(externally_assessed=True).count(),
        # The source sheet has no separate Agreement Type field. For the
        # dashboard, confirmed MOA/MOU is inferred from the Remarks text.
        'moa': partnerships_qs.filter(board_confirmed=True, remarks__icontains='MOA').count(),
        'mou': partnerships_qs.filter(board_confirmed=True, remarks__icontains='MOU').count(),
        'faculty_m': sum(x.faculty_male for x in ppas),
        'faculty_f': sum(x.faculty_female for x in ppas),
        'staff_m': sum(x.staff_male for x in ppas),
        'staff_f': sum(x.staff_female for x in ppas),
        'student_m': sum(x.student_male for x in ppas),
        'student_f': sum(x.student_female for x in ppas),
    }
    personnel_raw = [
        ('Faculty', counts['faculty_m'], counts['faculty_f']),
        ('Staff', counts['staff_m'], counts['staff_f']),
        ('Students', counts['student_m'], counts['student_f']),
    ]
    personnel_max = max([v for _label, male, female in personnel_raw for v in (male, female)] or [0])
    personnel_scale = max(personnel_max, 1)
    personnel_chart = [
        {
            'label': label,
            'male': male,
            'female': female,
            'male_pct': round((male / personnel_scale) * 100, 2),
            'female_pct': round((female / personnel_scale) * 100, 2),
        }
        for label, male, female in personnel_raw
    ]
    personnel_ticks = [
        {'label': personnel_max, 'pct': 100},
        {'label': round(personnel_max * .75), 'pct': 75},
        {'label': round(personnel_max * .50), 'pct': 50},
        {'label': round(personnel_max * .25), 'pct': 25},
        {'label': 0, 'pct': 0},
    ]

    partnership_counts = {code: partnerships_qs.filter(status='ACTIVE', partner_type=code).count() for code, _ in Partnership.PARTNER_TYPES}
    partnership_max = max(partnership_counts.values(), default=0)
    partnership_scale = max(partnership_max, 1)
    partnership_chart = [
        {
            'code': code,
            'label': label,
            'value': partnership_counts.get(code, 0),
            'pct': round((partnership_counts.get(code, 0) / partnership_scale) * 100, 2),
        }
        for code, label in Partnership.PARTNER_TYPES
    ]

    chosen = [int(x) for x in request.GET.getlist('indicator') if x.isdigit()][:4] or [1, 2, 3, 4]
    allinds = ExtensionIndicator.objects.filter(active=True).order_by('order')
    year = timezone.localdate().year
    tables = []
    dashboard_units = UNITS if is_manager(request.user) else [(unit_for(request.user), dict(UNITS).get(unit_for(request.user), unit_for(request.user)))]

    approved_entries = TaepQuarterEntry.objects.filter(report__status='APPROVED', report__budget_year=year)
    if not is_manager(request.user):
        approved_entries = approved_entries.filter(report__unit=unit_for(request.user))

    for indicator in allinds.filter(order__in=chosen).order_by('order'):
        quarters = []
        for q in range(1, 5):
            vals = {code: Decimal('0') for code, _ in dashboard_units}
            target = Decimal('0')
            for entry in approved_entries.filter(indicator=indicator, quarter=q):
                target += entry.target or 0
                for code, _label in dashboard_units:
                    vals[code] += getattr(entry, UNIT_FIELDS[code]) or 0
            quarters.append({'q': q, 'target': target, 'vals': vals, 'total': sum(vals.values())})
        tables.append({'indicator': indicator, 'quarters': quarters})

    latest_candidates = [
        TaepReport.objects.aggregate(x=Max('updated_at'))['x'],
        QparReport.objects.aggregate(x=Max('updated_at'))['x'],
        Partnership.objects.aggregate(x=Max('updated_at'))['x'],
        ExtensionPPA.objects.aggregate(x=Max('updated_at'))['x'],
    ]
    latest = max([x for x in latest_candidates if x], default=None)

    return render(request, 'dashboard/dashboard.html', {
        'active_page': 'dashboard',
        'status_table': status,
        'chart_values': chart_values,
        'chart_segments': chart_segments,
        'chart_sum': chart_sum,
        'counts': counts,
        'personnel_chart': personnel_chart,
        'personnel_ticks': personnel_ticks,
        'partnership_counts': partnership_counts,
        'partnership_chart': partnership_chart,
        'taep_tables': tables,
        'dashboard_units': dashboard_units,
        'all_indicators': allinds,
        'chosen': chosen,
        'year': year,
        'latest_update': latest,
        'end_user_view': not is_manager(request.user),
    })


@login_required
def taep_list(request):
    reports_qs = TaepReport.objects.filter(owner=request.user)
    return render(request, 'dashboard/taep_list.html', {'active_page': 'taep', 'reports': reports_qs})


@login_required
def taep_add(request):
    unit = '' if is_director(request.user) else unit_for(request.user)
    if not is_director(request.user) and not unit:
        messages.error(request, 'Your account has no assigned school/campus.')
        return redirect('taep_list')

    if request.method == 'POST':
        try:
            year = int(request.POST.get('budget_year') or timezone.localdate().year)
        except ValueError:
            messages.error(request, 'Budget Year must be a valid year.')
            return redirect('taep_add')
        if TaepReport.objects.filter(budget_year=year, unit=unit).exists():
            messages.error(request, 'A TAEP report already exists for that Budget Year and unit.')
            return redirect('taep_list')

        report = TaepReport.objects.create(budget_year=year, owner=request.user, unit=unit, status='DRAFT')
        try:
            save_taep(request, report)
        except Exception as exc:
            report.delete()
            messages.error(request, f'Could not save report: {exc}')
            return redirect('taep_add')

        if request.POST.get('action') == 'submit':
            report.submitted_at = timezone.now()
            if is_director(request.user):
                report.status = 'APPROVED'
                report.approved_at = timezone.now()
                log(request.user, 'Created approved TAEP', str(report))
            else:
                report.status = 'PENDING'
                log(request.user, 'Submitted TAEP', str(report))
            report.save()
        else:
            log(request.user, 'Saved TAEP draft', str(report))
        return redirect('taep_list')

    rows, units, director_mode = taep_rows(None, request.user)
    return render(request, 'dashboard/taep_form.html', {
        'active_page': 'taep', 'report': None, 'rows': rows, 'units': units,
        'director_mode': director_mode, 'default_year': timezone.localdate().year,
        'current_quarter': current_quarter(),
    })


@login_required
def taep_edit(request, pk):
    report = get_object_or_404(TaepReport, pk=pk)
    if report.owner_id != request.user.id:
        return HttpResponseForbidden('Only the creator can edit this report.')
    if report.status not in ('DRAFT', 'RETURNED'):
        return redirect('taep_view', pk=pk)

    if request.method == 'POST':
        try:
            year = int(request.POST.get('budget_year') or report.budget_year)
            if TaepReport.objects.exclude(pk=report.pk).filter(budget_year=year, unit=report.unit).exists():
                messages.error(request, 'Another report already uses that Budget Year.')
                return redirect('taep_edit', pk=pk)
            report.budget_year = year
            save_taep(request, report)
        except Exception as exc:
            messages.error(request, f'Could not save report: {exc}')
            return redirect('taep_edit', pk=pk)

        if request.POST.get('action') == 'submit':
            report.submitted_at = timezone.now()
            if is_director(request.user):
                report.status = 'APPROVED'
                report.approved_at = timezone.now()
                log(request.user, 'Updated approved TAEP', str(report))
            else:
                report.status = 'PENDING'
                log(request.user, 'Submitted TAEP', str(report))
        else:
            report.status = 'DRAFT'
            log(request.user, 'Saved TAEP draft', str(report))
        report.save()
        return redirect('taep_list')

    rows, units, director_mode = taep_rows(report, request.user)
    return render(request, 'dashboard/taep_form.html', {
        'active_page': 'taep', 'report': report, 'rows': rows, 'units': units,
        'director_mode': director_mode, 'default_year': report.budget_year,
        'current_quarter': current_quarter(),
    })


@login_required
def taep_delete(request, pk):
    report = get_object_or_404(TaepReport, pk=pk, owner=request.user)
    if report.status != 'DRAFT':
        messages.error(request, 'Only drafts can be deleted.')
        return redirect('taep_list')
    if request.method == 'POST':
        label = str(report)
        report.delete()
        log(request.user, 'Deleted TAEP draft', label)
    return redirect('taep_list')


@login_required
def taep_view(request, pk, review=False):
    report = get_object_or_404(TaepReport, pk=pk)
    if review:
        if not is_manager(request.user):
            return HttpResponseForbidden()
    elif report.owner_id != request.user.id:
        return HttpResponseForbidden()
    rows, units, director_mode = taep_rows(report, request.user if report.owner_id == request.user.id else report.owner)
    return render(request, 'dashboard/taep_view.html', {
        'active_page': 'reports' if review else 'taep', 'report': report,
        'rows': rows, 'units': units, 'review_mode': review, 'director_mode': director_mode,
    })


@login_required
def taep_review(request, pk):
    return taep_view(request, pk, True)


def next_rev(year, quarter, unit):
    return (QparReport.objects.filter(year=year, quarter=quarter, unit=unit).aggregate(x=Max('revision_no'))['x'] or 0) + 1


def save_qpar(request, report):
    report.entries.all().delete()
    units = UNITS if report.unit == '' else [(report.unit, dict(UNITS).get(report.unit, report.unit))]
    for idx, name in enumerate(request.POST.getlist('indicator')):
        name = name.strip()
        if not name:
            continue
        entry = QparEntry(report=report, indicator=name, target=parse_number(request.POST.get(f'target_{idx}'), False), remarks=request.POST.get(f'remarks_{idx}', '').strip())
        for code, _label in units:
            setattr(entry, UNIT_FIELDS[code], parse_number(request.POST.get(f'value_{idx}_{code}'), False))
        uploaded = request.FILES.get(f'mov_{idx}')
        if uploaded:
            entry.mov_pdf = uploaded
        entry.full_clean()
        entry.save()


@login_required
def qpar_list(request):
    reports_qs = QparReport.objects.filter(owner=request.user)
    return render(request, 'dashboard/qpar_list.html', {'active_page': 'qpar', 'reports': reports_qs})


@login_required
def qpar_add(request):
    unit = '' if is_director(request.user) else unit_for(request.user)
    if not is_director(request.user) and not unit:
        messages.error(request, 'Your account has no assigned school/campus.')
        return redirect('qpar_list')

    if request.method == 'POST':
        try:
            year = int(request.POST.get('year') or timezone.localdate().year)
            quarter = int(request.POST.get('quarter') or 1)
            if not is_director(request.user) and quarter > current_quarter() and year >= timezone.localdate().year:
                raise ValueError('You cannot submit a future quarter.')
            report = QparReport.objects.create(
                year=year, quarter=quarter, revision_no=next_rev(year, quarter, unit), owner=request.user,
                unit=unit, title=request.POST.get('title', '').strip(), status='DRAFT'
            )
            save_qpar(request, report)
        except Exception as exc:
            if 'report' in locals() and report.pk:
                report.delete()
            messages.error(request, f'Could not save QPAR: {exc}')
            return redirect('qpar_add')

        if request.POST.get('action') == 'submit':
            report.submitted_at = timezone.now()
            if is_director(request.user):
                report.status = 'APPROVED'
                report.approved_at = timezone.now()
                log(request.user, 'Created approved QPAR', str(report))
            else:
                report.status = 'PENDING'
                log(request.user, 'Submitted QPAR', str(report))
            report.save()
        else:
            log(request.user, 'Saved QPAR draft', str(report))
        return redirect('qpar_list')

    return render(request, 'dashboard/qpar_form.html', {
        'active_page': 'qpar', 'report': None,
        'units': UNITS if unit == '' else [(unit, dict(UNITS).get(unit, unit))],
        'default_year': timezone.localdate().year, 'current_quarter': current_quarter(),
    })


@login_required
def qpar_edit(request, pk):
    report = get_object_or_404(QparReport, pk=pk)
    if report.owner_id != request.user.id:
        return HttpResponseForbidden()
    if report.status not in ('DRAFT', 'RETURNED'):
        return redirect('qpar_view', pk=pk)

    if request.method == 'POST':
        try:
            report.year = int(request.POST.get('year') or report.year)
            report.quarter = int(request.POST.get('quarter') or report.quarter)
            report.title = request.POST.get('title', '').strip()
            save_qpar(request, report)
        except Exception as exc:
            messages.error(request, f'Could not save QPAR: {exc}')
            return redirect('qpar_edit', pk=pk)

        if request.POST.get('action') == 'submit':
            report.submitted_at = timezone.now()
            if is_director(request.user):
                report.status = 'APPROVED'
                report.approved_at = timezone.now()
                log(request.user, 'Updated approved QPAR', str(report))
            else:
                report.status = 'PENDING'
                log(request.user, 'Submitted QPAR', str(report))
        else:
            report.status = 'DRAFT'
            log(request.user, 'Saved QPAR draft', str(report))
        report.save()
        return redirect('qpar_list')

    units = UNITS if report.unit == '' else [(report.unit, dict(UNITS).get(report.unit, report.unit))]
    return render(request, 'dashboard/qpar_form.html', {
        'active_page': 'qpar', 'report': report, 'units': units, 'default_year': report.year,
        'current_quarter': current_quarter(),
    })


@login_required
def qpar_delete(request, pk):
    report = get_object_or_404(QparReport, pk=pk, owner=request.user)
    if report.status != 'DRAFT':
        messages.error(request, 'Only drafts can be deleted.')
        return redirect('qpar_list')
    if request.method == 'POST':
        label = str(report)
        report.delete()
        log(request.user, 'Deleted QPAR draft', label)
    return redirect('qpar_list')


@login_required
def qpar_view(request, pk, review=False):
    report = get_object_or_404(QparReport, pk=pk)
    if review:
        if not is_manager(request.user):
            return HttpResponseForbidden()
    elif report.owner_id != request.user.id:
        return HttpResponseForbidden()
    return render(request, 'dashboard/qpar_view.html', {
        'active_page': 'reports' if review else 'qpar', 'report': report, 'review_mode': review,
        'units': UNITS if report.unit == '' else [(report.unit, dict(UNITS).get(report.unit, report.unit))],
    })


@login_required
def qpar_review(request, pk):
    return qpar_view(request, pk, True)


@login_required
def reports(request):
    if not is_manager(request.user):
        return HttpResponseForbidden()
    return render(request, 'dashboard/reports.html', {
        'active_page': 'reports',
        'taep': TaepReport.objects.filter(status='PENDING').exclude(owner=request.user),
        'qpar': QparReport.objects.filter(status='PENDING').exclude(owner=request.user),
    })


@login_required
def report_action(request, kind, pk, action):
    if not is_director(request.user):
        return HttpResponseForbidden()
    model = TaepReport if kind == 'taep' else QparReport
    obj = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        if action == 'approve':
            obj.status = 'APPROVED'
            obj.approved_at = timezone.now()
            obj.returned_at = None
            obj.director_comment = ''
            title = f'{kind.upper()} approved'
            msg = f'Your {obj} was approved by the Director.'
            log(request.user, f'Approved {kind.upper()}', str(obj))
        elif action == 'return':
            comment = (request.POST.get('comment') or '').strip()
            if not comment:
                messages.error(request, 'A return comment is required.')
                return redirect('reports')
            obj.status = 'RETURNED'
            obj.returned_at = timezone.now()
            obj.director_comment = comment
            title = f'{kind.upper()} returned'
            msg = f'Your {obj} was returned. Comment: {comment}'
            log(request.user, f'Returned {kind.upper()}', comment)
        else:
            return HttpResponseForbidden()
        obj.save()
        link = reverse('taep_view', args=[obj.pk]) if kind == 'taep' else reverse('qpar_view', args=[obj.pk])
        notify(obj.owner, title, msg, link)
    return redirect('reports')


@login_required
def notifications(request):
    items = Notification.objects.filter(user=request.user)
    if request.method == 'POST':
        items.filter(is_read=False).update(is_read=True)
        return redirect('notifications')
    return render(request, 'dashboard/notifications.html', {'active_page': 'notifications', 'notifications': items})


@login_required
def notification_open(request, pk):
    item = get_object_or_404(Notification, pk=pk, user=request.user)
    item.is_read = True
    item.save(update_fields=['is_read'])
    return redirect(item.link or 'notifications')


@login_required
def pdf_view(request, kind, pk):
    if kind == 'taep':
        obj = get_object_or_404(TaepIndicatorMeta, pk=pk)
    elif kind == 'qpar':
        obj = get_object_or_404(QparEntry, pk=pk)
    else:
        raise Http404()
    report = obj.report
    if not is_manager(request.user) and report.owner_id != request.user.id:
        return HttpResponseForbidden()
    file_field = obj.mov_pdf
    if not file_field:
        raise Http404('No PDF uploaded.')
    return FileResponse(file_field.open('rb'), content_type='application/pdf', filename=file_field.name.split('/')[-1])


@login_required
def partnerships(request):
    form = PartnershipForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        log(request.user, 'Added partnership', obj.stakeholder_name)
        return redirect('partnerships')
    rows = Partnership.objects.all().order_by('-updated_at') if is_manager(request.user) else Partnership.objects.filter(created_by=request.user).order_by('-updated_at')
    return render(request, 'dashboard/partnerships.html', {'active_page': 'data', 'rows': rows, 'form': form})


@login_required
def partnership_edit(request, pk):
    obj = get_object_or_404(Partnership, pk=pk)
    if not is_manager(request.user) and obj.created_by_id != request.user.id:
        return HttpResponseForbidden()
    form = PartnershipForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log(request.user, 'Edited partnership', obj.stakeholder_name)
        return redirect('partnerships')
    return render(request, 'dashboard/simple_form.html', {'active_page': 'data', 'title': 'Edit Partnership', 'form': form})


@login_required
def ppas(request):
    assigned_unit = unit_for(request.user)
    initial = {'implementing_unit': assigned_unit} if not is_manager(request.user) else None
    form = ExtensionPPAForm(request.POST or None, initial=initial)
    if not is_manager(request.user) and 'implementing_unit' in form.fields:
        form.fields['implementing_unit'].disabled = True
        form.fields['implementing_unit'].help_text = 'Your account can only encode records for its assigned school/campus.'
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        if not is_manager(request.user):
            obj.implementing_unit = assigned_unit
        obj.created_by = request.user
        obj.save()
        log(request.user, 'Added extension PPA', obj.title)
        return redirect('ppas')
    rows = ExtensionPPA.objects.all().order_by('-updated_at') if is_manager(request.user) else ExtensionPPA.objects.filter(implementing_unit=assigned_unit).order_by('-updated_at')
    return render(request, 'dashboard/ppas.html', {'active_page': 'data', 'rows': rows, 'form': form})


@login_required
def ppa_edit(request, pk):
    obj = get_object_or_404(ExtensionPPA, pk=pk)
    assigned_unit = unit_for(request.user)
    if not is_manager(request.user) and obj.implementing_unit != assigned_unit:
        return HttpResponseForbidden()
    form = ExtensionPPAForm(request.POST or None, instance=obj)
    if not is_manager(request.user) and 'implementing_unit' in form.fields:
        form.fields['implementing_unit'].disabled = True
    if request.method == 'POST' and form.is_valid():
        edited = form.save(commit=False)
        if not is_manager(request.user):
            edited.implementing_unit = assigned_unit
        edited.save()
        log(request.user, 'Edited extension PPA', obj.title)
        return redirect('ppas')
    return render(request, 'dashboard/simple_form.html', {'active_page': 'data', 'title': 'Edit Extension Program / Project / Activity', 'form': form})


@login_required
def manage_users(request):
    if not is_director(request.user):
        return HttpResponseForbidden()
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        rv = form.cleaned_data['role']
        uv = form.cleaned_data['unit']
        school = {'SAAD', 'SAS', 'SAME', 'SOT', 'SOE', 'SOED'}
        campus = {'BURAUEN', 'CARIGARA', 'DULAG', 'ORMOC', 'TANAUAN'}
        if rv == 'SCHOOL' and uv not in school:
            form.add_error('unit', 'Choose one of the six schools.')
        elif rv == 'CAMPUS' and uv not in campus:
            form.add_error('unit', 'Choose one of the five campuses.')
        elif rv == 'ADMIN' and uv:
            form.add_error('unit', 'Admin Staff should not be assigned to a school/campus.')
        else:
            user = User.objects.create_user(
                username=form.cleaned_data['username'], password=form.cleaned_data['password'], email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'], last_name=form.cleaned_data['last_name']
            )
            UserProfile.objects.create(user=user, role=rv, unit=uv)
            log(request.user, 'Created user', user.username)
            return redirect('manage_users')
    users = User.objects.filter(is_superuser=False).select_related('profile').order_by('username')
    return render(request, 'dashboard/manage_users.html', {'active_page': 'admin', 'users': users, 'form': form})


@login_required
def user_edit(request, pk):
    if not is_director(request.user):
        return HttpResponseForbidden()
    user = get_object_or_404(User, pk=pk, is_superuser=False)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    form = UserEditForm(request.POST or None, initial={
        'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email,
        'role': profile.role, 'unit': profile.unit, 'is_active': user.is_active,
    })
    if request.method == 'POST' and form.is_valid():
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.email = form.cleaned_data['email']
        user.is_active = form.cleaned_data['is_active']
        user.save()
        profile.role = form.cleaned_data['role']
        profile.unit = form.cleaned_data['unit']
        profile.save()
        log(request.user, 'Edited user', user.username)
        return redirect('manage_users')
    return render(request, 'dashboard/simple_form.html', {'active_page': 'admin', 'title': f'Edit User — {user.username}', 'form': form})


@login_required
def activity_logs(request):
    if not is_director(request.user):
        return HttpResponseForbidden()
    return render(request, 'dashboard/activity_logs.html', {'active_page': 'admin', 'logs': ActivityLog.objects.select_related('actor')[:500]})
