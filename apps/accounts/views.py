from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import EmailVerification
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    ResendOTPSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from .tasks import send_otp_email


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a General Seeker or Authority account. If `is_authority` is
    true, `authority_type` is required, and `division` is required when
    authority_type == 'morgue_authority'. Sends an OTP email for first-time
    verification.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        verification = EmailVerification.objects.create(user=user)
        send_otp_email.delay(user.email, user.name, verification.otp_code)

        return Response(
            {
                "message": "Registration successful. Please verify your email with the OTP we sent you.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(APIView):
    """POST /api/auth/verify-otp/ — confirms the OTP and marks the account verified permanently."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp_code"]

        try:
            verification = EmailVerification.objects.select_related("user").get(
                user__email__iexact=email
            )
        except EmailVerification.DoesNotExist:
            return Response({"detail": "No pending verification for this email."}, status=404)

        if verification.otp_code != otp_code or not verification.is_valid():
            return Response({"detail": "Invalid or expired OTP."}, status=400)

        verification.is_used = True
        verification.save(update_fields=["is_used"])

        user = verification.user
        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return Response({"message": "Email verified successfully.", **_tokens_for(user)})


class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            verification = EmailVerification.objects.select_related("user").get(
                user__email__iexact=email
            )
        except EmailVerification.DoesNotExist:
            return Response({"detail": "No pending verification for this email."}, status=404)

        if verification.user.is_verified:
            return Response({"detail": "Account already verified."}, status=400)

        verification.regenerate()
        send_otp_email.delay(verification.user.email, verification.user.name, verification.otp_code)
        return Response({"message": "OTP resent."})


class LoginView(APIView):
    """
    POST /api/auth/login/
    Once a user is verified, subsequent logins bypass OTP entirely.
    Unverified users can still log in but the response flags is_verified=False
    so the app can route them back to the OTP screen.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        response_data = {"user": UserSerializer(user).data}
        if user.is_verified:
            response_data.update(_tokens_for(user))
        else:
            response_data["message"] = "Please verify your email with the OTP before continuing."
        return Response(response_data)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
