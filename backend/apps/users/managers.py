from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import validate_email
from rest_framework.exceptions import ValidationError


class UserManager(BaseUserManager):
    def email_validator(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise ValueError('You must provide a valid email address')

    def create_user(self, email, password, first_name, last_name, **kwargs):
        if not first_name:
            raise ValueError('User must submit a first name')

        if not last_name:
            raise ValueError('User must submit a last name')

        if email:
            email = self.normalize_email(email)
            self.email_validator(email)
        else:
            raise ValueError('User must submit a email')

        kwargs.setdefault("is_staff", False)
        kwargs.setdefault("is_superuser", False)

        user = self.model(
            first_name=first_name,
            last_name=last_name,
            email=email,
            **kwargs
        )

        user.set_password(password)

        user.save(using=self.db)
        return user

    def create_superuser(self, email, password, first_name, last_name, **kwargs):
        kwargs.setdefault("is_staff", True)
        kwargs.setdefault("is_superuser", True)
        from .models import Role
        kwargs.setdefault("role", Role.ADMIN)

        if kwargs.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if kwargs.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        if email:
            email = self.normalize_email(email)
            self.email_validator(email)
        else:
            raise ValueError('Superuser must submit a email')

        return self.create_user(email, password, first_name, last_name, **kwargs)