import hashlib
from django.contrib.auth.models import User
from rest_api.models import UserPrivate
from rest_api.models import UserBusiness


class CustomBackend(object):
    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        flag = False

        try:
            user_custom = UserPrivate.objects.get(user=user)
        except UserPrivate.DoesNotExist:
            flag = False

        if not flag:
            try:
                user_custom = UserBusiness.objects.get(user=user)
            except UserPrivate.DoesNotExist:
                flag = False

        if not flag:
            return None

        m = hashlib.sha1()
        pass2hash = password + user_custom.slug + user_custom.slug
        m.update(pass2hash.encode('UTF-8'))

        if m.hexdigest() == user.password:
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
