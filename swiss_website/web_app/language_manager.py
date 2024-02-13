import os 
import json

from django.conf import settings
from django.core.cache import cache

from rest_api.models import UserPrivate


class LanguageManager:
    trans_path = os.path.join(settings.BASE_DIR, 'web_app/translations.json')
    cache_key = 'translations'

    def __init__(self):
        with open(self.trans_path, 'r') as f:
            translations = json.load(f)
            cache.set(self.cache_key, translations, None)
        self.translations = translations

    def get_lang(self, user=None, request=None):
        if request:
            lang = request.COOKIES.get('lang', 'pl')
            return lang
            
        try:
            user = UserPrivate.objects.get(user=user)
            return user.lang
        except:
            return 'pl'
            
    def set_lang(self, user, lang):
        user = UserPrivate.objects.get(user=user)
        user.lang = lang
        user.save()

    def update_trans(self, translations_string):
        with open(self.trans_path, 'w') as f:
            f.write(translations_string)
        translations = json.loads(translations_string)

        cache.set(self.cache_key, translations, None)
        self.translations = translations
    
    def get_trans(self, user, key):
        lang = self.get_lang(user)
        return self.translations[lang][key]

    @staticmethod
    def get_trans_by_dict(lang, key, translations):
        return translations[lang][key]

    def get_trans_by_lang(self, lang, key):
        return self.translations[lang][key]

    def get_trans_dict(self):
        return self.translations
