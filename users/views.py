from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.views import View
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.shortcuts import get_object_or_404
from .forms import UserRegistrationForm, UserUpdateForm, StudentProfileForm, CustomAuthenticationForm
from .models import User, StudentProfile


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        form = UserRegistrationForm()
        return render(request, 'users/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile, created = StudentProfile.objects.get_or_create(
                user=user,
            )
            if created or not profile.student_id:
                profile.student_id = form.cleaned_data['student_id']
                profile.save()

            return redirect('users:login')
        return render(request, 'users/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    form_class = CustomAuthenticationForm


class CustomLogoutView(LogoutView):
    next_page = 'core:home'


class ProfileView(View):
    def get(self, request, pk):
        from wallet.models import Badge, Wallet
        profile_user = get_object_or_404(User, pk=pk)
        profile, _ = StudentProfile.objects.get_or_create(user=profile_user)
        badges = Badge.objects.filter(user=profile_user)
        wallet = Wallet.objects.filter(user=profile_user).first()
        return render(request, 'users/profile.html', {
            'profile_user': profile_user,
            'profile': profile,
            'badges': badges,
            'wallet': wallet,
        })


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'users/dashboard.html')


class ProfileUpdateView(LoginRequiredMixin, View):
    def get(self, request):
        user_form = UserUpdateForm(instance=request.user)
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        profile_form = StudentProfileForm(instance=profile)
        return render(request, 'users/profile_edit.html', {
            'user_form': user_form,
            'profile_form': profile_form,
        })

    def post(self, request):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        profile_form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:dashboard')
        return render(request, 'users/profile_edit.html', {
            'user_form': user_form,
            'profile_form': profile_form,
        })


@login_required
@require_POST
def remove_profile_picture(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    if profile.profile_picture:
        profile.profile_picture.delete(save=False)
        profile.profile_picture = None
        profile.save()
        messages.success(request, 'Profile picture removed.')
    return redirect('users:profile_edit')
