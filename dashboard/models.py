from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from django.db import models

UNITS = [
    ('SAAD', 'School of Architecture and Allied Disciplines (SAAD)'),
    ('SAS', 'School of Arts and Sciences (SAS)'),
    ('SAME', 'School of Applied Mathematics and Economics (SAME)'),
    ('SOT', 'School of Technology (SOT)'),
    ('SOE', 'School of Engineering (SOE)'),
    ('SOED', 'School of Education (SOEd)'),
    ('BURAUEN', 'Burauen Campus'),
    ('CARIGARA', 'Carigara Campus'),
    ('DULAG', 'Dulag Campus'),
    ('ORMOC', 'Ormoc City Campus'),
    ('TANAUAN', 'Tanauan Campus'),
]
ROLES = [('DIRECTOR', 'Director'), ('ADMIN', 'Admin Staff'), ('SCHOOL', 'School Coordinator'), ('CAMPUS', 'Campus Head')]
REPORT_STATUS = [('DRAFT', 'Draft'), ('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('RETURNED', 'Returned')]


def validate_pdf_size(file):
    if file and file.size > 10 * 1024 * 1024:
        raise ValidationError('PDF must be 10 MB or smaller.')


def validate_pdf_content(file):
    content_type = getattr(file, 'content_type', '')
    if file and content_type and content_type not in ('application/pdf', 'application/x-pdf'):
        raise ValidationError('Only PDF files are allowed.')


PDF_VALIDATORS = [FileExtensionValidator(['pdf']), validate_pdf_size, validate_pdf_content]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLES, default='SCHOOL')
    unit = models.CharField(max_length=20, choices=UNITS, blank=True)

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'

    @property
    def identity_label(self):
        if self.role == 'ADMIN':
            return 'Admin Staff'
        if self.unit:
            return dict(UNITS).get(self.unit, self.unit)
        return self.get_role_display()


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='extension_notifications')
    title = models.CharField(max_length=180)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ExtensionIndicator(models.Model):
    order = models.PositiveIntegerField(unique=True)
    name = models.TextField()
    uacs_code = models.CharField(max_length=60, blank=True)
    is_percentage = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.order}. {self.name}'


class TaepReport(models.Model):
    budget_year = models.PositiveIntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taep_reports')
    unit = models.CharField(max_length=20, choices=UNITS, blank=True)
    status = models.CharField(max_length=12, choices=REPORT_STATUS, default='DRAFT')
    director_comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['budget_year', 'unit'], name='unique_taep_year_unit_v7')]
        ordering = ['-budget_year', '-updated_at']

    @property
    def display_unit(self):
        return dict(UNITS).get(self.unit, self.unit) if self.unit else 'Consolidated'

    def __str__(self):
        return f'TAEP {self.budget_year} - {self.display_unit}'


class TaepQuarterEntry(models.Model):
    report = models.ForeignKey(TaepReport, on_delete=models.CASCADE, related_name='quarter_entries')
    indicator = models.ForeignKey(ExtensionIndicator, on_delete=models.PROTECT)
    quarter = models.PositiveSmallIntegerField(choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')])
    target = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    saad = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sas = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    same = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    soe = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    soed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    burauen = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    carigara = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    dulag = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ormoc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tanauan = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['report', 'indicator', 'quarter'], name='unique_taep_indicator_quarter_v7')]

    @property
    def total(self):
        fields = ['saad', 'sas', 'same', 'sot', 'soe', 'soed', 'burauen', 'carigara', 'dulag', 'ormoc', 'tanauan']
        return sum((getattr(self, field) or 0) for field in fields)


class TaepIndicatorMeta(models.Model):
    report = models.ForeignKey(TaepReport, on_delete=models.CASCADE, related_name='indicator_meta')
    indicator = models.ForeignKey(ExtensionIndicator, on_delete=models.PROTECT)
    remarks = models.TextField(blank=True)
    mov_pdf = models.FileField(upload_to='movs/taep/%Y/%m/', validators=PDF_VALIDATORS, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['report', 'indicator'], name='unique_taep_indicator_meta_v7')]


class QparReport(models.Model):
    QUARTERS = [(1, 'First Quarter'), (2, 'Second Quarter'), (3, 'Third Quarter'), (4, 'Fourth Quarter')]
    year = models.PositiveIntegerField()
    quarter = models.PositiveSmallIntegerField(choices=QUARTERS)
    revision_no = models.PositiveIntegerField(default=1)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qpar_reports')
    unit = models.CharField(max_length=20, choices=UNITS, blank=True)
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=REPORT_STATUS, default='DRAFT')
    director_comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['year', 'quarter', 'unit', 'revision_no'], name='unique_qpar_revision_v7')]
        ordering = ['-year', '-quarter', '-updated_at']

    @property
    def display_name(self):
        base = f'{self.year} {self.get_quarter_display()} QPAR'
        return base if self.revision_no == 1 else f'{base} ({self.revision_no})'

    @property
    def display_unit(self):
        return dict(UNITS).get(self.unit, self.unit) if self.unit else 'Consolidated'

    def __str__(self):
        return f'{self.display_name} - {self.display_unit}'


class QparEntry(models.Model):
    report = models.ForeignKey(QparReport, on_delete=models.CASCADE, related_name='entries')
    indicator = models.CharField(max_length=500)
    target = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    saad = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sas = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    same = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    soe = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    soed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    burauen = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    carigara = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    dulag = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ormoc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tanauan = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mov_pdf = models.FileField(upload_to='movs/qpar/%Y/%m/', validators=PDF_VALIDATORS, blank=True, null=True)
    remarks = models.TextField(blank=True)

    @property
    def total(self):
        fields = ['saad', 'sas', 'same', 'sot', 'soe', 'soed', 'burauen', 'carigara', 'dulag', 'ormoc', 'tanauan']
        return sum((getattr(self, field) or 0) for field in fields)


class Partnership(models.Model):
    PARTNER_TYPES = [('LGU', 'LGU'), ('INDUSTRY', 'Industry'), ('SME', 'SME'), ('OTHER', 'Other')]
    PARTNERSHIP_STATUS = [('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')]
    partner_id = models.CharField(max_length=50, unique=True)
    stakeholder_name = models.CharField(max_length=255)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPES)
    related_extension = models.CharField(max_length=255, blank=True)
    board_confirmed = models.BooleanField(default=False)
    date_signed = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PARTNERSHIP_STATUS, default='ACTIVE')
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.stakeholder_name


class ExtensionPPA(models.Model):
    TYPES = [('PROGRAM', 'Program'), ('PROJECT', 'Project'), ('ACTIVITY', 'Activity')]
    STATUSES = [('ONGOING', 'Ongoing'), ('TERMINATED', 'Terminated'), ('INACTIVE', 'Inactive')]
    program_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPES)
    implementing_unit = models.CharField(max_length=20, choices=UNITS)
    date_approved = models.DateField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    board_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUSES, default='ONGOING')
    trainees = models.PositiveIntegerField(default=0)
    training_length_days = models.PositiveIntegerField(default=0)
    faculty_male = models.PositiveIntegerField(default=0)
    faculty_female = models.PositiveIntegerField(default=0)
    staff_male = models.PositiveIntegerField(default=0)
    staff_female = models.PositiveIntegerField(default=0)
    student_male = models.PositiveIntegerField(default=0)
    student_female = models.PositiveIntegerField(default=0)
    internally_assessed = models.BooleanField(default=False)
    externally_assessed = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def weighted_trainees(self):
        return self.trainees * self.training_length_days

    def __str__(self):
        return self.title


class ActivityLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
