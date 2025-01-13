from django.db import models
from django.contrib.auth.models import User
from vote.models import VoteModel
from django.contrib.contenttypes.fields import GenericRelation
from hitcount.models import HitCountMixin, HitCount
from django.utils import timezone
from django.apps import apps


class Profile(VoteModel, models.Model, HitCountMixin):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=500)
    torn_id = models.CharField(max_length=250, null=True, unique=True)
    image = models.ImageField(
        default='profile_pics/default.jpg', upload_to='profile_pics')
    api_key = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activity_status = models.CharField(max_length=250, null=True)
    last_active = models.DateTimeField(null=True)
    work_stats_int = models.IntegerField(null=True)
    work_stats_end = models.IntegerField(null=True)
    work_stats_man = models.IntegerField(null=True)
    work_stats_total = models.IntegerField(null=True)
    hit_count_generic = GenericRelation(
        HitCount, object_id_field='object_pk',
        related_query_name='hit_count_generic_relation')

    te_plus_status = models.BooleanField(default=False)
    te_plus_days = models.IntegerField(null=True)
    active_trader = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        try:
            self.work_stats_total = self.work_stats_end + \
                self.work_stats_int + self.work_stats_man
        except TypeError:
            self.work_stats_total = None
        super().save(*args, **kwargs)
        Settings.objects.get_or_create(owner=self)

    def __str__(self):
        return f'{self.name} Profile'


class Settings(models.Model):
    owner = models.OneToOneField(
        Profile, on_delete=models.CASCADE, related_name='settings')
    trade_list_description = models.CharField(
        max_length=500, null=True, blank=True)
    trade_enable_sets = models.BooleanField(default=True)
    service_list_description = models.CharField(
        max_length=500, null=True, blank=True)
    link_to_forum_post = models.CharField(
        max_length=250, null=True, blank=True)
    receipt_paste_text = models.TextField(
        max_length=250, null=True, blank=True)
    tutorial = models.BooleanField(default=True)
    selling_revives = models.BooleanField(default=False)
    selling_losses = models.BooleanField(default=False)
    revives_message = models.CharField(max_length=140, null=True, blank=True)
    losses_message = models.CharField(max_length=140, null=True, blank=True)
    job_seeking = models.BooleanField(default=False)
    job_message = models.CharField(max_length=140, null=True, blank=True)
    job_post_start_date = models.DateTimeField(auto_now_add=True)
    selling_company = models.BooleanField(default=False)
    selling_company_price_negotiable = models.BooleanField(default=False)
    selling_company_asking_price = models.BigIntegerField(default=0)
    selling_company_description = models.CharField(
        max_length=140, null=True, blank=True)
    company_looking_to_hire = models.BooleanField(default=False)
    company_looking_to_hire_message = models.CharField(
        max_length=140, null=True, blank=True)
    __job_seeking = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__job_seeking = self.job_seeking

    def __str__(self):
        return f'{self.owner.name}- Settings'

    def save(self, *args, **kwargs):
        if self.pk:
            if self.job_seeking != self.__job_seeking and self.job_seeking == True:
                self.job_post_start_date = timezone.now()
                print('updated creation date')
            self.__job_seeking = self.job_seeking
        players_company = apps.get_model(
            'main', 'Company').objects.filter(owner=self.owner).first()
        if players_company is not None:
            players_company.asking_price = self.selling_company_asking_price
            players_company.description = self.selling_company_description
            players_company.negotiable = self.selling_company_price_negotiable
            players_company.company_looking_to_hire_message = self.company_looking_to_hire_message
            players_company.save()
            if self.selling_company == False and self.company_looking_to_hire == False:
                players_company.delete()
        super().save(*args, **kwargs)
# Create your models here.
