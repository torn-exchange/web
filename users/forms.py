from django import forms
from .models import Settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, Field, HTML
from crispy_forms.bootstrap import PrependedAppendedText


class UserRegisterForm(UserCreationForm):
    torn_id = forms.IntegerField(required=True)

    class Meta:
        model = User
        fields = ['username', 'torn_id', 'password1', 'password2']


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = [
            'selling_revives',
            'revives_message',
            'selling_losses',
            'losses_message',
            'service_list_description',
            'tutorial',
            'job_seeking',
            'job_message',
            'selling_company',
            'selling_company_asking_price',
            'selling_company_description',
            'selling_company_price_negotiable',
            'company_looking_to_hire',
            'company_looking_to_hire_message',]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.fields['tutorial'].label = "Show page tutorials"
        self.fields['service_list_description'].label = "Service list description"
        self.fields['job_seeking'].label = 'Looking for jobs'
        self.fields['selling_company_price_negotiable'].label = 'Price negotiable'
        self.fields['selling_company_asking_price'].label = 'Price in Millions'
        self.fields['selling_company_description'].label = 'Listing Description'
        self.fields['company_looking_to_hire'].label = 'Looking to Hire?'
        self.fields['company_looking_to_hire_message'].label = 'Who are you looking for?'
        self.helper.layout = Layout(
            ###3 Traders Tab ####
            HTML(f"""
                <div class="tab-pane fade show active" id="traders" role="tabpanel" aria-labelledby="traders-tab">
                <p>Trading-related settings (price list description, trade message, forum thread link, sets)
                have moved to Manage My Price List.</p>
                <a class="btn btn-primary" href="{reverse('manage_price_list')}">
                    <i class="fa-solid fa-list"></i> Go to Manage My Price List
                </a>
                </div>
                """),
            #### Job Seeking Tab ####
            HTML("""
                <div class="tab-pane fade " id="jobseekers" role="tabpanel" aria-labelledby="jobseekers-tab">"""),
            HTML("<p class=' small'>NOTE: It will take a couple of minutes for your workstats to be displayed on your ad.</p><br />"),
            Field('job_seeking'),
            Field('job_message',
                  placeholder='Looking for 3* AN send me your offers'),
            HTML("</div>"),
            #### Services Tab ####
            HTML("""
                <div class="tab-pane fade" id="services" role="tabpanel" aria-labelledby="services-tab">"""),
            Field("service_list_description",
                  placeholder="Welcome. These are the services that I provide. Click on profile button and chat me up."),
            HTML("</div>"),
            #### Selling Revives Tab ####
            HTML("""
                <div class="tab-pane fade" id="revivers" role="tabpanel" aria-labelledby="revivers-tab">"""),
            Field('selling_revives'), Field('revives_message',
                                            placeholder='Reviving for $1m or 1 Xanax.'),
            HTML("</div>"),
            #### Selling Losses Tab ####
            HTML("""
                <div class="tab-pane fade" id="losses" role="tabpanel" aria-labelledby="losses-tab">"""),
            Field('selling_losses'), Field('losses_message',
                                           placeholder='Selling losses 300k each.'),
            HTML("</div>"),
            #### Selling Company Tab ####
            HTML("""
                <div class="tab-pane fade" id="selling_company" role="tabpanel" aria-labelledby="selling_company-tab">"""),
            Field('selling_company'), Field('selling_company_price_negotiable', label='Price negotiable?'), Field(
                PrependedAppendedText('selling_company_asking_price', '$', 'M')), Field('selling_company_description'),
            HTML("</div>"),
            #### Company Looking to Hire Tab ####
            HTML("""
                <div class="tab-pane fade" id="company_hiring" role="tabpanel" aria-labelledby="company_hiring-tab">"""),
            Field('company_looking_to_hire'), Field(
                    'company_looking_to_hire_message'),
            HTML("</div>"),
            HTML("""
                <div class="tab-pane fade " id="general" role="tabpanel" aria-labelledby="general-tab">"""),
            Field('tutorial'),
            HTML("</div><br />"),
            ButtonHolder(
                    Submit('submit', 'Submit', css_class='btn btn-primary')
            )
        )
