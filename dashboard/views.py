from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import *
from .models import *
from .services import forecast_projects


PHASES = {
    1: 'Needs assessment',
    2: 'Early project implementation',
    3: 'Middle project implementation',
    4: 'Late project implementation',
    5: 'Completion of project',
    6: 'Evaluation of output and outcome',
    7: 'Impact evaluation',
}


def get_profile(user):
    try:
        return user.evsu_profile
    except Exception:
        return None


def get_role(user):
    if user.is_superuser:
        return UserProfile.ME_HEAD
    p = get_profile(user)
    return p.role if p else ''


def require_roles(user, *roles):
    if get_role(user) not in roles:
        raise PermissionDenied


def unit_scope(user, qs):
    if get_role(user) == UserProfile.COORDINATOR:
        p = get_profile(user)
        return qs.filter(unit=p.unit) if p and p.unit else qs.none()
    return qs


def display_name(user):
    if not user:
        return ''
    return user.get_full_name().strip() or user.username


def formal_name(user):
    name = display_name(user)
    try:
        post = (user.evsu_profile.post_nominals or '').strip()
    except Exception:
        post = ''
    return f'{name}, {post}' if name and post else name


def director_name():
    profile = UserProfile.objects.select_related('user').filter(
        role=UserProfile.DIRECTOR, user__is_active=True
    ).order_by('user__last_name', 'user__first_name', 'user__username').first()
    return formal_name(profile.user) if profile else ''


def log(user, action, details=''):
    ActivityLog.objects.create(actor=user, action=action, details=details)


def parse_bool(value):
    return str(value).lower() in ('1', 'true', 'yes', 'on')


def dec(value):
    try:
        return Decimal(value) if str(value).strip() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def quarter_bounds(year, quarter):
    starts = {1: 1, 2: 4, 3: 7, 4: 10}
    start_month = starts[int(quarter)]
    start = date(int(year), start_month, 1)
    if int(quarter) == 4:
        end = date(int(year), 12, 31)
    else:
        end = date(int(year), start_month + 3, 1) - timedelta(days=1)
    return start, end


def _smooth_svg_path(points):
    """Return a smooth cubic SVG path through four chart points."""
    if not points:
        return ''
    if len(points) == 1:
        x, y = points[0]
        return f'M {x:.1f} {y:.1f}'
    d = [f'M {points[0][0]:.1f} {points[0][1]:.1f}']
    for i in range(len(points) - 1):
        x0, y0 = points[i - 1] if i > 0 else points[i]
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        x3, y3 = points[i + 2] if i + 2 < len(points) else points[i + 1]
        c1x = x1 + (x2 - x0) / 6.0
        c1y = y1 + (y2 - y0) / 6.0
        c2x = x2 - (x3 - x1) / 6.0
        c2y = y2 - (y3 - y1) / 6.0
        d.append(f'C {c1x:.1f} {c1y:.1f}, {c2x:.1f} {c2y:.1f}, {x2:.1f} {y2:.1f}')
    return ' '.join(d)


def _project_operational_status(project, today):
    latest = project.quarterly_monitoring_reports.order_by('-period_end', '-updated_at').first()
    if project.termination_date or (latest and latest.project_status == QuarterlyMonitoringReport.TERMINATED):
        return 'terminated'
    if project.auto_inactive or (latest and latest.project_status == QuarterlyMonitoringReport.INACTIVE):
        return 'inactive'
    if project.is_completed:
        return 'completed'
    if latest and latest.project_status == QuarterlyMonitoringReport.ONGOING:
        return 'ongoing'
    if project.start_date and project.end_date and project.start_date <= today <= project.end_date:
        return 'ongoing'
    if project.end_date and project.end_date < today:
        return 'inactive'
    return 'pending'


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')
    return render(request, 'dashboard/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    role = get_role(request.user)
    # Dashboard metrics intentionally ignore drafts. Draft PPAs are workspace records only.
    ppas = unit_scope(request.user, PPA.objects.filter(workflow_status=PPA.SAVED)).select_related('unit')
    projects = ppas.filter(ppa_type=PPA.PROJECT).prefetch_related('activities', 'quarterly_monitoring_reports', 'impact_assessments')
    programs = ppas.filter(ppa_type=PPA.PROGRAM)
    activities = Activity.objects.filter(project__in=projects)

    today = timezone.localdate()
    selected_year = request.GET.get('year')
    selected_quarter = request.GET.get('quarter')
    try:
        selected_year = int(selected_year) if selected_year else today.year
    except (TypeError, ValueError):
        selected_year = today.year
    try:
        selected_quarter = int(selected_quarter) if selected_quarter else ((today.month - 1) // 3) + 1
    except (TypeError, ValueError):
        selected_quarter = ((today.month - 1) // 3) + 1
    if selected_quarter not in (1, 2, 3, 4):
        selected_quarter = ((today.month - 1) // 3) + 1

    def status_counts(qs):
        data = {'approved': 0, 'board_confirmed': 0, 'ongoing': 0, 'inactive': 0, 'terminated': 0}
        for obj in qs:
            if obj.workflow_status == PPA.SAVED:
                data['approved'] += 1
            if obj.board_confirmed:
                data['board_confirmed'] += 1
            if obj.ppa_type == PPA.PROJECT:
                status = _project_operational_status(obj, today)
                if status in data:
                    data[status] += 1
            elif obj.termination_date:
                data['terminated'] += 1
            elif obj.start_date and obj.end_date and obj.start_date <= today <= obj.end_date:
                data['ongoing'] += 1
            elif obj.end_date and obj.end_date < today:
                data['inactive'] += 1
        return data

    status_programs = status_counts(programs)
    status_projects = status_counts(projects)
    summary_counts = {k: status_programs[k] + status_projects[k] for k in status_programs}
    summary_total = programs.count() + projects.count()

    operational = [summary_counts['ongoing'], summary_counts['terminated'], summary_counts['inactive']]
    operational_total = sum(operational)
    if operational_total:
        p1 = round(operational[0] / operational_total * 100, 2)
        p2 = round(p1 + operational[1] / operational_total * 100, 2)
        summary_gradient = f'conic-gradient(#b05066 0 {p1}%, #781328 {p1}% {p2}%, #cfc6c1 {p2}% 100%)'
    else:
        summary_gradient = 'conic-gradient(#e8e2de 0 100%)'

    assessment_counts = {
        'internal': ImpactAssessment.objects.filter(project__in=projects, assessment_type=ImpactAssessment.INTERNAL, date__isnull=False).count(),
        'external': ImpactAssessment.objects.filter(project__in=projects, assessment_type=ImpactAssessment.EXTERNAL, date__isnull=False).count(),
    }
    board_counts = {
        'confirmed': ppas.filter(board_confirmed=True).count(),
        'moa_mou': ppas.filter(with_moa_mou=True).count(),
    }

    partner_labels = [('LGU', 'LGU'), ('INDUSTRY', 'Industry'), ('SME', 'SME'), ('OTHERS', 'Other')]
    partner_raw = [(code, label, ppas.filter(partner_category=code).count()) for code, label in partner_labels]
    partner_max = max([n for _, _, n in partner_raw] or [1]) or 1
    partnerships = [
        {'label': label, 'count': n, 'percent': round((n / partner_max) * 100, 1) if n else 0}
        for _, label, n in partner_raw
    ]

    counts = {
        'programs': programs.count(),
        'projects': projects.count(),
        'activities': activities.count(),
        'active': status_projects['ongoing'],
        'drafts': ppas.filter(workflow_status=PPA.DRAFT).count(),
    }
    termination_due = sum(1 for x in projects if x.termination_eligible)
    impact_due = sum(1 for x in projects if x.impact_assessment_eligible and x.impact_assessments.count() < 2)

    # Dashboard TAEP always reads the SAVED QPAR record for the selected period.
    # Coordinator sees only the Total for their own unit; site-wide roles see each unit plus total.
    taep = []
    units = Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE)
    if role == UserProfile.COORDINATOR:
        prof = get_profile(request.user)
        units = units.filter(pk=prof.unit_id) if prof and prof.unit_id else units.none()
    for ind in ExtensionIndicator.objects.filter(active=True, order__lte=4):
        vals = []
        for unit in units:
            value = QparIndicatorValue.objects.filter(
                submission__unit=unit,
                submission__year=selected_year,
                submission__quarter=selected_quarter,
                submission__status=QparSubmission.SAVED,
                indicator=ind,
            ).aggregate(x=Sum('accomplishment'))['x'] or Decimal('0')
            vals.append((unit, value))
        total = sum((value for _, value in vals), Decimal('0'))
        taep.append((ind, vals, total))

    forecast = []
    prediction_top = None
    prediction_year = today.year
    try:
        prediction_year = int(request.GET.get('prediction_year') or today.year)
    except (TypeError, ValueError):
        prediction_year = today.year
    if role in (UserProfile.DIRECTOR, UserProfile.ADMIN_STAFF):
        forecast = forecast_projects(prediction_year)
        prediction_top = forecast[0] if forecast else None
        # Show every school/campus on one smooth line chart.
        chart_max = max([max(row.get('plot_values', [0])) for row in forecast] or [1]) or 1
        x_positions = [8, 38, 68, 98]
        palette = ['#8b1535','#d5a300','#b05066','#5d6270','#8e7d6b','#3f7d6d','#8d5da7','#bf6a3d','#4c78a8','#7a8f3a','#a65b74']
        for index, row in enumerate(forecast):
            points = []
            for x, value in zip(x_positions, row.get('plot_values', [0, 0, 0, 0])):
                y = 90 - ((float(value) / chart_max) * 72)
                points.append((x, y))
            row['chart_path'] = _smooth_svg_path(points)
            row['chart_color'] = palette[index % len(palette)]

    return render(request, 'dashboard/dashboard.html', {
        'counts': counts,
        'termination_due': termination_due,
        'impact_due': impact_due,
        'taep': taep,
        'quarter': selected_quarter,
        'year': selected_year,
        'forecast': forecast,
        'prediction_top': prediction_top,
        'prediction_year': prediction_year,
        'status_programs': status_programs,
        'status_projects': status_projects,
        'summary_counts': summary_counts,
        'summary_total': summary_total,
        'summary_gradient': summary_gradient,
        'assessment_counts': assessment_counts,
        'board_counts': board_counts,
        'partnerships': partnerships,
    })


@login_required
def ppa_list(request):
    require_roles(request.user, UserProfile.COORDINATOR)
    rows = unit_scope(request.user, PPA.objects.all()).select_related('unit', 'umbrella_program').prefetch_related('activities')

    query = (request.GET.get('q') or '').strip()
    ppa_type = (request.GET.get('type') or '').strip().upper()
    status = (request.GET.get('status') or '').strip().upper()
    sort = request.GET.get('sort') or 'updated_desc'

    if query:
        rows = rows.filter(Q(title__icontains=query) | Q(umbrella_program__title__icontains=query))
    if ppa_type in (PPA.PROGRAM, PPA.PROJECT):
        rows = rows.filter(ppa_type=ppa_type)
        # Program/Project tabs represent finalized PPAs. Drafts are a separate
        # workspace and remain visible under All or the Draft filter.
        if status not in (PPA.DRAFT, PPA.SAVED):
            rows = rows.filter(workflow_status=PPA.SAVED)
    if status in (PPA.DRAFT, PPA.SAVED):
        rows = rows.filter(workflow_status=status)

    order_map = {
        'updated_desc': ('-updated_at', 'title'),
        'updated_asc': ('updated_at', 'title'),
        'title_asc': ('title',),
        'title_desc': ('-title',),
        'type': ('ppa_type', '-updated_at'),
    }
    rows = rows.order_by(*order_map.get(sort, order_map['updated_desc']))

    base_rows = unit_scope(request.user, PPA.objects.all())
    counts = {
        'all': base_rows.count(),
        'programs': base_rows.filter(ppa_type=PPA.PROGRAM, workflow_status=PPA.SAVED).count(),
        'projects': base_rows.filter(ppa_type=PPA.PROJECT, workflow_status=PPA.SAVED).count(),
        'drafts': base_rows.filter(workflow_status=PPA.DRAFT).count(),
    }
    return render(request, 'dashboard/ppa_list.html', {
        'rows': rows,
        'filter_q': query,
        'filter_type': ppa_type,
        'filter_status': status,
        'filter_sort': sort,
        'list_counts': counts,
    })


def _unit_for_post(request, key='unit'):
    if get_role(request.user) == UserProfile.COORDINATOR:
        p = get_profile(request.user)
        if not p or not p.unit:
            raise ValidationError('Your account has no assigned school/campus.')
        return p.unit
    uid = request.POST.get(key) or request.GET.get(key)
    return get_object_or_404(Unit, pk=uid) if uid else None


def _joined_repeater(data, name, prefix='', fallback=''):
    values = [v.strip() for v in data.getlist(prefix + name + '[]') if v.strip()]
    if values:
        return '\n'.join(values)
    return data.get(prefix + name, fallback)


def _assign_ppa_fields(obj, data, prefix=''):
    def g(name, default=''):
        return data.get(prefix + name, default)

    obj.notice_to_proceed_no = g('notice_to_proceed_no').strip()
    obj.special_order_no = g('special_order_no').strip()
    obj.title = g('title').strip()
    obj.proponents = _joined_repeater(data, 'proponents', prefix)
    obj.partner_category = g('partner_category')
    obj.partner_name = g('partner_name').strip()
    obj.with_moa_mou = parse_bool(g('with_moa_mou'))
    obj.board_confirmed = parse_bool(g('board_confirmed'))
    obj.board_resolution_no = g('board_resolution_no').strip()
    obj.board_resolution_date = g('board_resolution_date') or None
    obj.leader_name = g('leader_name').strip()
    obj.leader_position = g('leader_position').strip()
    obj.leader_contact = g('leader_contact').strip()
    obj.assistant_name = g('assistant_name').strip()
    obj.assistant_position = g('assistant_position').strip()
    obj.assistant_contact = g('assistant_contact').strip()
    obj.members = _joined_repeater(data, 'members', prefix)
    obj.clientele = g('clientele')
    obj.target_area = g('target_area').strip()
    obj.start_date = g('start_date') or None
    obj.end_date = g('end_date') or None
    obj.project_cost = dec(g('project_cost'))
    obj.funding_source = g('funding_source').strip()
    obj.urdea = g('urdea')
    # Kept for backward compatibility with older database rows. Structured SDGs
    # are saved in SustainableDevelopmentGoal records below.
    obj.sdgs = g('sdgs', '')
    return obj


def _save_sdgs(ppa, data, prefix='', replace=False):
    if replace:
        ppa.sdg_entries.all().delete()
    goals = data.getlist(prefix + 'sdg_goal[]')
    targets = data.getlist(prefix + 'sdg_target[]')
    descriptions = data.getlist(prefix + 'sdg_description[]')
    indicators = data.getlist(prefix + 'sdg_indicator[]')
    created = 0
    for i, goal in enumerate(goals):
        goal = (goal or '').strip()
        target = targets[i].strip() if i < len(targets) else ''
        description = descriptions[i] if i < len(descriptions) else ''
        indicator = indicators[i].strip() if i < len(indicators) else ''
        if not any([goal, target, description.strip(), indicator]):
            continue
        SustainableDevelopmentGoal.objects.create(
            ppa=ppa,
            order=created + 1,
            goal_description=goal or 'Unspecified SDG',
            target=target,
            description=description,
            indicator=indicator,
        )
        created += 1
    return created


def _save_activities(project, data, prefix='', require_three=True, replace=False):
    if replace:
        project.activities.all().delete()
    titles = data.getlist(prefix + 'activity_title[]')
    dates = data.getlist(prefix + 'activity_date[]')
    times = data.getlist(prefix + 'activity_time[]')
    venues = data.getlist(prefix + 'activity_venue[]')
    leaders = data.getlist(prefix + 'activity_leader[]')
    topics = data.getlist(prefix + 'activity_topics[]')
    objectives = data.getlist(prefix + 'activity_objectives[]')
    outcomes = data.getlist(prefix + 'activity_outcomes[]')
    budgets = data.getlist(prefix + 'activity_budget[]')

    def at(arr, i):
        return arr[i] if i < len(arr) else ''

    created = 0
    for i, title in enumerate(titles):
        if not (title or '').strip():
            continue
        Activity.objects.create(
            project=project,
            title=title.strip(),
            date=at(dates, i) or None,
            time=at(times, i) or None,
            venue=at(venues, i).strip(),
            activity_leader=at(leaders, i).strip(),
            topics=at(topics, i),
            objectives=at(objectives, i),
            learning_outcomes=at(outcomes, i),
            budget=dec(at(budgets, i)),
        )
        created += 1
    if require_three and created < 3:
        raise ValidationError(f'Every project must have at least 3 activities. Only {created} complete activity title(s) were received.')
    return created


def _ppa_payload(obj):
    def rows(text):
        return [x.strip() for x in (text or '').splitlines() if x.strip()]
    return {
        'id': obj.pk,
        'ppa_type': obj.ppa_type,
        'notice_to_proceed_no': obj.notice_to_proceed_no or '',
        'special_order_no': obj.special_order_no or '',
        'title': obj.title or '',
        'umbrella_program': obj.umbrella_program_id or '',
        'umbrella_program_title': obj.umbrella_program.title if obj.umbrella_program else '',
        'proponents': rows(obj.proponents),
        'partner_category': obj.partner_category or '',
        'partner_name': obj.partner_name or '',
        'with_moa_mou': obj.with_moa_mou,
        'board_confirmed': obj.board_confirmed,
        'board_resolution_no': obj.board_resolution_no or '',
        'board_resolution_date': obj.board_resolution_date.isoformat() if obj.board_resolution_date else '',
        'leader_name': obj.leader_name or '',
        'leader_position': obj.leader_position or '',
        'leader_contact': obj.leader_contact or '',
        'assistant_name': obj.assistant_name or '',
        'assistant_position': obj.assistant_position or '',
        'assistant_contact': obj.assistant_contact or '',
        'members': rows(obj.members),
        'clientele': obj.clientele or '',
        'target_area': obj.target_area or '',
        'start_date': obj.start_date.isoformat() if obj.start_date else '',
        'end_date': obj.end_date.isoformat() if obj.end_date else '',
        'project_cost': str(obj.project_cost) if obj.project_cost is not None else '',
        'funding_source': obj.funding_source or '',
        'urdea': obj.urdea or '',
        'sdgs': [
            {
                'goal': x.goal_description,
                'target': x.target,
                'description': x.description,
                'indicator': x.indicator,
            }
            for x in obj.sdg_entries.all()
        ],
        'activities': [
            {
                'title': a.title,
                'date': a.date.isoformat() if a.date else '',
                'time': a.time.strftime('%H:%M') if a.time else '',
                'venue': a.venue,
                'leader': a.activity_leader,
                'topics': a.topics,
                'objectives': a.objectives,
                'outcomes': a.learning_outcomes,
                'budget': str(a.budget) if a.budget is not None else '',
            }
            for a in obj.activities.all().order_by('date', 'id')
        ] if obj.ppa_type == PPA.PROJECT else [],
    }


@login_required
def ppa_add_project(request):
    require_roles(request.user, UserProfile.COORDINATOR)
    profile = get_profile(request.user)
    unit = profile.unit if profile else None
    programs = unit_scope(request.user, PPA.objects.filter(ppa_type=PPA.PROGRAM, workflow_status=PPA.SAVED))

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        try:
            with transaction.atomic():
                obj = PPA(
                    created_by=request.user,
                    unit=_unit_for_post(request),
                    ppa_type=PPA.PROJECT,
                    workflow_status=PPA.DRAFT if action == 'draft' else PPA.SAVED,
                )
                _assign_ppa_fields(obj, request.POST)
                umb = request.POST.get('umbrella_program')
                if umb:
                    obj.umbrella_program = unit_scope(request.user, PPA.objects.filter(ppa_type=PPA.PROGRAM, workflow_status=PPA.SAVED)).get(pk=umb)
                if action != 'draft' and (not obj.notice_to_proceed_no or not obj.special_order_no):
                    raise ValidationError('Notice to Proceed No. and Special Order No. are required before final Save.')
                obj.full_clean()
                obj.save()
                _save_sdgs(obj, request.POST)
                saved_count = _save_activities(obj, request.POST, require_three=(action != 'draft'))
                if action != 'draft' and obj.activities.count() < 3:
                    raise ValidationError('Project final Save failed: at least 3 Activities must actually be stored.')
                log(request.user, 'Created project', f'{obj.title} ({saved_count} activities)')
            messages.success(request, 'Project saved.' if action != 'draft' else 'Project saved as draft.')
            return redirect('ppa_list')
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, 'dashboard/ppa_form.html', {
        'mode': 'project',
        'programs': programs,
        'units': Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),
        'auto_unit': unit,
        'initial_json': '{}',
        'edit_obj': None,
    })


@login_required
def ppa_add_program(request):
    require_roles(request.user, UserProfile.COORDINATOR)
    profile = get_profile(request.user)
    unit = profile.unit if profile else None

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        try:
            with transaction.atomic():
                program = PPA(
                    created_by=request.user,
                    unit=_unit_for_post(request),
                    ppa_type=PPA.PROGRAM,
                    workflow_status=PPA.DRAFT if action == 'draft' else PPA.SAVED,
                )
                _assign_ppa_fields(program, request.POST)
                if action != 'draft' and (not program.notice_to_proceed_no or not program.special_order_no):
                    raise ValidationError('Program Notice to Proceed No. and Special Order No. are required before final Save.')
                program.full_clean()
                program.save()
                _save_sdgs(program, request.POST)

                project_indexes = [x for x in request.POST.getlist('project_index[]') if str(x).isdigit()]
                if action != 'draft' and not project_indexes:
                    raise ValidationError('Add at least one Project under the Program.')

                for idx in project_indexes:
                    prefix = f'project_{idx}_'
                    title = request.POST.get(prefix + 'title', '').strip()
                    if not title:
                        continue
                    pr = PPA(
                        created_by=request.user,
                        unit=program.unit,
                        ppa_type=PPA.PROJECT,
                        umbrella_program=program,
                        workflow_status=program.workflow_status,
                    )
                    _assign_ppa_fields(pr, request.POST, prefix)
                    if action != 'draft' and (not pr.notice_to_proceed_no or not pr.special_order_no):
                        raise ValidationError(f'Project “{title}” needs Notice to Proceed No. and Special Order No.')
                    pr.full_clean()
                    pr.save()
                    _save_sdgs(pr, request.POST, prefix=prefix)
                    saved_count = _save_activities(pr, request.POST, prefix=prefix, require_three=(action != 'draft'))
                    if action != 'draft' and pr.activities.count() < 3:
                        raise ValidationError(f'Project “{title}” final Save failed: at least 3 Activities must actually be stored.')
                    log(request.user, 'Created nested project', f'{title} ({saved_count} activities)')

                log(request.user, 'Created program with nested projects', program.title)
            messages.success(request, 'Program, projects, and activities saved.' if action != 'draft' else 'Program workflow saved as draft.')
            return redirect('ppa_list')
        except Exception as exc:
            messages.error(request, str(exc))

    return render(request, 'dashboard/ppa_form.html', {
        'mode': 'program',
        'units': Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),
        'auto_unit': unit,
        'initial_json': '{}',
        'edit_obj': None,
    })


@login_required
def ppa_edit(request, pk):
    """Draft-only editor. Saved/approved PPAs remain immutable in this workspace."""
    require_roles(request.user, UserProfile.COORDINATOR)
    qs = unit_scope(request.user, PPA.objects.all()).select_related('unit', 'umbrella_program').prefetch_related('activities', 'sdg_entries', 'projects__activities', 'projects__sdg_entries')
    obj = get_object_or_404(qs, pk=pk)
    if obj.workflow_status != PPA.DRAFT:
        messages.error(request, 'Only Draft PPAs can be edited from this page.')
        return redirect('ppa_detail', pk=obj.pk)

    unit = get_profile(request.user).unit
    programs = unit_scope(request.user, PPA.objects.filter(ppa_type=PPA.PROGRAM, workflow_status=PPA.SAVED)).exclude(pk=obj.pk)

    if request.method == 'POST':
        action = request.POST.get('action', 'draft')
        try:
            with transaction.atomic():
                obj.workflow_status = PPA.DRAFT if action == 'draft' else PPA.SAVED
                _assign_ppa_fields(obj, request.POST)
                if obj.ppa_type == PPA.PROJECT:
                    umb = request.POST.get('umbrella_program')
                    obj.umbrella_program = programs.filter(pk=umb).first() if umb else None
                if action != 'draft' and (not obj.notice_to_proceed_no or not obj.special_order_no):
                    raise ValidationError('Notice to Proceed No. and Special Order No. are required before final Save.')
                obj.full_clean()
                obj.save()
                _save_sdgs(obj, request.POST, replace=True)

                if obj.ppa_type == PPA.PROJECT:
                    saved_count = _save_activities(obj, request.POST, require_three=(action != 'draft'), replace=True)
                    if action != 'draft' and obj.activities.count() < 3:
                        raise ValidationError('Project final Save failed: at least 3 Activities must actually be stored.')
                    log(request.user, 'Edited draft project', f'{obj.title} ({saved_count} activities)')
                else:
                    # Draft nested Projects are safe to rebuild because draft records are not
                    # included in dashboards, reports, forecasts, or field monitoring.
                    obj.projects.filter(workflow_status=PPA.DRAFT).delete()
                    project_indexes = [x for x in request.POST.getlist('project_index[]') if str(x).isdigit()]
                    if action != 'draft' and not project_indexes:
                        raise ValidationError('Add at least one Project under the Program.')
                    for idx in project_indexes:
                        prefix = f'project_{idx}_'
                        title = request.POST.get(prefix + 'title', '').strip()
                        if not title:
                            continue
                        pr = PPA(created_by=request.user, unit=obj.unit, ppa_type=PPA.PROJECT, umbrella_program=obj, workflow_status=obj.workflow_status)
                        _assign_ppa_fields(pr, request.POST, prefix)
                        if action != 'draft' and (not pr.notice_to_proceed_no or not pr.special_order_no):
                            raise ValidationError(f'Project “{title}” needs Notice to Proceed No. and Special Order No.')
                        pr.full_clean(); pr.save()
                        _save_sdgs(pr, request.POST, prefix=prefix)
                        _save_activities(pr, request.POST, prefix=prefix, require_three=(action != 'draft'))
                        if action != 'draft' and pr.activities.count() < 3:
                            raise ValidationError(f'Project “{title}” final Save failed: at least 3 Activities must actually be stored.')
                    log(request.user, 'Edited draft program workflow', obj.title)

            messages.success(request, 'Draft updated.' if action == 'draft' else 'Draft finalized and saved.')
            return redirect('ppa_list')
        except Exception as exc:
            messages.error(request, str(exc))

    payload = _ppa_payload(obj)
    if obj.ppa_type == PPA.PROGRAM:
        payload['projects'] = [_ppa_payload(p) for p in obj.projects.filter(workflow_status=PPA.DRAFT).prefetch_related('activities', 'sdg_entries').order_by('created_at', 'id')]
    return render(request, 'dashboard/ppa_form.html', {
        'mode': 'project' if obj.ppa_type == PPA.PROJECT else 'program',
        'programs': programs,
        'units': Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),
        'auto_unit': unit,
        'initial_json': json.dumps(payload),
        'edit_obj': obj,
    })


@login_required
def ppa_discard_draft(request, pk):
    require_roles(request.user, UserProfile.COORDINATOR)
    obj = get_object_or_404(unit_scope(request.user, PPA.objects.all()), pk=pk)
    if request.method != 'POST':
        raise PermissionDenied
    if obj.workflow_status != PPA.DRAFT:
        messages.error(request, 'Only Draft PPAs can be discarded.')
        return redirect('ppa_list')
    title = obj.title
    with transaction.atomic():
        if obj.ppa_type == PPA.PROGRAM:
            obj.projects.filter(workflow_status=PPA.DRAFT).delete()
        obj.delete()
    log(request.user, 'Discarded draft PPA', title)
    messages.success(request, f'Draft “{title}” was discarded.')
    return redirect('ppa_list')


@login_required
def ppa_detail(request, pk):
    obj = get_object_or_404(
        unit_scope(request.user, PPA.objects.all()).select_related('unit', 'umbrella_program', 'created_by'),
        pk=pk,
    )
    internal = obj.impact_assessments.filter(assessment_type=ImpactAssessment.INTERNAL).first()
    external = obj.impact_assessments.filter(assessment_type=ImpactAssessment.EXTERNAL).first()
    return render(request, 'dashboard/ppa_detail.html', {'obj': obj, 'internal': internal, 'external': external})


@login_required
def ppa_lifecycle(request, pk):
    require_roles(request.user, UserProfile.COORDINATOR)
    obj = get_object_or_404(unit_scope(request.user, PPA.objects.filter(ppa_type=PPA.PROJECT)), pk=pk)
    if request.method == 'POST':
        try:
            if request.POST.get('termination_date'):
                if not obj.termination_eligible and not obj.termination_date:
                    raise ValidationError('Termination is locked until one year after the End Date while the project remains incomplete.')
                obj.termination_date = request.POST.get('termination_date')
                obj.full_clean()
                obj.save()
            if obj.impact_assessment_eligible:
                for typ, prefix in [(ImpactAssessment.INTERNAL, 'internal_'), (ImpactAssessment.EXTERNAL, 'external_')]:
                    ass, _ = ImpactAssessment.objects.get_or_create(project=obj, assessment_type=typ)
                    ass.date = request.POST.get(prefix + 'date') or None
                    ass.evaluations = request.POST.get(prefix + 'evaluations', '')
                    ass.lead = request.POST.get(prefix + 'lead', '')
                    ass.members = request.POST.get(prefix + 'members', '')
                    ass.save()
            log(request.user, 'Updated lifecycle', obj.title)
            messages.success(request, 'Lifecycle information saved.')
            return redirect('ppa_detail', pk=pk)
        except Exception as exc:
            messages.error(request, str(exc))
    internal = obj.impact_assessments.filter(assessment_type=ImpactAssessment.INTERNAL).first()
    external = obj.impact_assessments.filter(assessment_type=ImpactAssessment.EXTERNAL).first()
    return render(request, 'dashboard/ppa_lifecycle.html', {'obj': obj, 'internal': internal, 'external': external})


@login_required
def qpar_list(request):
    require_roles(request.user, UserProfile.COORDINATOR, UserProfile.ADMIN_STAFF)
    qs = QparSubmission.objects.select_related('unit', 'created_by', 'created_by__evsu_profile')
    if get_role(request.user) == UserProfile.COORDINATOR:
        profile = get_profile(request.user)
        qs = qs.filter(unit=profile.unit)
    rows = []
    for item in qs:
        creator_role = get_role(item.created_by)
        protected = get_role(request.user) == UserProfile.ADMIN_STAFF and creator_role == UserProfile.COORDINATOR and item.status == QparSubmission.SAVED
        rows.append({'obj': item, 'protected': protected})
    return render(request, 'dashboard/qpar_list.html', {'rows': rows})


@login_required
def qpar_edit(request, pk=None):
    require_roles(request.user, UserProfile.COORDINATOR, UserProfile.ADMIN_STAFF)
    obj = get_object_or_404(QparSubmission.objects.select_related('created_by__evsu_profile'), pk=pk) if pk else None
    role = get_role(request.user)
    if obj and role == UserProfile.COORDINATOR and obj.unit_id != get_profile(request.user).unit_id:
        raise PermissionDenied

    protected = bool(
        obj and role == UserProfile.ADMIN_STAFF
        and get_role(obj.created_by) == UserProfile.COORDINATOR
        and obj.status == QparSubmission.SAVED
    )
    if protected and request.method == 'POST':
        raise PermissionDenied('Saved Coordinator QPAR inputs are read-only to Admin Staff.')

    today = timezone.localdate()
    default_year = today.year
    default_quarter = ((today.month - 1) // 3) + 1

    if request.method == 'POST':
        try:
            unit = _unit_for_post(request)
            year = int(request.POST.get('year'))
            quarter = int(request.POST.get('quarter'))
            if obj is None:
                existing = QparSubmission.objects.filter(unit=unit, year=year, quarter=quarter).select_related('created_by__evsu_profile').first()
                if existing:
                    if role == UserProfile.ADMIN_STAFF and get_role(existing.created_by) == UserProfile.COORDINATOR and existing.status == QparSubmission.SAVED:
                        raise ValidationError('A saved Coordinator QPAR already exists for this unit and period. Admin Staff may view it but cannot overwrite it.')
                    obj = existing
                else:
                    obj = QparSubmission(unit=unit, year=year, quarter=quarter, created_by=request.user)
            else:
                obj.unit = unit
                obj.year = year
                obj.quarter = quarter

            obj.status = QparSubmission.DRAFT if request.POST.get('action') == 'draft' else QparSubmission.SAVED
            if not obj.pk:
                obj.created_by = request.user
            obj.save()

            for ind in ExtensionIndicator.objects.filter(active=True):
                value, _ = QparIndicatorValue.objects.get_or_create(submission=obj, indicator=ind)
                value.target = dec(request.POST.get(f'target_{ind.pk}'))
                value.accomplishment = dec(request.POST.get(f'accomplishment_{ind.pk}'))
                value.remarks = request.POST.get(f'remarks_{ind.pk}', '')
                value.save()

            log(request.user, 'Saved QPAR input', str(obj))
            messages.success(request, f'QPAR input saved for Q{quarter} {year}. The first four SAVED indicators now feed TAEP for this same period.')
            return redirect(f'/qpar/?saved={obj.pk}')
        except Exception as exc:
            messages.error(request, str(exc))

    indicators = []
    for ind in ExtensionIndicator.objects.filter(active=True):
        value = obj.values.filter(indicator=ind).first() if obj else None
        indicators.append((ind, value))
    profile = get_profile(request.user)
    return render(request, 'dashboard/qpar_form.html', {
        'obj': obj,
        'indicators': indicators,
        'units': Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),
        'auto_unit': profile.unit if role == UserProfile.COORDINATOR and profile else None,
        'default_year': obj.year if obj else default_year,
        'default_quarter': obj.quarter if obj else default_quarter,
        'read_only': protected,
    })


def _taep_tables(year):
    tables = []
    units = Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE)
    for ind in ExtensionIndicator.objects.filter(active=True, order__lte=4):
        quarters = []
        for q in range(1, 5):
            unitvals = []
            for unit in units:
                value = QparIndicatorValue.objects.filter(
                    submission__unit=unit,
                    submission__year=year,
                    submission__quarter=q,
                    submission__status=QparSubmission.SAVED,
                    indicator=ind,
                ).aggregate(x=Sum('accomplishment'))['x'] or Decimal('0')
                unitvals.append((unit, value))
            quarters.append((q, unitvals, sum((v for _, v in unitvals), Decimal('0'))))
        tables.append((ind, quarters))
    return tables


@login_required
def taep_report(request):
    require_roles(request.user, UserProfile.ME_HEAD)
    year = int(request.GET.get('year') or timezone.localdate().year)
    return render(request, 'dashboard/taep_report.html', {'tables': _taep_tables(year), 'year': year})


@login_required
def taep_print(request):
    require_roles(request.user, UserProfile.ME_HEAD)
    year = int(request.GET.get('year') or timezone.localdate().year)
    return render(request, 'dashboard/taep_print.html', {
        'tables': _taep_tables(year),
        'year': year,
        'printed_by': formal_name(request.user),
    })


@login_required
def qmr_list(request):
    require_roles(request.user, UserProfile.ME_HEAD, UserProfile.ADMIN_STAFF)
    rows = QuarterlyMonitoringReport.objects.select_related('project__unit', 'created_by').order_by('-updated_at')
    return render(request, 'dashboard/qmr_list.html', {'rows': rows})


@login_required
def qmr_edit(request, pk=None):
    require_roles(request.user, UserProfile.ME_HEAD, UserProfile.ADMIN_STAFF)
    obj = get_object_or_404(QuarterlyMonitoringReport, pk=pk) if pk else None
    projects = PPA.objects.filter(ppa_type=PPA.PROJECT, workflow_status=PPA.SAVED).select_related('unit').prefetch_related('activities')

    data = request.POST.copy() if request.method == 'POST' else None
    selected_project = None
    if request.method == 'POST':
        project_id = data.get('project')
        if project_id:
            selected_project = get_object_or_404(projects, pk=project_id)
            if selected_project.start_date:
                data['period_start'] = selected_project.start_date.isoformat()
            if selected_project.end_date:
                data['period_end'] = selected_project.end_date.isoformat()
            if not data.get('location'):
                data['location'] = selected_project.target_area
            if not data.get('funding_source'):
                data['funding_source'] = selected_project.funding_source
            if not data.get('total_project_cost') and selected_project.project_cost is not None:
                data['total_project_cost'] = str(selected_project.project_cost)
            if selected_project.unit.unit_type == Unit.SCHOOL:
                data['school_name'] = selected_project.unit.name
                data['campus_name'] = 'Main Campus'
            elif selected_project.unit.unit_type == Unit.CAMPUS:
                data['school_name'] = ''
                data['campus_name'] = selected_project.unit.name
            else:
                data['school_name'] = ''
                data['campus_name'] = selected_project.unit.campus_name or ''

    form = QuarterlyMonitoringReportForm(data or None, instance=obj)
    form.fields['project'].queryset = projects
    if request.method != 'POST' and obj:
        unit = obj.project.unit
        if not obj.school_name:
            form.fields['school_name'].initial = unit.name if unit.unit_type == Unit.SCHOOL else ''
        if not obj.campus_name:
            form.fields['campus_name'].initial = 'Main Campus' if unit.unit_type == Unit.SCHOOL else (unit.name if unit.unit_type == Unit.CAMPUS else (unit.campus_name or ''))

    if request.method == 'POST' and form.is_valid():
        report = form.save(commit=False)
        report.created_by = request.user
        if report.project.unit.unit_type == Unit.SCHOOL:
            report.school_name = report.project.unit.name
            report.campus_name = 'Main Campus'
        elif report.project.unit.unit_type == Unit.CAMPUS:
            report.school_name = ''
            report.campus_name = report.project.unit.name
        else:
            report.school_name = ''
            report.campus_name = report.project.unit.campus_name or ''
        # Non-ongoing statuses do not carry a phase selection.
        if report.project_status != QuarterlyMonitoringReport.ONGOING:
            report.phase = None
        if report.project_status != QuarterlyMonitoringReport.INACTIVE:
            report.inactive_remarks = ''
        if report.project_status != QuarterlyMonitoringReport.TERMINATED:
            report.date_of_termination = None
        report.full_clean()
        report.save()

        if report.project_status == QuarterlyMonitoringReport.TERMINATED and report.date_of_termination:
            project = report.project
            project.termination_date = report.date_of_termination
            project.save(update_fields=['termination_date', 'updated_at'])

        log(request.user, 'Saved Quarterly Monitoring Report', report.project.title)
        messages.success(request, 'Quarterly Monitoring Report saved.')
        return redirect('qmr_print', pk=report.pk) if request.POST.get('action') == 'save_print' else redirect('qmr_list')

    project_meta = {}
    for project in projects:
        project_meta[str(project.pk)] = {
            'start': project.start_date.isoformat() if project.start_date else '',
            'end': project.end_date.isoformat() if project.end_date else '',
            'location': project.target_area or '',
            'funding': project.funding_source or '',
            'cost': str(project.project_cost or ''),
            'school': project.unit.name if project.unit.unit_type == Unit.SCHOOL else '',
            'campus': 'Main Campus' if project.unit.unit_type == Unit.SCHOOL else (project.unit.name if project.unit.unit_type == Unit.CAMPUS else (project.unit.campus_name or '')),
            'auto_inactive': project.auto_inactive,
            'termination_eligible': project.termination_eligible or bool(project.termination_date),
            'termination_date': project.termination_date.isoformat() if project.termination_date else '',
            'not_conducted': project.not_conducted_activity_count,
            'completed': project.is_completed,
        }

    return render(request, 'dashboard/qmr_form.html', {
        'form': form,
        'obj': obj,
        'phases': PHASES,
        'project_meta_json': json.dumps(project_meta),
        'extension_director_name': director_name() or '—',
    })


@login_required
def qmr_print(request, pk):
    require_roles(request.user, UserProfile.ME_HEAD, UserProfile.ADMIN_STAFF)
    obj = get_object_or_404(
        QuarterlyMonitoringReport.objects.select_related('project__unit', 'created_by'),
        pk=pk,
    )
    unit = obj.project.unit
    fallback_school = unit.name if unit.unit_type == Unit.SCHOOL else ''
    fallback_campus = 'Main Campus' if unit.unit_type == Unit.SCHOOL else (unit.name if unit.unit_type == Unit.CAMPUS else (unit.campus_name or ''))
    return render(request, 'dashboard/qmr_print.html', {
        'obj': obj,
        'phases': PHASES,
        'prepared_by': formal_name(obj.created_by),
        'prepared_role': (get_profile(obj.created_by).get_role_display() if get_profile(obj.created_by) else 'Prepared by'),
        'extension_director_name': director_name() or '—',
        'qmr_school': obj.school_name or fallback_school,
        'qmr_campus': obj.campus_name or fallback_campus,
    })


@login_required
def field_visit_list(request):
    require_roles(request.user, UserProfile.COORDINATOR, UserProfile.ME_HEAD, UserProfile.DIRECTOR)
    today = timezone.localdate()
    raw_year = (request.GET.get('year') or '').strip()
    raw_quarter = (request.GET.get('quarter') or '').strip()
    try:
        year = int(raw_year) if raw_year else None
    except (TypeError, ValueError):
        year = None
    try:
        quarter = int(raw_quarter) if raw_quarter else None
    except (TypeError, ValueError):
        quarter = None
    if quarter not in (None, 1, 2, 3, 4):
        quarter = None

    unit_id = request.GET.get('unit') or ''
    query = (request.GET.get('q') or '').strip()

    base_projects = unit_scope(request.user, PPA.objects.filter(
        ppa_type=PPA.PROJECT,
        workflow_status=PPA.SAVED,
    )).select_related('unit', 'umbrella_program', 'created_by').prefetch_related('activities')

    if unit_id and get_role(request.user) != UserProfile.COORDINATOR:
        base_projects = base_projects.filter(unit_id=unit_id)
    if query:
        # Project-name search is independent from the period filters.
        base_projects = base_projects.filter(Q(title__icontains=query) | Q(umbrella_program__title__icontains=query))

    projects = base_projects.distinct()
    if year and quarter:
        start, end = quarter_bounds(year, quarter)
        projects = projects.filter(
            Q(start_date__lte=end, end_date__gte=start) |
            Q(activities__date__range=(start, end))
        ).distinct()
    elif year:
        ystart, yend = date(year, 1, 1), date(year, 12, 31)
        projects = projects.filter(
            Q(start_date__lte=yend, end_date__gte=ystart) |
            Q(activities__date__year=year)
        ).distinct()
    elif quarter:
        # Quarter-only filter works across years by checking approved Activity dates
        # and Project Start Dates that fall in the same quarter number.
        months = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}[quarter]
        projects = projects.filter(
            Q(start_date__month__in=months) | Q(end_date__month__in=months) |
            Q(activities__date__month__in=months)
        ).distinct()

    monitor_year = year or today.year
    monitor_quarter = quarter or ((today.month - 1) // 3) + 1

    # Older builds could leave multiple PPA rows representing revisions of the
    # same Project. Collapse those legacy duplicates for monitoring and keep the
    # newest record. NTP/Special Order numbers are preferred as the identity key;
    # title + unit is the fallback.
    deduped = {}
    for project in projects.order_by('-updated_at', '-pk'):
        identity = (project.notice_to_proceed_no or project.special_order_no or project.title).strip().casefold()
        key = (project.unit_id, identity)
        if key not in deduped:
            deduped[key] = project

    rows = []
    for project in deduped.values():
        logs = FieldVisitLog.objects.filter(project=project)
        if year:
            logs = logs.filter(year=year)
        if quarter:
            logs = logs.filter(quarter=quarter)
        latest_log = logs.order_by('-updated_at', '-pk').first()
        rows.append({
            'project': project,
            'log': latest_log,
            'last_updated': latest_log.updated_at if latest_log else project.updated_at,
            'entries': latest_log.entries.count() if latest_log else 0,
        })
    rows.sort(key=lambda row: row['last_updated'], reverse=True)

    title_source = unit_scope(request.user, PPA.objects.filter(
        ppa_type=PPA.PROJECT, workflow_status=PPA.SAVED
    )).order_by('title').values_list('title', flat=True).distinct()

    return render(request, 'dashboard/field_visit_list.html', {
        'rows': rows,
        'units': Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),
        'filter_year': year or '',
        'filter_quarter': quarter or '',
        'filter_unit': str(unit_id),
        'filter_q': query,
        'project_titles': list(title_source),
        'monitor_year': monitor_year,
        'monitor_quarter': monitor_quarter,
    })


@login_required
def field_visit_create(request):
    # Compatibility route from earlier builds; project selection now lives on the list page.
    return redirect('field_visit_list')


@login_required
def field_visit_monitor(request, project_pk):
    require_roles(request.user, UserProfile.COORDINATOR, UserProfile.ME_HEAD, UserProfile.DIRECTOR)
    projects = unit_scope(request.user, PPA.objects.filter(ppa_type=PPA.PROJECT, workflow_status=PPA.SAVED)).select_related('unit', 'umbrella_program', 'created_by')
    project = get_object_or_404(projects, pk=project_pk)

    today = timezone.localdate()
    try:
        year = int(request.POST.get('year') or request.GET.get('year') or today.year)
    except (TypeError, ValueError):
        year = today.year
    try:
        quarter = int(request.POST.get('quarter') or request.GET.get('quarter') or ((today.month - 1) // 3) + 1)
    except (TypeError, ValueError):
        quarter = ((today.month - 1) // 3) + 1
    if quarter not in (1, 2, 3, 4):
        quarter = ((today.month - 1) // 3) + 1

    start, end = quarter_bounds(year, quarter)
    activities = list(project.activities.filter(date__range=(start, end)).order_by('date', 'id'))
    if not activities:
        activities = list(project.activities.all().order_by('date', 'id'))

    logobj = FieldVisitLog.objects.filter(project=project, year=year, quarter=quarter).order_by('-updated_at', '-pk').first()
    can_edit = get_role(request.user) == UserProfile.COORDINATOR

    if request.method == 'POST':
        if not can_edit:
            raise PermissionDenied
        try:
            with transaction.atomic():
                if logobj is None:
                    logobj = FieldVisitLog.objects.create(
                        project=project, year=year, quarter=quarter,
                        created_by=request.user,
                    )
                logobj.evaluation = request.POST.get('evaluation', '')
                logobj.partner_representative_name = request.POST.get('partner_representative_name', '').strip()
                logobj.partner_representative_postnominals = request.POST.get('partner_representative_postnominals', '').strip()
                logobj.created_by = request.user
                logobj.save()

                activity_ids = set()
                for activity in activities:
                    activity_ids.add(activity.pk)
                    entry = logobj.entries.filter(activity=activity).first()
                    if entry is None:
                        entry = FieldVisitEntry(log=logobj, activity=activity)

                    # Approved Project Design data is authoritative and is not editable here.
                    entry.objectives = activity.objectives
                    entry.activities = activity.title
                    entry.date = activity.date
                    entry.place = activity.venue
                    entry.time = activity.time
                    entry.expected_parameter = request.POST.get(f'parameter_{activity.pk}', '').strip()
                    entry.expected_target = request.POST.get(f'target_{activity.pk}', '').strip()
                    entry.person_contacted = request.POST.get(f'person_{activity.pk}', '').strip()
                    entry.position = request.POST.get(f'position_{activity.pk}', '').strip()
                    entry.result = request.POST.get(f'result_{activity.pk}', 'NOT_CONDUCTED')
                    entry.rescheduled_date = request.POST.get(f'rescheduled_{activity.pk}') or None
                    entry.remarks = request.POST.get(f'remarks_{activity.pk}', '')
                    entry.full_clean()
                    entry.save()

                # Remove legacy/manual rows that do not correspond to an approved activity.
                logobj.entries.exclude(activity_id__in=activity_ids).delete()
                log(request.user, 'Saved Work Plan / Field Visit Log', f'{project.title} Q{quarter} {year}')

            messages.success(request, 'Work Plan and Monitoring Log saved.')
            if request.POST.get('action') == 'save_print':
                return redirect('field_visit_print', pk=logobj.pk)
            return redirect(f'/field-visits/project/{project.pk}/?year={year}&quarter={quarter}')
        except Exception as exc:
            messages.error(request, str(exc))

    existing = {}
    if logobj:
        for entry in logobj.entries.select_related('activity'):
            if entry.activity_id:
                existing[entry.activity_id] = entry
    activity_rows = [{'activity': activity, 'entry': existing.get(activity.pk)} for activity in activities]

    return render(request, 'dashboard/field_visit_form.html', {
        'selected': project,
        'logobj': logobj,
        'activity_rows': activity_rows,
        'year': year,
        'quarter': quarter,
        'can_edit': can_edit,
    })


@login_required
def field_visit_print(request, pk):
    require_roles(request.user, UserProfile.COORDINATOR, UserProfile.ME_HEAD, UserProfile.DIRECTOR)
    qs = FieldVisitLog.objects.select_related('project__unit', 'project__created_by', 'created_by').prefetch_related('entries')
    obj = get_object_or_404(qs, pk=pk)
    if get_role(request.user) == UserProfile.COORDINATOR and obj.project.unit_id != get_profile(request.user).unit_id:
        raise PermissionDenied
    return render(request, 'dashboard/field_visit_print.html', {
        'obj': obj,
        'project_leader_name': obj.project.leader_name or '—',
        'coordinator_name': formal_name(obj.project.created_by),
        'director_name': director_name() or '—',
    })


@login_required
def analytics(request):
    require_roles(request.user, UserProfile.ADMIN_STAFF, UserProfile.DIRECTOR)
    year = int(request.GET.get('year') or timezone.localdate().year)
    forecast = forecast_projects(year)
    chart_max = max([max(row.get('plot_values', [0])) for row in forecast] or [1]) or 1
    x_positions = [8, 38, 68, 98]
    palette = ['#8b1535','#d5a300','#b05066','#5d6270','#8e7d6b','#3f7d6d','#8d5da7','#bf6a3d','#4c78a8','#7a8f3a','#a65b74']
    for index, row in enumerate(forecast):
        points = []
        for x, value in zip(x_positions, row.get('plot_values', [0, 0, 0, 0])):
            y = 90 - ((float(value) / chart_max) * 72)
            points.append((x, y))
        row['chart_path'] = _smooth_svg_path(points)
        row['chart_color'] = palette[index % len(palette)]
    return render(request, 'dashboard/analytics.html', {
        'forecast': forecast,
        'year': year,
        'prediction_top': forecast[0] if forecast else None,
    })


@login_required
def manage_users(request):
    require_roles(request.user, UserProfile.ME_HEAD)
    edit_id = request.GET.get('edit') or request.POST.get('user_id') or ''
    target = None
    if edit_id:
        target = get_object_or_404(User.objects.select_related('evsu_profile__unit'), pk=edit_id)
        if target.pk == request.user.pk:
            messages.error(request, 'Use Django Admin if you need to change your own superuser account.')
            return redirect('manage_users')

    initial = None
    if target and request.method != 'POST':
        prof = get_profile(target)
        initial = {
            'username': target.username,
            'first_name': target.first_name,
            'last_name': target.last_name,
            'email': target.email,
            'post_nominals': prof.post_nominals if prof else '',
            'role': prof.role if prof else '',
            'unit': prof.unit_id if prof else None,
            'is_active': target.is_active,
        }

    if request.method == 'POST':
        form = UserManageForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            username = cd['username']
            duplicate = User.objects.filter(username=username)
            if target:
                duplicate = duplicate.exclude(pk=target.pk)
            if duplicate.exists():
                messages.error(request, 'Username already exists.')
            else:
                if target:
                    user = target
                    user.username = username
                    user.first_name = cd['first_name']
                    user.last_name = cd['last_name']
                    user.email = cd['email']
                    user.is_active = cd['is_active']
                    if cd['password']:
                        user.set_password(cd['password'])
                    action_text = 'Updated user'
                else:
                    user = User.objects.create_user(
                        username=username,
                        password=cd['password'] or 'ChangeMe123!',
                        first_name=cd['first_name'],
                        last_name=cd['last_name'],
                        email=cd['email'],
                        is_active=cd['is_active'],
                    )
                    action_text = 'Created user'
                role = cd['role']
                user.is_superuser = role == UserProfile.ME_HEAD
                user.is_staff = user.is_superuser
                user.save()
                profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': role})
                profile.role = role
                profile.unit = cd['unit'] if role == UserProfile.COORDINATOR else None
                profile.post_nominals = cd['post_nominals']
                profile.save()
                log(request.user, action_text, f'{display_name(user)} ({username})')
                messages.success(request, 'User information saved. Real names and post-nominal letters are now available to printable signatories.')
                return redirect('manage_users')
    else:
        form = UserManageForm(initial=initial)

    return render(request, 'dashboard/manage_users.html', {
        'form': form,
        'edit_user': target,
        'users': User.objects.exclude(pk=request.user.pk).select_related('evsu_profile__unit').order_by('last_name', 'first_name', 'username'),
    })


@login_required
def activity_logs(request):
    require_roles(request.user, UserProfile.ME_HEAD)
    logs = ActivityLog.objects.select_related('actor')
    start_date = (request.GET.get('start') or '').strip()
    end_date = (request.GET.get('end') or '').strip()
    if start_date:
        logs = logs.filter(created_at__date__gte=start_date)
    if end_date:
        logs = logs.filter(created_at__date__lte=end_date)
    return render(request, 'dashboard/activity_logs.html', {
        'logs': logs[:1000],
        'filter_start': start_date,
        'filter_end': end_date,
    })
