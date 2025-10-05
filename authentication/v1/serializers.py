from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "a"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["profile_picture"] = instance.profile_picture
        return data
