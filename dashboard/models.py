from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Unit(models.Model):
    SCHOOL = 'SCHOOL'
    CAMPUS = 'CAMPUS'
    OFFICE = 'OFFICE'
    TYPES = [(SCHOOL, 'School'), (CAMPUS, 'Campus'), (OFFICE, 'Office')]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    unit_type = models.CharField(max_length=12, choices=TYPES)
    campus_name = models.CharField(max_length=120, default='Main Campus')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['unit_type', 'name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ME_HEAD = 'ME_HEAD'
    COORDINATOR = 'COORDINATOR'
    ADMIN_STAFF = 'ADMIN_STAFF'
    DIRECTOR = 'DIRECTOR'
    ROLES = [
        (ME_HEAD, 'M&E Head'),
        (COORDINATOR, 'Coordinator'),
        (ADMIN_STAFF, 'Admin Staff'),
        (DIRECTOR, 'Director'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='evsu_profile')
    role = models.CharField(max_length=20, choices=ROLES)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'


class PPA(models.Model):
    PROGRAM = 'PROGRAM'
    PROJECT = 'PROJECT'
    TYPES = [(PROGRAM, 'Program'), (PROJECT, 'Project')]

    DRAFT = 'DRAFT'
    SAVED = 'SAVED'
    WORKFLOW = [(DRAFT, 'Draft'), (SAVED, 'Saved')]

    PARTNER_TYPES = [
        ('LGU', 'LGU'),
        ('INDUSTRY', 'Industry'),
        ('SME', 'SME'),
        ('OTHERS', 'Others'),
    ]

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_ppas')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='ppas')
    ppa_type = models.CharField(max_length=10, choices=TYPES)
    umbrella_program = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        limit_choices_to={'ppa_type': PROGRAM}, related_name='projects'
    )
    workflow_status = models.CharField(max_length=10, choices=WORKFLOW, default=DRAFT)

    notice_to_proceed_no = models.CharField(max_length=120, blank=True)
    special_order_no = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=300)
    proponents = models.TextField(blank=True)
    partner_category = models.CharField(max_length=20, choices=PARTNER_TYPES, blank=True)
    partner_name = models.CharField(max_length=240, blank=True)
    with_moa_mou = models.BooleanField(default=False)
    board_confirmed = models.BooleanField(default=False)
    board_resolution_no = models.CharField(max_length=120, blank=True)
    board_resolution_date = models.DateField(null=True, blank=True)

    leader_name = models.CharField(max_length=180, blank=True)
    leader_position = models.CharField(max_length=180, blank=True)
    leader_contact = models.CharField(max_length=220, blank=True)
    assistant_name = models.CharField(max_length=180, blank=True)
    assistant_position = models.CharField(max_length=180, blank=True)
    assistant_contact = models.CharField(max_length=220, blank=True)
    members = models.TextField(blank=True, help_text='One member per line')

    clientele = models.TextField(blank=True)
    target_area = models.CharField(max_length=260, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    project_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    funding_source = models.CharField(max_length=240, blank=True)
    urdea = models.TextField(blank=True)
    sdgs = models.TextField(blank=True)

    termination_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', 'title']

    def __str__(self):
        return self.title

    def clean(self):
        if self.ppa_type == self.PROJECT and self.umbrella_program and self.umbrella_program.ppa_type != self.PROGRAM:
            raise ValidationError({'umbrella_program': 'Umbrella Program must be a Program.'})
        if self.board_confirmed and (not self.board_resolution_no or not self.board_resolution_date):
            raise ValidationError('Board Resolution No. and Date are required when Board Confirmed is Yes.')
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be earlier than start date.'})

    def _latest_activity_entry(self, activity):
        return activity.field_visit_entries.select_related('log').order_by(
            '-log__year', '-log__quarter', '-log__updated_at', '-pk'
        ).first()

    @property
    def completed_activity_count(self):
        count = 0
        for activity in self.activities.all():
            latest = self._latest_activity_entry(activity)
            if latest and latest.result == 'COMPLETED':
                count += 1
        return count

    @property
    def not_conducted_activity_count(self):
        count = 0
        for activity in self.activities.all():
            latest = self._latest_activity_entry(activity)
            if latest and latest.result == 'NOT_CONDUCTED':
                count += 1
        return count

    @property
    def is_completed(self):
        if self.ppa_type != self.PROJECT:
            return False
        total = self.activities.count()
        return total > 0 and self.completed_activity_count >= total

    @property
    def auto_inactive(self):
        """System rule requested by the project team: after the project end date,
        3 or more approved activities whose latest monitoring result is Not Conducted
        marks the project as inactive unless the project is completed.
        """
        return bool(
            self.ppa_type == self.PROJECT
            and self.end_date
            and timezone.localdate() > self.end_date
            and not self.is_completed
            and self.not_conducted_activity_count >= 3
        )

    @property
    def termination_eligible(self):
        return bool(
            self.ppa_type == self.PROJECT
            and self.end_date
            and timezone.localdate() >= self.end_date + timedelta(days=365)
            and not self.is_completed
            and not self.termination_date
        )

    @property
    def impact_assessment_eligible(self):
        return bool(
            self.termination_date
            and timezone.localdate() >= self.termination_date + timedelta(days=365)
        )


class Activity(models.Model):
    project = models.ForeignKey(
        PPA, on_delete=models.CASCADE, related_name='activities',
        limit_choices_to={'ppa_type': PPA.PROJECT}
    )
    title = models.CharField(max_length=300)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=260, blank=True)
    activity_leader = models.CharField(max_length=180, blank=True)
    topics = models.TextField(blank=True)
    objectives = models.TextField(blank=True)
    learning_outcomes = models.TextField(blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['date', 'id']

    def __str__(self):
        return self.title


class ImpactAssessment(models.Model):
    INTERNAL = 'INTERNAL'
    EXTERNAL = 'EXTERNAL'
    TYPES = [(INTERNAL, 'Internal Assessment'), (EXTERNAL, 'External Assessment')]

    project = models.ForeignKey(PPA, on_delete=models.CASCADE, related_name='impact_assessments')
    assessment_type = models.CharField(max_length=12, choices=TYPES)
    date = models.DateField(null=True, blank=True)
    evaluations = models.TextField(blank=True)
    lead = models.CharField(max_length=180, blank=True)
    members = models.TextField(blank=True)

    class Meta:
        unique_together = [('project', 'assessment_type')]


class ExtensionIndicator(models.Model):
    order = models.PositiveIntegerField(unique=True)
    name = models.TextField()
    is_percentage = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.order}. {self.name}'


class QparSubmission(models.Model):
    DRAFT = 'DRAFT'
    SAVED = 'SAVED'
    STATUS = [(DRAFT, 'Draft'), (SAVED, 'Saved')]

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='qpar_submissions')
    year = models.PositiveIntegerField()
    quarter = models.PositiveSmallIntegerField(choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')])
    status = models.CharField(max_length=10, choices=STATUS, default=DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='qpar_submissions')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('unit', 'year', 'quarter')]
        ordering = ['-year', '-quarter', 'unit__name']

    def __str__(self):
        return f'{self.unit} Q{self.quarter} {self.year}'


class QparIndicatorValue(models.Model):
    submission = models.ForeignKey(QparSubmission, on_delete=models.CASCADE, related_name='values')
    indicator = models.ForeignKey(ExtensionIndicator, on_delete=models.PROTECT)
    target = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    accomplishment = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = [('submission', 'indicator')]


class QuarterlyMonitoringReport(models.Model):
    ONGOING = 'ONGOING'
    INACTIVE = 'INACTIVE'
    TERMINATED = 'TERMINATED'
    STATUSES = [
        ('', 'Select status'),
        (ONGOING, 'Ongoing'),
        (INACTIVE, 'Inactive'),
        (TERMINATED, 'Terminated'),
    ]

    project = models.ForeignKey(
        PPA, on_delete=models.PROTECT, related_name='quarterly_monitoring_reports',
        limit_choices_to={'ppa_type': PPA.PROJECT}
    )
    period_start = models.DateField()
    period_end = models.DateField()
    date_conducted = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=260, blank=True)
    funding_source = models.CharField(max_length=240, blank=True)
    total_project_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    phase = models.PositiveSmallIntegerField(choices=[(i, f'Phase {i}') for i in range(1, 8)], null=True, blank=True)
    project_status = models.CharField(max_length=12, choices=STATUSES, blank=True, default='')
    inactive_remarks = models.TextField(blank=True)
    date_of_termination = models.DateField(null=True, blank=True)
    evaluation = models.TextField(blank=True)

    # Prepared by is always the logged-in report creator. The other signatories
    # change by office assignment, so the report stores the names entered for that printout.
    noted_dean_name = models.CharField(max_length=180, blank=True)
    noted_extension_director_name = models.CharField(max_length=180, blank=True)
    approved_vp_name = models.CharField(max_length=180, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='monitoring_reports')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_end', 'project__title']

    def clean(self):
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValidationError({'period_end': 'Period end cannot be earlier than period start.'})
        if not self.project_status:
            raise ValidationError({'project_status': 'Select the project status.'})
        if self.project_status == self.ONGOING and not self.phase:
            raise ValidationError({'phase': 'Select the current phase for an ongoing project.'})
        if self.project_status == self.INACTIVE and not self.inactive_remarks:
            raise ValidationError({'inactive_remarks': 'Remarks are required for inactive projects.'})
        if self.project_status == self.TERMINATED:
            if not self.date_of_termination:
                raise ValidationError({'date_of_termination': 'Date of Termination is required.'})
            if not self.project.end_date:
                raise ValidationError({'project': 'The selected project must have an End Date before termination can be recorded.'})
            eligible_on = self.project.end_date + timedelta(days=365)
            if timezone.localdate() < eligible_on or self.project.is_completed:
                raise ValidationError({'date_of_termination': f'Termination is locked until {eligible_on:%B %d, %Y} and only while the project remains incomplete.'})
            if self.date_of_termination < eligible_on:
                raise ValidationError({'date_of_termination': f'Date of Termination cannot be earlier than {eligible_on:%B %d, %Y}.'})


class FieldVisitLog(models.Model):
    project = models.ForeignKey(
        PPA, on_delete=models.PROTECT, related_name='field_visit_logs',
        limit_choices_to={'ppa_type': PPA.PROJECT}
    )
    year = models.PositiveIntegerField()
    quarter = models.PositiveSmallIntegerField(choices=[(1, '1st Quarter'), (2, '2nd Quarter'), (3, '3rd Quarter'), (4, '4th Quarter')])
    evaluation = models.TextField(blank=True)
    partner_representative_name = models.CharField(max_length=180, blank=True)
    partner_representative_postnominals = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='field_visit_logs')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-year', '-quarter', 'project__title']

    def __str__(self):
        return f'{self.project} - Q{self.quarter} {self.year}'


class FieldVisitEntry(models.Model):
    RESULTS = [
        ('COMPLETED', 'Completed'),
        ('RESCHEDULED', 'Rescheduled'),
        ('NOT_CONDUCTED', 'Not Conducted'),
    ]

    log = models.ForeignKey(FieldVisitLog, on_delete=models.CASCADE, related_name='entries')
    activity = models.ForeignKey(Activity, null=True, blank=True, on_delete=models.SET_NULL, related_name='field_visit_entries')
    objectives = models.TextField(blank=True)
    activities = models.TextField()
    date = models.DateField(null=True, blank=True)
    place = models.CharField(max_length=240, blank=True)
    time = models.TimeField(null=True, blank=True)
    expected_parameter = models.CharField(max_length=240, blank=True)
    expected_target = models.CharField(max_length=240, blank=True)
    person_contacted = models.CharField(max_length=180, blank=True)
    position = models.CharField(max_length=180, blank=True)
    result = models.CharField(max_length=20, choices=RESULTS, default='NOT_CONDUCTED')
    rescheduled_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['date', 'id']

    def clean(self):
        if self.result == 'RESCHEDULED' and not self.rescheduled_date:
            raise ValidationError({'rescheduled_date': 'New date is required when result is Rescheduled.'})
        if self.result != 'RESCHEDULED':
            self.rescheduled_date = None


class ActivityLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=180)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
