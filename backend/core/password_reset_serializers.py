from rest_framework import serializers


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    # Six-digit codes are used for new requests. The second pattern keeps
    # unexpired 43-character tokens sent before deployment usable.
    token = serializers.CharField(min_length=6, max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(min_length=1, max_length=128, write_only=True)

    def validate_token(self, value):
        if value.isascii() and value.isdigit() and len(value) == 6:
            return value
        if 32 <= len(value) <= 128 and all(
            character.isascii() and (character.isalnum() or character in "_-")
            for character in value
        ):
            return value
        raise serializers.ValidationError("Saisissez un code à 6 chiffres valide.")
