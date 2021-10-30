from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.is_active = True
        return user
