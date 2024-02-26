import re
import itertools
from django.db.models.expressions import Subquery
from django.forms import TextInput, Textarea
from django.db import models
from datetime import datetime
from django.contrib.admin import widgets
from django.contrib.admin.sites import site
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, DELETION
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.html import escape
from django.core.urlresolvers import reverse
from django.db.models import F, Max, Q, Count, OuterRef
from django.conf.urls import url
from django_admin_json_editor import JSONEditorWidget
from django.contrib.admin.views.main import ChangeList

from web_app.utils import log_exception
from .models import (
    Auction,
    TopAuction,
    AuctionPhoto,
    UserPrivate,
    UserBusiness,
    Bet,
    BetSupervisor,
    LanguageModel,
    AutomateDashboardModel,
    ShortUrlModel,
    ScheduledBet,
    Banner,
    MarketingCampaign,
    BetNotificationsModel,
)

from .views import (LanguageAdminView, AutomateDashboardAdminView, BetNotificationsAdminView)

from django.contrib.auth.models import User
# from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
class DefaultAdmin(admin.ModelAdmin):
    pass


class LogEntryAdmin(admin.ModelAdmin):
    list_display = [
        'action_time',
        'user',
        'content_type',
        'change_message',
        'object_repr',
    ]
    list_filter = [
        'user',
        'content_type',
        'object_repr',
    ]

'''
    date_hierarchy = 'action_time'
    readonly_fields = LogEntry._meta.get_all_field_names()
    search_fields = [
        'object_repr',
        'change_message'
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False

    def action_flag_(self, obj):
        flags = {
            1: "Addition",
            2: "Changed",
            3: "Deleted",
        }
        return flags[obj.action_flag]

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = u'<a href="%s">%s</a>' % (
                reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return link
    object_link.allow_tags = True
    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'object'

'''


class ScheduledBetAdmin(admin.ModelAdmin):
    raw_id_fields = ('bet',)
    list_display = ('name', 'user_bet_price', 'price', 'price_max', 'betted', 'auction_to_end')
    readonly_fields = ('betted',)

    def lookup_allowed(self, key):
        if key in ('auction__end_date__gte', 'auction__end_date', 'auction__subprovider_name', 'auction__subprovider_name__in'):
            return True
        return super(ScheduledBetAdmin, self).lookup_allowed(key)

    def lookup_allowed(self, key, value):
        if key in ('auction__end_date__gte', 'auction__end_date', 'auction__subprovider_name', 'auction__subprovider_name__in'):
            return True
        return super(ScheduledBetAdmin, self).lookup_allowed(key, value)


class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'published',)
    list_editable = ('published', )


class ShortUrlAdmin(admin.ModelAdmin):
    list_display = ('title', 'short_url',)
    readonly_fields = ('short_url',)


class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(BetNotificationsModel)
class BetNotificationsAdmin(admin.ModelAdmin):
    def get_urls(self):
        view_name = '{}_{}_changelist'.format(
                BetNotificationsModel._meta.app_label, BetNotificationsModel._meta.model_name)
        return [
            url(r'^bet-notifications/$', BetNotificationsAdminView.as_view(), name=view_name)
        ]


@admin.register(LanguageModel)
class LanguageAdmin(admin.ModelAdmin):
    def get_urls(self):
        view_name = '{}_{}_changelist'.format(
                LanguageModel._meta.app_label, LanguageModel._meta.model_name)
        return [
            url(r'^languages/$', LanguageAdminView.as_view(), name=view_name)
        ]

@admin.register(AutomateDashboardModel)
class AutomateDashboardAdmin(admin.ModelAdmin):
    def get_urls(self):
        view_name = '{}_{}_changelist'.format(
                AutomateDashboardModel._meta.app_label, AutomateDashboardModel._meta.model_name)
        return [
            url(r'^automatedashboard/$', AutomateDashboardAdminView.as_view(), name=view_name),
            url(r'^automatedashboard/(?P<provider>\w+)/changepass/$', AutomateDashboardAdminView.as_view(), name=view_name)
        ]

def make_published(modeladmin, request, queryset):
    queryset.update(published=True)
make_published.short_description = "Oznacz jako opublikowane"


def make_unpublished(modeladmin, request, queryset):
    queryset.update(published=False)
make_unpublished.short_description = "Oznacz jako nieopublikowane"


def set_top_auction(modeladmin, request, queryset):
    for car in queryset:
        top = TopAuction(auction=car)
        top.save()
set_top_auction.short_description = "Ustaw jako aukcje dnia"


class ArchiveAuctionListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('Archiwum')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('no', _('Aktywne')),
            ('yes', _('Archiwum')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == 'no':
            return queryset.filter(
                end_date__gte=timezone.now()
            )
        if self.value() == 'yes':
            return queryset.filter(
                end_date__lt=timezone.now()
            )


class ColorAuctionListFilter(admin.SimpleListFilter):
    title = _('Kolor')
    parameter_name = 'color'

    def lookups(self, request, model_admin):
        return (
            ('0', _('Biały')),
            ('1', _('Zielony')),
            ('2', _('Niebieski')),
            ('3', _('Pomarańczowy')),
            ('4', _('Czerwony')),
            ('5', _('Złoty')),
        )

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        color = int(self.value())
        bets = Bet.objects.order_by('auction__pk', '-price').distinct('auction__pk')
        bets_max = Bet.objects.filter(pk__in=bets).filter(color=color).values('auction__pk')
        ret_queryset = queryset.filter(pk__in=bets_max)

        return ret_queryset


class AuctionPhotoAdmin(admin.StackedInline):
    model = AuctionPhoto


def dynamic_schema(widget):
    return {
        "type": "object",
    }



class AuctionAdmin(admin.ModelAdmin):
    list_display = ('title', 'ref_id', 'published', 'highlighted', 'first_photo_img', 'provider_name', 'brand', 'to_end_date', 'get_bets')
    readonly_fields = ('first_photo_img', 'ref_id', 'get_bets',)
    list_editable = ('published', 'highlighted',)
    list_per_page = 30
    list_filter = (ArchiveAuctionListFilter, 'provider_name', ColorAuctionListFilter,)
    search_fields = ('title', 'id', 'ref_id', 'provider_id', 'data')
    actions = (make_published, make_unpublished, set_top_auction, )
    inlines = (AuctionPhotoAdmin, )
    exclude = ('images_count', 'min_image', 'ref_id', 'get_bets', )

    def get_queryset(self, request):
        queryset = super(AuctionAdmin, self).get_queryset(request)
        if request.GET.get('is_active', 'yes') == 'no':
            queryset = queryset.filter(
                end_date__gte=timezone.now()
            ).order_by('end_date')
        elif request.GET.get('is_active', None) is None:
            queryset = queryset.order_by('-end_date')

        return queryset


    def get_form(self, request, obj=None, **kwargs):
        widget = JSONEditorWidget(dynamic_schema, False)
        form = super().get_form(request, obj, widgets={'data': widget}, **kwargs)
        return form


class ColorBetListFilter(admin.SimpleListFilter):
    title = _('Kolor')
    parameter_name = 'color'

    def lookups(self, request, model_admin):
        if request.user.groups.filter(name='RestrictedGroup').exists():
                 return (
                ('1', _('Zielony')),
                ('2', _('Niebieski')),
            )
        else:
            return (
                ('0', _('Biały')),
                ('1', _('Zielony')),
                ('2', _('Niebieski')),
                ('3', _('Pomarańczowy')),
                ('4', _('Czerwony')),
                ('5', _('Złoty')),
            )

    def queryset(self, request, queryset):
        print("#### : COLOR_FILTER : ", self.value())
        if self.value() is None:
            if request.user.groups.filter(name='RestrictedGroup').exists():
                return queryset.filter(color__in=[1, 2])
            else:
                return queryset
        color = int(self.value())
        ret_queryset = queryset.filter(color=color)
        return ret_queryset

class BetActiveFilter(admin.SimpleListFilter):
    title = _('Aktywne')
    parameter_name = 'active'

    def lookups(self, request, model_admin):
       return (
           ('yes', _('Tak')),
           ('no', _('Nie')),
       )

    def choices(self, changelist):
        # yield {
        #     'selected': self.value() is None,
        #     'query_string': changelist.get_query_string({}, [self.parameter_name]),
        #     'display': 'Tak',
        #     # 'query_string': changelist.get_query_string(remove=[self.parameter_name]),
        #     # 'display': _('All'),
        # }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == str(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }

    def queryset(self, request, queryset):
        print("#### : BETACTIVE_FILTER : ", self.value())
        query = self.value()
        if query == 'no':
            queryset = queryset.filter(auction_end_date__lt=timezone.now()).order_by('-auction_end_date', '-price' ,'auction')
        else :
            queryset = queryset.filter(auction_end_date__gt=timezone.now()).order_by('auction_end_date', '-price' ,'auction')
        return queryset


class BetAdmin(admin.ModelAdmin):
    raw_id_fields = ('auction', 'user')
    search_fields = ('auction__ref_id', 'user__email', 'auction__title', 'user__id',)
    list_filter = (BetActiveFilter, ColorBetListFilter)
    list_per_page = 100
    list_editable = ('color',)
    # list_select_related = ('auction', 'user', 'user_priv')
    exclude=('user_priv', 'auction_end_date')
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }

    def get_changelist(self, request, **kwargs):
        """
        Return the ChangeList class for use on the changelist page.
        """
        return ChangeList
    
    def get_list_display(self, request):
        if request.user.groups.filter(name='RestrictedGroup').exists():
            return ('auction', 'field_auction_link', 'field_user_registered_restricted', 'price', 'note_admin', 'field_is_bet_automate', 'auction_to_end', 'color',)
        else:
            return ('auction', 'field_auction_link', 'field_user_registered', 'price', 'note_admin', 'field_is_bet_automate', 'auction_to_end', 'color',)
        
    def field_user_registered_restricted(self, obj):
        user = obj.user_priv
        user_bets = ''
        try:
            # user = UserPrivate.objects.get(user=obj.user)
            user_bets = '<a href="/admin/rest_api/bet/?q=%s" style="color:#ac0303;float:right;display:inline-block">licytacje</a>' % obj.user.email
            user = '<span style="display:inline-block;float:left;">%s %s</span> ' % (user.first_name, user.last_name)
            user += user_bets
            return user
        except Exception as e:
            log_exception(e)

        try:
            user = '<span >%s %s</span> ' % (user.first_name, user.last_name)
        except:
            user = str(obj.user.username)
        user += user_bets

        return user
    field_user_registered_restricted.short_description = 'Użytkownik'
    field_user_registered_restricted.allow_tags = True

    def field_user_registered(self, obj):
        user = obj.user_priv
        user_bets = ''
        try:
            # user = UserPrivate.objects.get(user=obj.user)
            user_bets = '<a href="/admin/rest_api/bet/?q=%s" style="color:#ac0303;float:right;display:inline-block">licytacje</a>' % obj.user.email
            user = '<a href="/admin/rest_api/userprivate/%s/change/" style="display:inline-block;float:left;">%s %s</a> ' % (user.id, user.first_name, user.last_name)
            user += user_bets
            return user
        except Exception as e:
            log_exception(e)

        try:
            user = '<a href="/admin/rest_api/userprivate/%s/change/">%s %s</a>' % (user.id, user.first_name, user.last_name)
        except:
            user = str(obj.user.username)
        user += user_bets

        return user
    field_user_registered.short_description = 'Użytkownik'
    field_user_registered.allow_tags = True


    def field_is_bet_automate(self, obj):
        count = obj.scheduledbet_set.count()
        return count > 0
    field_is_bet_automate.boolean = True
    field_is_bet_automate.short_description = 'Automat'

    def field_auction_link(self, obj):
        try:
            bet_count = obj.bet_count
            car_bets = '<a href="/admin/rest_api/bet/?q=%s" style="color:#ac0303;float:right;margin-right:5px">(%s)</a>' % (obj.auction.ref_id, bet_count)
            provider_link = '<a href="%s" target="_blank" style="float:right">%s</a>' % (obj.auction.get_provider_link(), obj.auction.provider_name)
            link = '<a target="_blank" class="admin-auction-short-link" href="%s">Podgląd aukcji</a> ' % obj.auction.get_link()
            if obj.auction.get_provider_link() is not None:
                link += provider_link
            else:
                link += '<span style="float:right">%s</span>' % obj.auction.provider_name
            link += car_bets
            return link
        except Exception as e:
            log_exception(e)
            return "Błąd linku"
    field_auction_link.allow_tags = True
    field_auction_link.short_description = 'Link do aukcji'

    def lookup_allowed(self, key):
        if key in ('auction__end_date__gte', 'auction__end_date', ):
            return True
        return super().lookup_allowed(key)

    def lookup_allowed(self, key, value):
        if key in ('auction__end_date__gte', 'auction__end_date', ):
            return True
        return super().lookup_allowed(key, value)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(BetAdmin, self).get_search_results(request, queryset, search_term)
        print("#### : GET_SEARCH_RESULT: ", search_term)
        if '@' in request.GET.get('q', ''):
            user_private = None
            last_name = 'NOTEXISTENTLASTNAME'
            splitted = search_term.split(' ')
            first_name = splitted[0]
            if len(splitted) > 1:
                last_name = splitted[1]
            try:
                user_private = UserPrivate.objects.filter(
                    Q(user__email__icontains=search_term.strip()) |
                    Q(Q(first_name__icontains=first_name) &
                        Q(last_name__icontains=last_name)) |
                    Q(last_name__icontains=search_term)
                ).first()
            except UserPrivate.DoesNotExist:
                pass

            user_business = None
            try:
                user_business = UserBusiness.objects.get(user__email__icontains=search_term)
            except UserBusiness.DoesNotExist:
                pass

            user = user_private
            if user_business:
                user = user_business

            bets_queryset = queryset.order_by('auction', '-price')
            if user:
                ret_queryset = Bet.objects.filter(user=user.user, id__in=bets_queryset)
            else:
                ret_queryset = Bet.objects.filter(id__in=bets_queryset)

            ret_queryset = ret_queryset.select_related('auction', 'user').prefetch_related('scheduledbet_set').annotate(
                bet_count=Count('auction__bet'),
            ).extra(
                select={
                    'is_recent': "CASE WHEN \"rest_api_auction\".\"end_date\" < '%s' THEN '01-01-2037' ELSE \"rest_api_auction\".\"end_date\" END" % timezone.now(), 
                    'is_recent2': "CASE WHEN \"rest_api_auction\".\"end_date\" > '%s' THEN '01-01-1970' ELSE \"rest_api_auction\".\"end_date\" END" % timezone.now() 
                }
            ).order_by('is_recent', '-is_recent2', 'auction', '-price', 'auction')

            return ret_queryset, use_distinct
        else:
            print("### : case 4 : ")
            ret_queryset = queryset.select_related('auction', 'user', 'user_priv').prefetch_related('scheduledbet_set').annotate(
                bet_count=Count('auction__bet'),
            )      
            return ret_queryset, use_distinct

    def get_queryset(self, request):
        queryset = super(BetAdmin, self).get_queryset(request)
        print("#### : GET_QUERYSET")
        if request.META.get('HTTP_REFERER', '').strip().endswith('/admin/rest_api/scheduledbet/add/'):
            bets_queryset = queryset.order_by('auction', '-price').distinct('auction')
            return Bet.objects.filter(
                Q(id__in=bets_queryset) & 
                Q(auction_end_date__gte=timezone.now()) &
                ~Q(auction__subprovider_name__in=['Vaudoise Assurances'])
                )     
        else:    
            bets_queryset = queryset.order_by('auction', '-price').distinct('auction')
            return Bet.objects.filter(id__in=bets_queryset)

class BetSupervisorAdmin(admin.ModelAdmin):
    raw_id_fields = ('auction',)
    list_display = ('auction_link', 'user_registered', 'price', 'auction_to_end', 'color',)
    #readonly_fields = ('user',)

    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':2, 'cols':40})},
    }

    def get_readonly_fields(self, request, obj=None):
        if obj: #This is the case when obj is already created i.e. it's an edit
            return ('user', )
        else:
            return []

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(BetSupervisorAdmin, self).get_search_results(request, queryset, search_term)
        current_user = UserPrivate.objects.get(user=request.user)
        managed_priv_users = UserPrivate.objects.filter(user_top=current_user)
        managed_users = [us.user for us in managed_priv_users]
        queryset = queryset.filter(user__in=managed_users)

        user_private = None
        last_name = 'NOTEXISTENTLASTNAME'
        splitted = search_term.split(' ')
        first_name = splitted[0]
        if len(splitted) > 1:
            last_name = splitted[1]
        try:
            user_private = UserPrivate.objects.filter(
                Q(user__email__icontains=search_term) |
                Q(Q(first_name__icontains=first_name) &
                    Q(last_name__icontains=last_name)) |
                Q(last_name__icontains=search_term)
            ).first()
        except UserPrivate.DoesNotExist:
            pass

        user_business = None
        try:
            user_business = UserBusiness.objects.get(user__email__icontains=search_term)
        except UserBusiness.DoesNotExist:
            pass

        user = user_private
        if user_business:
            user = user_business

        if not user:
            return queryset, use_distinct

        managed_users.append(user.user)
        bets = BetSupervisor.objects.filter(user__in=managed_users)
        queryset |= bets

        if request.GET.get('q', None) is not None and request.GET.get('q', None):
            ret_queryset = queryset.order_by('auction', '-price').distinct('auction')

            queryset_low = queryset.filter(id__in=ret_queryset, auction__end_date__gt=timezone.now())
            queryset_high = queryset.filter(id__in=ret_queryset, auction__end_date__lt=timezone.now())

            ret_queryset = queryset.extra(
                 select={
                     'is_recent': "CASE WHEN \"rest_api_auction\".\"end_date\" < '%s' THEN '01-01-2037' ELSE \"rest_api_auction\".\"end_date\" END" % timezone.now(), 
                     'is_recent2': "CASE WHEN \"rest_api_auction\".\"end_date\" > '%s' THEN '01-01-1970' ELSE \"rest_api_auction\".\"end_date\" END" % timezone.now(), 
                 }).order_by('is_recent', '-is_recent2', '-price')

            return ret_queryset, use_distinct

        return queryset, use_distinct

    def get_queryset(self, request):
        queryset = super(BetSupervisorAdmin, self).get_queryset(request)
        current_user = UserPrivate.objects.get(user=request.user)
        managed_priv_users = UserPrivate.objects.filter(user_top=current_user)
        managed_users = [us.user for us in managed_priv_users]
        queryset = queryset.filter(user__in=managed_users)

        if '@' in request.GET.get('q', ''):
            return queryset

        ret_queryset = None
        if request.build_absolute_uri().endswith('admin/rest_api/bet/'):
            ret_queryset = queryset.order_by('auction', '-price').distinct('auction')
        else:
            ret_queryset = queryset

        queryset_low = queryset.filter(id__in=ret_queryset, auction__end_date__gt=timezone.now());
        queryset_high = queryset.filter(id__in=ret_queryset, auction__end_date__lt=timezone.now());

        ret_queryset = queryset_low | queryset_high
        # ret_queryset = ret_queryset.extra(select={'is_recent': "\"rest_api_auction\".\"end_date\" < '%s'" % timezone.now()}).order_by('is_recent', 'auction__end_date')
        ret_queryset = ret_queryset.extra(
             select={
                 'is_recent': "CASE WHEN \"rest_api_auction\".\"end_date\" < '%s' THEN '01-01-2037' ELSE \"rest_api_auction\".\"end_date\" END" % timezone.now(), 
                 'is_recent2': "CASE WHEN \"rest_api_auction\".\"end_date\" > '%s' THEN '01-01-1970' ELSE \"rest_api_auction\".\"end_date\" END" % timezone.now(), 
             }).order_by('is_recent', '-is_recent2', '-price')

        return ret_queryset

class AuctionPhotoAdmin(admin.ModelAdmin):
    pass


class UserAdmin(admin.ModelAdmin):
    raw_id_fields = ('user_top',)
    list_display = ('first_name', 'last_name', 'phone_number', 'email', 'accepted', 'note', 'bets', )
    list_per_page = 30
    list_editable = ('accepted', )
    search_fields = ('first_name', 'last_name', 'phone_number', 'lookup',)


class UserBusinessAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'second_name', 'business_name', 'phone_number', 'email', 'accepted', 'note', 'bets', )
    list_per_page = 30
    search_fields = ('first_name', 'second_name', 'phone_number', 'business_name', )
    list_editable = ('accepted', )


class TopAuctionAdmin(admin.ModelAdmin):
    list_display = ('get_title', 'get_photo_auction', 'admin_link', 'get_end_date', )


admin.site.register(Auction, AuctionAdmin)
admin.site.register(TopAuction, TopAuctionAdmin)
# admin.site.register(AuctionPhoto, DefaultAdmin)
admin.site.register(UserPrivate, UserAdmin)
# admin.site.register(UserBusiness, UserBusinessAdmin)
admin.site.register(Bet, BetAdmin)
admin.site.register(BetSupervisor, BetSupervisorAdmin)
admin.site.register(ShortUrlModel, ShortUrlAdmin)
admin.site.register(ScheduledBet, ScheduledBetAdmin)
admin.site.register(Banner, BannerAdmin)

#admin.site.unregister(User)
#admin.site.unregister(Group)
#admin.site.unregister(Site)
#admin.site.unregister(Token)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(MarketingCampaign, MarketingCampaignAdmin)
        