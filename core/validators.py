"""Validation shared by every user-uploaded image."""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']

validate_image_extension = FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS)


def validate_image_size(file):
    limit = settings.MAX_UPLOAD_SIZE
    if file.size > limit:
        raise ValidationError(f'Images must be smaller than {limit // (1024 * 1024)} MB.')


IMAGE_VALIDATORS = [validate_image_extension, validate_image_size]


@deconstructible
class RandomFilename:
    """upload_to callable: store uploads under a random name.

    The original filename is attacker-controlled; it is replaced by a UUID so
    that it cannot collide with, overwrite or be used to guess other files.
    Only the (already validated) extension is kept.
    """

    def __init__(self, prefix):
        self.prefix = prefix

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        return f'{self.prefix}/{uuid.uuid4().hex}{ext}'
