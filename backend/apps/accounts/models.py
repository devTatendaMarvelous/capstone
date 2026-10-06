from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        RESEARCHER = "researcher", "Researcher"
        ANALYST = "analyst", "Analyst"
        FARMER = "farmer", "Farmer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FARMER, db_index=True)
    email = models.EmailField(unique=True)

    def save(self, *args, **kwargs):
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

    @property
    def is_privileged(self) -> bool:
        return self.is_superuser or self.role in {self.Role.ADMIN, self.Role.RESEARCHER, self.Role.ANALYST}
