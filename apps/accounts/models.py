import random
import uuid
from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    GENERAL_SEEKER = "general_seeker", "General Seeker"
    AUTHORITY = "authority", "Found Reporter / Authority"


class AuthorityType(models.TextChoices):
    POLICE = "police", "Police"
    GOVT_EMPLOYEE = "govt_employee", "Govt Employee"
    RAB = "rab", "RAB"
    ARMY = "army", "Army"
    MORGUE_AUTHORITY = "morgue_authority", "Morgue Authority"


class Division(models.TextChoices):
    DHAKA = "dhaka", "Dhaka"
    CHATTOGRAM = "chattogram", "Chattogram"
    RAJSHAHI = "rajshahi", "Rajshahi"
    KHULNA = "khulna", "Khulna"
    BARISHAL = "barishal", "Barishal"
    SYLHET = "sylhet", "Sylhet"
    RANGPUR = "rangpur", "Rangpur"
    MYMENSINGH = "mymensingh", "Mymensingh"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("role", UserRole.AUTHORITY)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Single user table with a role flag, matching the spec's requirement of
    'separate tables/roles' for General Seeker vs Found Reporter / Authority.
    Using one table with a role discriminator keeps auth simple while still
    modelling the two roles distinctly (see role-specific fields below).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20)
    profession = models.CharField(max_length=150, blank=True)
    nid_number = models.CharField("NID Number", max_length=30)

    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.GENERAL_SEEKER)

    # Authority-specific fields (only relevant when role == AUTHORITY)
    is_authority = models.BooleanField(default=False)
    authority_type = models.CharField(
        max_length=30, choices=AuthorityType.choices, blank=True, null=True
    )
    division = models.CharField(
        max_length=20,
        choices=Division.choices,
        blank=True,
        null=True,
        help_text="Required when authority_type is Morgue Authority",
    )

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "phone_number", "nid_number"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def authority_badge(self):
        """e.g. 'Morgue Authority from Sylhet Division'"""
        if not self.is_authority or not self.authority_type:
            return None
        label = self.get_authority_type_display()
        if self.authority_type == AuthorityType.MORGUE_AUTHORITY and self.division:
            return f"{label} from {self.get_division_display()} Division"
        return label


def generate_otp():
    return f"{random.randint(0, 999999):06d}"


def default_otp_expiry():
    return timezone.now() + timedelta(minutes=10)


class EmailVerification(models.Model):
    """
    OTP / verification-link record. Once the user is verified, this is no
    longer checked on future logins (per spec: 'once verified, bypass for
    future logins').
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="email_verification")
    otp_code = models.CharField(max_length=6, default=generate_otp)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    expires_at = models.DateTimeField(default=default_otp_expiry)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at

    def regenerate(self):
        self.otp_code = generate_otp()
        self.token = uuid.uuid4()
        self.expires_at = default_otp_expiry()
        self.is_used = False
        self.save(update_fields=["otp_code", "token", "expires_at", "is_used"])
