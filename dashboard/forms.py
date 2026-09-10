from django import forms
from .models import UserProfile, Partnership, ExtensionPPA

BASE_ATTRS = {'class': 'control'}


class UserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs=BASE_ATTRS))
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs=BASE_ATTRS))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs=BASE_ATTRS))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs=BASE_ATTRS))
    role = forms.ChoiceField(choices=[('ADMIN', 'Admin Staff'), ('SCHOOL', 'School Coordinator'), ('CAMPUS', 'Campus Head')], widget=forms.Select(attrs=BASE_ATTRS))
    unit = forms.ChoiceField(choices=[('', '— None for Admin Staff —')] + list(UserProfile._meta.get_field('unit').choices), required=False, widget=forms.Select(attrs=BASE_ATTRS))
    password = forms.CharField(widget=forms.PasswordInput(attrs=BASE_ATTRS))


class UserEditForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs=BASE_ATTRS))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs=BASE_ATTRS))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs=BASE_ATTRS))
    role = forms.ChoiceField(choices=[('ADMIN', 'Admin Staff'), ('SCHOOL', 'School Coordinator'), ('CAMPUS', 'Campus Head')], widget=forms.Select(attrs=BASE_ATTRS))
    unit = forms.ChoiceField(choices=[('', '— None for Admin Staff —')] + list(UserProfile._meta.get_field('unit').choices), required=False, widget=forms.Select(attrs=BASE_ATTRS))
    is_active = forms.BooleanField(required=False)


class PartnershipForm(forms.ModelForm):
    class Meta:
        model = Partnership
        exclude = ['created_by', 'updated_at']
        labels = {
            'partner_id': 'Partner ID',
            'stakeholder_name': 'Partner / Stakeholder Name',
            'partner_type': 'Partner Type',
            'related_extension': 'Related Extension Program / Project',
            'board_confirmed': 'Board Confirmed?',
            'date_signed': 'Date Signed',
            'status': 'Partnership Status',
            'remarks': 'Remarks',
        }
        widgets = {
            'partner_id': forms.TextInput(attrs=BASE_ATTRS),
            'stakeholder_name': forms.TextInput(attrs=BASE_ATTRS),
            'partner_type': forms.Select(attrs=BASE_ATTRS),
            'related_extension': forms.TextInput(attrs=BASE_ATTRS),
            'board_confirmed': forms.CheckboxInput(attrs={'class': 'checkinput'}),
            'date_signed': forms.DateInput(attrs={'type': 'date', 'class': 'control'}),
            'status': forms.Select(attrs=BASE_ATTRS),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'control textarea'}),
        }


class ExtensionPPAForm(forms.ModelForm):
    class Meta:
        model = ExtensionPPA
        exclude = ['created_by', 'updated_at']
        labels = {
            'program_id': 'Program ID',
            'title': 'Program / Project / Activity Title',
            'type': 'Type',
            'implementing_unit': 'College / Implementing Unit',
            'date_approved': 'Date Approved',
            'approved': 'Approved?',
            'board_confirmed': 'Board Confirmed?',
            'trainees': 'No. of Trainees',
            'training_length_days': 'Training Length (days)',
            'internally_assessed': 'Internally Impact Assessed',
            'externally_assessed': 'Externally Impact Assessed',
        }
        widgets = {
            'date_approved': forms.DateInput(attrs={'type': 'date', 'class': 'control'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'control textarea'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.CheckboxInput,)):
                field.widget.attrs['class'] = 'checkinput'
            elif 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'control'
        integer_fields = ['trainees', 'training_length_days', 'faculty_male', 'faculty_female', 'staff_male', 'staff_female', 'student_male', 'student_female']
        for name in integer_fields:
            self.fields[name].widget.attrs.update({'min': '0', 'step': '1', 'inputmode': 'numeric'})

    def clean(self):
        cleaned = super().clean()
        approved = cleaned.get('approved')
        date_approved = cleaned.get('date_approved')
        if approved and not date_approved:
            self.add_error('date_approved', 'Enter the approval date when Approved is checked.')
        if not approved:
            cleaned['date_approved'] = None
        return cleaned
