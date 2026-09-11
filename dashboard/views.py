from datetime import date
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .forms import *
from .models import *
from .services import forecast_projects

PHASES={1:'Needs assessment',2:'Early project implementation',3:'Middle project implementation',4:'Late project implementation',5:'Completion of project',6:'Evaluation of output and outcome',7:'Impact evaluation'}

def get_profile(user):
    try:return user.evsu_profile
    except Exception:return None

def get_role(user):
    if user.is_superuser:return UserProfile.ME_HEAD
    p=get_profile(user); return p.role if p else ''

def require_roles(user,*roles):
    if get_role(user) not in roles: raise PermissionDenied

def unit_scope(user, qs):
    if get_role(user)==UserProfile.COORDINATOR:
        p=get_profile(user)
        return qs.filter(unit=p.unit) if p and p.unit else qs.none()
    return qs

def log(user, action, details=''):
    ActivityLog.objects.create(actor=user,action=action,details=details)

def parse_bool(value): return str(value).lower() in ('1','true','yes','on')
def dec(value):
    try:return Decimal(value) if str(value).strip() else None
    except (InvalidOperation,ValueError,TypeError):return None

def login_view(request):
    if request.user.is_authenticated:return redirect('dashboard')
    form=AuthenticationForm(request,data=request.POST or None)
    if request.method=='POST' and form.is_valid():
        login(request,form.get_user()); return redirect('dashboard')
    return render(request,'dashboard/login.html',{'form':form})

def logout_view(request):
    if request.method=='POST': logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    role=get_role(request.user); ppas=unit_scope(request.user,PPA.objects.all())
    projects=ppas.filter(ppa_type=PPA.PROJECT); programs=ppas.filter(ppa_type=PPA.PROGRAM)
    activities=Activity.objects.filter(project__in=projects)
    today=timezone.localdate()
    q=((today.month-1)//3)+1

    def status_counts(qs):
        data={'approved':0,'board_confirmed':0,'ongoing':0,'inactive':0,'terminated':0}
        for obj in qs:
            if obj.workflow_status==PPA.SAVED:
                data['approved']+=1
            if obj.board_confirmed:
                data['board_confirmed']+=1
            latest=None
            if obj.ppa_type==PPA.PROJECT:
                latest=obj.quarterly_monitoring_reports.order_by('-period_end','-updated_at').first()
            if latest:
                if latest.project_status==QuarterlyMonitoringReport.ONGOING: data['ongoing']+=1
                elif latest.project_status==QuarterlyMonitoringReport.INACTIVE: data['inactive']+=1
                elif latest.project_status==QuarterlyMonitoringReport.TERMINATED: data['terminated']+=1
            elif obj.termination_date:
                data['terminated']+=1
            elif obj.start_date and obj.end_date and obj.start_date<=today<=obj.end_date:
                data['ongoing']+=1
            elif obj.end_date and obj.end_date<today:
                data['inactive']+=1
        return data

    status_programs=status_counts(programs)
    status_projects=status_counts(projects)
    summary_counts={k:status_programs[k]+status_projects[k] for k in status_programs}
    summary_total=programs.count()+projects.count()

    # The ring uses mutually exclusive operational states; approval/board confirmation remain in the legend/table.
    operational=[summary_counts['ongoing'],summary_counts['terminated'],summary_counts['inactive']]
    operational_total=sum(operational)
    if operational_total:
        p1=round(operational[0]/operational_total*100,2)
        p2=round(p1+operational[1]/operational_total*100,2)
        summary_gradient=f"conic-gradient(#b05066 0 {p1}%, #781328 {p1}% {p2}%, #cfc6c1 {p2}% 100%)"
    else:
        summary_gradient='conic-gradient(#e8e2de 0 100%)'

    internal_assessed=ImpactAssessment.objects.filter(project__in=projects,assessment_type=ImpactAssessment.INTERNAL,date__isnull=False).count()
    external_assessed=ImpactAssessment.objects.filter(project__in=projects,assessment_type=ImpactAssessment.EXTERNAL,date__isnull=False).count()
    assessment_counts={'internal':internal_assessed,'external':external_assessed}
    board_counts={'confirmed':ppas.filter(board_confirmed=True).count(),'moa_mou':ppas.filter(with_moa_mou=True).count()}

    partner_labels=[('LGU','LGU'),('INDUSTRY','Industry'),('SME','SME'),('OTHERS','Other')]
    partner_raw=[(code,label,ppas.filter(partner_category=code).count()) for code,label in partner_labels]
    partner_max=max([n for _,_,n in partner_raw] or [1]) or 1
    partnerships=[{'label':label,'count':n,'percent':round((n/partner_max)*100,1) if n else 0} for _,label,n in partner_raw]

    counts={'programs':programs.count(),'projects':projects.count(),'activities':activities.count(),'active':status_projects['ongoing'],'drafts':ppas.filter(workflow_status=PPA.DRAFT).count()}
    termination_due=sum(1 for x in projects if x.termination_eligible)
    impact_due=sum(1 for x in projects if x.impact_assessment_eligible and x.impact_assessments.count()<2)
    indicators=list(ExtensionIndicator.objects.filter(active=True,order__lte=4))
    taep=[]
    for ind in indicators:
        vals=[]
        units=Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE)
        if role==UserProfile.COORDINATOR:
            prof=get_profile(request.user); units=units.filter(pk=prof.unit_id) if prof and prof.unit_id else units.none()
        for u in units:
            v=QparIndicatorValue.objects.filter(submission__unit=u,submission__year=today.year,submission__quarter=q,submission__status=QparSubmission.SAVED,indicator=ind).aggregate(x=Sum('accomplishment'))['x'] or 0
            vals.append((u,v))
        taep.append((ind,vals,sum((v for _,v in vals),Decimal('0'))))
    forecast=forecast_projects(today.year) if role in (UserProfile.ME_HEAD,UserProfile.ADMIN_STAFF,UserProfile.DIRECTOR) else []
    return render(request,'dashboard/dashboard.html',{
        'counts':counts,'termination_due':termination_due,'impact_due':impact_due,'taep':taep,'quarter':q,'year':today.year,'forecast':forecast[:6],
        'status_programs':status_programs,'status_projects':status_projects,'summary_counts':summary_counts,'summary_total':summary_total,'summary_gradient':summary_gradient,
        'assessment_counts':assessment_counts,'board_counts':board_counts,'partnerships':partnerships,
    })

@login_required
def ppa_list(request):
    require_roles(request.user,UserProfile.COORDINATOR)
    rows=unit_scope(request.user,PPA.objects.all()).select_related('unit','umbrella_program')
    return render(request,'dashboard/ppa_list.html',{'rows':rows})

def _unit_for_post(request, key='unit'):
    if get_role(request.user)==UserProfile.COORDINATOR:
        p=get_profile(request.user)
        if not p or not p.unit: raise ValidationError('Your account has no assigned school/campus.')
        return p.unit
    uid=request.POST.get(key) or request.GET.get(key)
    return get_object_or_404(Unit,pk=uid) if uid else None

def _assign_ppa_fields(obj, data, prefix=''):
    def g(name,default=''): return data.get(prefix+name,default)
    obj.notice_to_proceed_no=g('notice_to_proceed_no')
    obj.special_order_no=g('special_order_no')
    obj.title=g('title').strip()
    obj.proponents=g('proponents')
    obj.partner_category=g('partner_category')
    obj.partner_name=g('partner_name')
    obj.with_moa_mou=parse_bool(g('with_moa_mou'))
    obj.board_confirmed=parse_bool(g('board_confirmed'))
    obj.board_resolution_no=g('board_resolution_no')
    obj.board_resolution_date=g('board_resolution_date') or None
    obj.leader_name=g('leader_name'); obj.leader_position=g('leader_position'); obj.leader_contact=g('leader_contact')
    obj.assistant_name=g('assistant_name'); obj.assistant_position=g('assistant_position'); obj.assistant_contact=g('assistant_contact')
    obj.members=g('members'); obj.clientele=g('clientele'); obj.target_area=g('target_area')
    obj.start_date=g('start_date') or None; obj.end_date=g('end_date') or None
    obj.project_cost=dec(g('project_cost')); obj.funding_source=g('funding_source'); obj.urdea=g('urdea'); obj.sdgs=g('sdgs')
    return obj

def _save_activities(project, data, prefix='', require_three=True):
    titles=data.getlist(prefix+'activity_title[]')
    valid=0
    for i,title in enumerate(titles):
        if not title.strip(): continue
        valid+=1
        def item(name):
            arr=data.getlist(prefix+name+'[]'); return arr[i] if i<len(arr) else ''
        Activity.objects.create(project=project,title=title.strip(),date=item('activity_date') or None,time=item('activity_time') or None,venue=item('activity_venue'),activity_leader=item('activity_leader'),topics=item('activity_topics'),objectives=item('activity_objectives'),learning_outcomes=item('activity_outcomes'),budget=dec(item('activity_budget')))
    if require_three and valid<3: raise ValidationError('Every project must have at least 3 activities.')

@login_required
def ppa_add_project(request):
    require_roles(request.user,UserProfile.COORDINATOR)
    unit=_unit_for_post(request) if request.method=='POST' else (get_profile(request.user).unit if get_role(request.user)==UserProfile.COORDINATOR and get_profile(request.user) else None)
    programs=unit_scope(request.user,PPA.objects.filter(ppa_type=PPA.PROGRAM,workflow_status=PPA.SAVED))
    if request.method=='POST':
        action=request.POST.get('action','save')
        try:
            with transaction.atomic():
                obj=PPA(created_by=request.user,unit=_unit_for_post(request),ppa_type=PPA.PROJECT,workflow_status=PPA.DRAFT if action=='draft' else PPA.SAVED)
                _assign_ppa_fields(obj,request.POST)
                umb=request.POST.get('umbrella_program')
                if umb: obj.umbrella_program=unit_scope(request.user,PPA.objects.filter(ppa_type=PPA.PROGRAM)).get(pk=umb)
                if action!='draft' and (not obj.notice_to_proceed_no or not obj.special_order_no): raise ValidationError('Notice to Proceed No. and Special Order No. are required before final Save.')
                obj.full_clean(); obj.save(); _save_activities(obj,request.POST,require_three=(action!='draft'))
                log(request.user,'Created project',obj.title)
            messages.success(request,'Project saved.' if action!='draft' else 'Project saved as draft.')
            return redirect('ppa_list')
        except Exception as e: messages.error(request,str(e))
    return render(request,'dashboard/ppa_form.html',{'mode':'project','programs':programs,'units':Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),'auto_unit':unit})

@login_required
def ppa_add_program(request):
    require_roles(request.user,UserProfile.COORDINATOR)
    unit=(get_profile(request.user).unit if get_role(request.user)==UserProfile.COORDINATOR and get_profile(request.user) else None)
    if request.method=='POST':
        action=request.POST.get('action','save')
        try:
            with transaction.atomic():
                program=PPA(created_by=request.user,unit=_unit_for_post(request),ppa_type=PPA.PROGRAM,workflow_status=PPA.DRAFT if action=='draft' else PPA.SAVED)
                _assign_ppa_fields(program,request.POST)
                if action!='draft' and (not program.notice_to_proceed_no or not program.special_order_no): raise ValidationError('Program Notice to Proceed No. and Special Order No. are required before final Save.')
                program.full_clean(); program.save()
                project_indexes=[x for x in request.POST.getlist('project_index[]') if str(x).isdigit()]
                if action!='draft' and not project_indexes: raise ValidationError('Add at least one Project under the Program.')
                for idx in project_indexes:
                    prefix=f'project_{idx}_'
                    title=request.POST.get(prefix+'title','').strip()
                    if not title: continue
                    pr=PPA(created_by=request.user,unit=program.unit,ppa_type=PPA.PROJECT,umbrella_program=program,workflow_status=program.workflow_status)
                    _assign_ppa_fields(pr,request.POST,prefix)
                    if action!='draft' and (not pr.notice_to_proceed_no or not pr.special_order_no): raise ValidationError(f'Project “{title}” needs Notice to Proceed No. and Special Order No.')
                    pr.full_clean(); pr.save(); _save_activities(pr,request.POST,prefix=prefix,require_three=(action!='draft'))
                log(request.user,'Created program with nested projects',program.title)
            messages.success(request,'Program, projects, and activities saved.' if action!='draft' else 'Program workflow saved as draft.')
            return redirect('ppa_list')
        except Exception as e: messages.error(request,str(e))
    return render(request,'dashboard/ppa_form.html',{'mode':'program','units':Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),'auto_unit':unit})

@login_required
def ppa_detail(request,pk):
    obj=get_object_or_404(unit_scope(request.user,PPA.objects.all()).select_related('unit','umbrella_program'),pk=pk)
    internal=obj.impact_assessments.filter(assessment_type=ImpactAssessment.INTERNAL).first(); external=obj.impact_assessments.filter(assessment_type=ImpactAssessment.EXTERNAL).first()
    return render(request,'dashboard/ppa_detail.html',{'obj':obj,'internal':internal,'external':external})

@login_required
def ppa_lifecycle(request,pk):
    require_roles(request.user,UserProfile.COORDINATOR)
    obj=get_object_or_404(unit_scope(request.user,PPA.objects.filter(ppa_type=PPA.PROJECT)),pk=pk)
    if request.method=='POST':
        try:
            if request.POST.get('termination_date'):
                if not obj.termination_eligible and not obj.termination_date: raise ValidationError('Termination is locked until one year after the End Date with no completed accomplishment.')
                obj.termination_date=request.POST.get('termination_date'); obj.full_clean(); obj.save()
            if obj.impact_assessment_eligible:
                for typ,prefix in [(ImpactAssessment.INTERNAL,'internal_'),(ImpactAssessment.EXTERNAL,'external_')]:
                    ass,_=ImpactAssessment.objects.get_or_create(project=obj,assessment_type=typ)
                    ass.date=request.POST.get(prefix+'date') or None; ass.evaluations=request.POST.get(prefix+'evaluations',''); ass.lead=request.POST.get(prefix+'lead',''); ass.members=request.POST.get(prefix+'members',''); ass.save()
            log(request.user,'Updated lifecycle',obj.title); messages.success(request,'Lifecycle information saved.'); return redirect('ppa_detail',pk=pk)
        except Exception as e: messages.error(request,str(e))
    internal=obj.impact_assessments.filter(assessment_type=ImpactAssessment.INTERNAL).first(); external=obj.impact_assessments.filter(assessment_type=ImpactAssessment.EXTERNAL).first()
    return render(request,'dashboard/ppa_lifecycle.html',{'obj':obj,'internal':internal,'external':external})

@login_required
def qpar_list(request):
    require_roles(request.user,UserProfile.COORDINATOR,UserProfile.ADMIN_STAFF)
    qs=QparSubmission.objects.select_related('unit','created_by')
    if get_role(request.user)==UserProfile.COORDINATOR:
        p=get_profile(request.user); qs=qs.filter(unit=p.unit)
    return render(request,'dashboard/qpar_list.html',{'rows':qs})

@login_required
def qpar_edit(request,pk=None):
    require_roles(request.user,UserProfile.COORDINATOR,UserProfile.ADMIN_STAFF)
    obj=get_object_or_404(QparSubmission,pk=pk) if pk else None
    if obj and get_role(request.user)==UserProfile.COORDINATOR and obj.unit_id!=get_profile(request.user).unit_id: raise PermissionDenied
    if request.method=='POST':
        try:
            unit=_unit_for_post(request)
            year=int(request.POST.get('year')); quarter=int(request.POST.get('quarter'))
            if obj is None: obj,_=QparSubmission.objects.get_or_create(unit=unit,year=year,quarter=quarter,defaults={'created_by':request.user})
            obj.status=QparSubmission.DRAFT if request.POST.get('action')=='draft' else QparSubmission.SAVED; obj.created_by=request.user; obj.save()
            for ind in ExtensionIndicator.objects.filter(active=True):
                val,_=QparIndicatorValue.objects.get_or_create(submission=obj,indicator=ind)
                val.target=dec(request.POST.get(f'target_{ind.pk}')); val.accomplishment=dec(request.POST.get(f'accomplishment_{ind.pk}')); val.remarks=request.POST.get(f'remarks_{ind.pk}',''); val.save()
            log(request.user,'Saved QPAR input',str(obj)); messages.success(request,'QPAR input saved.'); return redirect('qpar_list')
        except Exception as e: messages.error(request,str(e))
    indicators=[]
    for ind in ExtensionIndicator.objects.filter(active=True):
        value=obj.values.filter(indicator=ind).first() if obj else None; indicators.append((ind,value))
    p=get_profile(request.user)
    return render(request,'dashboard/qpar_form.html',{'obj':obj,'indicators':indicators,'units':Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE),'auto_unit':p.unit if get_role(request.user)==UserProfile.COORDINATOR and p else None})

@login_required
def taep_report(request):
    require_roles(request.user,UserProfile.ME_HEAD)
    year=int(request.GET.get('year') or timezone.localdate().year)
    tables=[]
    for ind in ExtensionIndicator.objects.filter(active=True):
        quarters=[]
        for q in range(1,5):
            unitvals=[]
            for u in Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE):
                val=QparIndicatorValue.objects.filter(submission__unit=u,submission__year=year,submission__quarter=q,submission__status=QparSubmission.SAVED,indicator=ind).aggregate(x=Sum('accomplishment'))['x'] or 0
                unitvals.append((u,val))
            quarters.append((q,unitvals,sum((v for _,v in unitvals),Decimal('0'))))
        tables.append((ind,quarters))
    return render(request,'dashboard/taep_report.html',{'tables':tables,'year':year})

@login_required
def qmr_list(request):
    require_roles(request.user,UserProfile.ME_HEAD,UserProfile.ADMIN_STAFF)
    return render(request,'dashboard/qmr_list.html',{'rows':QuarterlyMonitoringReport.objects.select_related('project__unit','created_by')})

@login_required
def qmr_edit(request,pk=None):
    require_roles(request.user,UserProfile.ME_HEAD,UserProfile.ADMIN_STAFF)
    obj=get_object_or_404(QuarterlyMonitoringReport,pk=pk) if pk else None
    form=QuarterlyMonitoringReportForm(request.POST or None,instance=obj)
    form.fields['project'].queryset=PPA.objects.filter(ppa_type=PPA.PROJECT,workflow_status=PPA.SAVED).select_related('unit')
    if request.method=='POST' and form.is_valid():
        x=form.save(commit=False); x.created_by=request.user; x.save(); log(request.user,'Saved Quarterly Monitoring Report',x.project.title); messages.success(request,'Quarterly Monitoring Report saved.'); return redirect('qmr_print',pk=x.pk) if request.POST.get('action')=='save_print' else redirect('qmr_list')
    return render(request,'dashboard/qmr_form.html',{'form':form,'obj':obj,'phases':PHASES})

@login_required
def qmr_print(request,pk):
    require_roles(request.user,UserProfile.ME_HEAD,UserProfile.ADMIN_STAFF)
    obj=get_object_or_404(QuarterlyMonitoringReport.objects.select_related('project__unit'),pk=pk)
    return render(request,'dashboard/qmr_print.html',{'obj':obj,'phases':PHASES})

@login_required
def field_visit_list(request):
    require_roles(request.user,UserProfile.COORDINATOR,UserProfile.ME_HEAD,UserProfile.DIRECTOR)
    qs=FieldVisitLog.objects.select_related('project__unit','created_by')
    if get_role(request.user)==UserProfile.COORDINATOR: qs=qs.filter(project__unit=get_profile(request.user).unit)
    year=request.GET.get('year'); quarter=request.GET.get('quarter'); unit=request.GET.get('unit')
    if year and str(year).isdigit(): qs=qs.filter(year=year)
    if quarter and str(quarter).isdigit(): qs=qs.filter(quarter=quarter)
    if unit and get_role(request.user)!=UserProfile.COORDINATOR: qs=qs.filter(project__unit_id=unit)
    return render(request,'dashboard/field_visit_list.html',{'rows':qs,'units':Unit.objects.filter(active=True).exclude(unit_type=Unit.OFFICE)})

@login_required
def field_visit_create(request):
    require_roles(request.user,UserProfile.COORDINATOR)
    if request.method=='POST':
        try:
            project=get_object_or_404(unit_scope(request.user,PPA.objects.filter(ppa_type=PPA.PROJECT)),pk=request.POST.get('project'))
            year=int(request.POST.get('year')); quarter=int(request.POST.get('quarter'))
            with transaction.atomic():
                logobj=FieldVisitLog.objects.create(project=project,year=year,quarter=quarter,evaluation=request.POST.get('evaluation',''),created_by=request.user)
                acts=request.POST.getlist('fv_activities[]')
                for i,a in enumerate(acts):
                    if not a.strip(): continue
                    def item(name):
                        arr=request.POST.getlist(name+'[]'); return arr[i] if i<len(arr) else ''
                    entry=FieldVisitEntry(log=logobj,objectives=item('fv_objectives'),activities=a,date=item('fv_date') or None,place=item('fv_place'),time=item('fv_time') or None,expected_parameter=item('fv_parameter'),expected_target=item('fv_target'),person_contacted=item('fv_person'),position=item('fv_position'),result=item('fv_result') or 'NOT_CONDUCTED',rescheduled_date=item('fv_rescheduled') or None,remarks=item('fv_remarks'))
                    entry.full_clean(); entry.save()
                log(request.user,'Created Work Plan / Field Visit Log',str(logobj))
            messages.success(request,'Work Plan and Monitoring Log saved.'); return redirect('field_visit_print',pk=logobj.pk) if request.POST.get('action')=='save_print' else redirect('field_visit_list')
        except Exception as e: messages.error(request,str(e))
    projects=unit_scope(request.user,PPA.objects.filter(ppa_type=PPA.PROJECT,workflow_status=PPA.SAVED)).select_related('unit')
    selected=None; preset=[]
    pid=request.GET.get('project'); year=int(request.GET.get('year') or timezone.localdate().year); quarter=int(request.GET.get('quarter') or ((timezone.localdate().month-1)//3+1))
    if pid:
        selected=get_object_or_404(projects,pk=pid)
        months={1:(1,3),2:(4,6),3:(7,9),4:(10,12)}[quarter]
        preset=list(selected.activities.filter(date__year=year,date__month__gte=months[0],date__month__lte=months[1]))
        if not preset: preset=list(selected.activities.all())
    return render(request,'dashboard/field_visit_form.html',{'projects':projects,'selected':selected,'preset':preset,'year':year,'quarter':quarter})

@login_required
def field_visit_print(request,pk):
    require_roles(request.user,UserProfile.COORDINATOR,UserProfile.ME_HEAD,UserProfile.DIRECTOR)
    qs=FieldVisitLog.objects.select_related('project__unit','created_by').prefetch_related('entries')
    obj=get_object_or_404(qs,pk=pk)
    if get_role(request.user)==UserProfile.COORDINATOR and obj.project.unit_id!=get_profile(request.user).unit_id: raise PermissionDenied
    return render(request,'dashboard/field_visit_print.html',{'obj':obj})

@login_required
def analytics(request):
    require_roles(request.user,UserProfile.ADMIN_STAFF,UserProfile.DIRECTOR,UserProfile.ME_HEAD)
    year=int(request.GET.get('year') or timezone.localdate().year)
    return render(request,'dashboard/analytics.html',{'forecast':forecast_projects(year),'year':year})

@login_required
def manage_users(request):
    require_roles(request.user,UserProfile.ME_HEAD)
    if request.method=='POST':
        form=UserManageForm(request.POST)
        if form.is_valid():
            cd=form.cleaned_data; username=cd['username']
            if User.objects.filter(username=username).exists(): messages.error(request,'Username already exists.')
            else:
                u=User.objects.create_user(username=username,password=cd['password'] or 'ChangeMe123!',first_name=cd['first_name'],last_name=cd['last_name'],email=cd['email'],is_active=cd['is_active'])
                role=cd['role']; u.is_superuser=(role==UserProfile.ME_HEAD); u.is_staff=u.is_superuser; u.save(); UserProfile.objects.create(user=u,role=role,unit=cd['unit'] if role==UserProfile.COORDINATOR else None); log(request.user,'Created user',username); messages.success(request,'User created.'); return redirect('manage_users')
    else: form=UserManageForm()
    return render(request,'dashboard/manage_users.html',{'form':form,'users':User.objects.exclude(pk=request.user.pk).order_by('username')})

@login_required
def activity_logs(request):
    require_roles(request.user,UserProfile.ME_HEAD)
    return render(request,'dashboard/activity_logs.html',{'logs':ActivityLog.objects.select_related('actor')[:500]})
