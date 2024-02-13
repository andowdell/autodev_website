from django import template
from web_app.language_manager import LanguageManager

register = template.Library()


@register.simple_tag(name='trans2', takes_context=True)
def trans2(context, lang, key):
    if not lang:
        lang = 'pl'

    translations = context.get('translations', None)
    if not translations:
        lm = LanguageManager()
        return lm.get_trans_by_lang(lang, key)
    else:
        return LanguageManager.get_trans_by_dict(lang, key, translations)
