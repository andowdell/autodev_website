from django import template
from rest_api.models import UserPrivate

register = template.Library()


@register.filter(name='is_calculator_enabled')
def is_calculator_enabled(user):
    try:
        calc_enabled = UserPrivate.objects.get(user=user).calculator_enabled
    except:
        calc_enabled = False

    return calc_enabled
