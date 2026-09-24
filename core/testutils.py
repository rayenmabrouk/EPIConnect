"""Helpers shared by the test suites."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from users.models import StudentProfile, User

PASSWORD = 'Str0ng-Test-Passw0rd!'


def make_user(username, verified=True, **extra):
    user = User.objects.create_user(
        username=username, email=f'{username}@epi.test', password=PASSWORD, **extra
    )
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    profile.student_id = f'EPI-{username}'
    profile.is_verified = verified
    profile.save()
    return user


def png_upload(name='photo.png', size=(8, 8)):
    buf = io.BytesIO()
    Image.new('RGB', size, (200, 30, 30)).save(buf, format='PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')
