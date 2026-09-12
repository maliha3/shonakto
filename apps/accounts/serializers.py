from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import AuthorityType, Division, User, UserRole


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    is_authority = serializers.BooleanField(default=False)
    authority_type = serializers.ChoiceField(choices=AuthorityType.choices, required=False, allow_null=True)
    division = serializers.ChoiceField(choices=Division.choices, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "name",
            "address",
            "phone_number",
            "profession",
            "nid_number",
            "is_authority",
            "authority_type",
            "division",
        ]

    def validate(self, attrs):
        is_authority = attrs.get("is_authority", False)
        authority_type = attrs.get("authority_type")

        if is_authority and not authority_type:
            raise serializers.ValidationError(
                {"authority_type": "Select an authority type when the authority checkbox is checked."}
            )
        if not is_authority:
            attrs["authority_type"] = None
            attrs["division"] = None
        elif authority_type != AuthorityType.MORGUE_AUTHORITY:
            attrs["division"] = None
        elif authority_type == AuthorityType.MORGUE_AUTHORITY and not attrs.get("division"):
            raise serializers.ValidationError(
                {"division": "Select a division for Morgue Authority accounts."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        is_authority = validated_data.pop("is_authority", False)
        validated_data["role"] = UserRole.AUTHORITY if is_authority else UserRole.GENERAL_SEEKER
        validated_data["is_authority"] = is_authority
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    authority_badge = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "address",
            "phone_number",
            "profession",
            "nid_number",
            "role",
            "is_authority",
            "authority_type",
            "division",
            "authority_badge",
            "is_verified",
            "date_joined",
        ]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")
        attrs["user"] = user
        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
