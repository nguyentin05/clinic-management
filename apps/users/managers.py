from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class UserManager(BaseUserManager):
    def email_validator(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('You must provide a valid email address')

    def create_user(self, email, password, first_name, last_name, **extra_fields):
        if not first_name:
            raise ValueError('User must submit a first name')

        if not last_name:
            raise ValueError('User must submit a last name')

        if email:
            email = self.normalize_email(email)
            self.email_validator(email)
        else:
            raise ValueError('User must submit a email')

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email=email,
            **extra_fields
        )

        user.set_password(password)

        user.save(using=self.db)
        return user

    def create_superuser(self, email, password, first_name, last_name, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        from .models import UserRole
        extra_fields.setdefault("user_role", UserRole.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, first_name, last_name, **extra_fields)