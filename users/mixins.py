from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render


class VerifiedStudentMixin(LoginRequiredMixin):
    """Block access unless the user has a verified student profile."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        profile = getattr(request.user, 'profile', None)
        if not profile or not profile.is_verified:
            return render(request, 'users/verification_required.html', status=403)
        return super().dispatch(request, *args, **kwargs)
