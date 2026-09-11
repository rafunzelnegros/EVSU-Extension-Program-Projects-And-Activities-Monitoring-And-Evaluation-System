from django import forms
from .models import *


class DateInput(forms.DateInput):
    input_type = 'date'


class TimeInput(forms.TimeInput):
    input_type = 'time'


class PPAForm(forms.ModelForm):
    class Meta:
        model = PPA
        fields = [
            'notice_to_proceed_no', 'special_order_no', 'title', 'umbrella_program',
            'proponents', 'partner_category', 'partner_name', 'with_moa_mou',
            'board_confirmed', 'board_resolution_no', 'board_resolution_date',
            'leader_name', 'leader_position', 'leader_contact', 'assistant_name',
            'assistant_position', 'assistant_contact', 'members', 'clientele',
            'target_area', 'start_date', 'end_date', 'project_cost', 'funding_source',
            'urdea', 'sdgs'
        ]
        widgets = {
            'notice_to_proceed_no': forms.TextInput(attrs={'placeholder': 'Input the Notice to Proceed number'}),
            'special_order_no': forms.TextInput(attrs={'placeholder': 'Input the Special Order number'}),
            'board_resolution_date': DateInput(),
            'start_date': DateInput(),
            'end_date': DateInput(),
            'proponents': forms.Textarea(attrs={'rows': 2}),
            'members': forms.Textarea(attrs={'rows': 3, 'placeholder': 'One member per line'}),
            'clientele': forms.Textarea(attrs={'rows': 2}),
            'urdea': forms.Textarea(attrs={'rows': 3}),
            'sdgs': forms.Textarea(attrs={'rows': 3}),
        }


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'date', 'time', 'venue', 'activity_leader', 'topics', 'objectives', 'learning_outcomes', 'budget']
        widgets = {
            'date': DateInput(), 'time': TimeInput(),
            'topics': forms.Textarea(attrs={'rows': 2}),
            'objectives': forms.Textarea(attrs={'rows': 2}),
            'learning_outcomes': forms.Textarea(attrs={'rows': 2}),
        }


class ImpactAssessmentForm(forms.ModelForm):
    class Meta:
        model = ImpactAssessment
        fields = ['date', 'evaluations', 'lead', 'members']
        widgets = {
            'date': DateInput(),
            'evaluations': forms.Textarea(attrs={'rows': 5}),
            'members': forms.Textarea(attrs={'rows': 3, 'placeholder': '1.\n2.\n3.'}),
        }


class QuarterlyMonitoringReportForm(forms.ModelForm):
    class Meta:
        model = QuarterlyMonitoringReport
        exclude = ['created_by']
        labels = {
            'period_start': 'Project Start Date',
            'period_end': 'Project End Date',
            'phase': 'Current Project Phase',
            'noted_dean_name': 'Campus Director / Dean',
            'noted_extension_director_name': 'Extension Director',
            'approved_vp_name': 'VP for OPRDEXS',
        }
        widgets = {
            'period_start': DateInput(attrs={'readonly': 'readonly'}),
            'period_end': DateInput(attrs={'readonly': 'readonly'}),
            'date_conducted': DateInput(),
            'date_of_termination': DateInput(),
            'evaluation': forms.Textarea(attrs={'rows': 7, 'placeholder': 'Enter the monitoring and evaluation narrative...'}),
            'inactive_remarks': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Explain why the project is inactive...'}),
            'noted_dean_name': forms.TextInput(attrs={'placeholder': 'Input current Campus Director / Dean name'}),
            'noted_extension_director_name': forms.TextInput(attrs={'placeholder': 'Input current Extension Director name'}),
            'approved_vp_name': forms.TextInput(attrs={'placeholder': 'Input current VP for OPRDEXS name'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project_status'].required = True
        self.fields['project_status'].initial = ''
        self.fields['phase'].required = False
        self.fields['inactive_remarks'].required = False
        self.fields['date_of_termination'].required = False


class FieldVisitLogForm(forms.ModelForm):
    class Meta:
        model = FieldVisitLog
        fields = [
            'project', 'year', 'quarter', 'evaluation',
            'partner_representative_name', 'partner_representative_postnominals'
        ]
        widgets = {'evaluation': forms.Textarea(attrs={'rows': 7})}


class FieldVisitEntryForm(forms.ModelForm):
    class Meta:
        model = FieldVisitEntry
        exclude = ['log', 'activity']
        widgets = {
            'objectives': forms.Textarea(attrs={'rows': 2}),
            'activities': forms.Textarea(attrs={'rows': 2}),
            'date': DateInput(), 'time': TimeInput(),
            'rescheduled_date': DateInput(),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }


class UserManageForm(forms.Form):
    username = forms.CharField(max_length=150, label='Username')
    first_name = forms.CharField(max_length=150, required=True, label='First name')
    last_name = forms.CharField(max_length=150, required=True, label='Last name')
    email = forms.EmailField(required=False)
    role = forms.ChoiceField(choices=UserProfile.ROLES)
    unit = forms.ModelChoiceField(queryset=Unit.objects.none(), required=False, label='Assigned school/campus')
    password = forms.CharField(
        widget=forms.PasswordInput, required=False,
        help_text='Required for new users; leave blank to use the temporary default password.'
    )
    is_active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit'].queryset = Unit.objects.filter(active=True)
