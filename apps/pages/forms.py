from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import DepartmentProfile


def split_full_name(value):
    parts = value.strip().split(maxsplit=1)
    return (parts[0], parts[1] if len(parts) > 1 else "") if parts else ("", "")


class DokTrakRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full name",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Your full name",
            "autocomplete": "name",
        }),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "you@example.com",
            "autocomplete": "email",
        }),
    )
    department = forms.CharField(
        label="Department",
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Your department",
            "autocomplete": "organization-title",
        }),
    )

    class Meta:
        model = User
        fields = ("username", "full_name", "email")
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Choose a username",
                "autocomplete": "username",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(("username", "full_name", "email", "department", "password1", "password2"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name, user.last_name = split_full_name(self.cleaned_data["full_name"])
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            self.save_m2m()
            DepartmentProfile.objects.update_or_create(
                user=user, defaults={"department": self.cleaned_data["department"]}
            )
        return user


class UserProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        label="Full name",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control dk-profile-input",
            "autocomplete": "name",
        }),
    )
    email = forms.EmailField(
        label="Email address",
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "form-control dk-profile-input",
            "autocomplete": "email",
        }),
    )
    department = forms.CharField(
        label="Department",
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": "form-control dk-profile-input",
            "autocomplete": "organization-title",
        }),
    )

    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["full_name"].initial = self.instance.get_full_name()
            profile, _ = DepartmentProfile.objects.get_or_create(user=self.instance)
            self.fields["department"].initial = profile.department

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name, user.last_name = split_full_name(self.cleaned_data["full_name"])
        if commit:
            user.save()
            DepartmentProfile.objects.update_or_create(
                user=user, defaults={"department": self.cleaned_data["department"]}
            )
        return user
