from django import forms
from .models import Settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, Field, HTML
from crispy_forms.bootstrap import PrependedText, PrependedAppendedText


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
            'trade_list_description',
            'trade_enable_sets',
            'service_list_description',
            'link_to_forum_post',
            'receipt_paste_text',
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
        self.fields['receipt_paste_text'].label = "Receipt Paste Text"
        self.fields['tutorial'].label = "Show page tutorials"
        self.fields['trade_list_description'].label = "Price list description"
        self.fields['trade_enable_sets'].label = "Enable Plushies and Flowers sets"
        self.fields['service_list_description'].label = "Service list description"
        self.fields['job_seeking'].label = 'Looking for jobs'
        self.fields['selling_company_price_negotiable'].label = 'Price negotiable'
        self.fields['selling_company_asking_price'].label = 'Price in Millions'
        self.fields['selling_company_description'].label = 'Listing Description'
        self.fields['company_looking_to_hire'].label = 'Looking to Hire?'
        self.fields['company_looking_to_hire_message'].label = 'Who are you looking for?'
        self.helper.layout = Layout(
            ###3 Traders Tab ####
            HTML("""
                <div class="tab-pane fade show active" id="traders" role="tabpanel" aria-labelledby="traders-tab">
                """),
            Field("trade_list_description",
                  placeholder="Welcome to my price list. Click Start Trade now to start a trade. (Emojis are allowed 🤑) "),
            Field(PrependedText('link_to_forum_post',
                  'https//:www.torn.com/'), placeholder='To'),
            Field('trade_enable_sets'),
            Field('receipt_paste_text', placeholder='''Paste your receipt message here, you will be able to copy this to the clipboard later. 
You can use the following variables in your message:
[[seller_name]] - The name of the seller
[[total]] - The total price of the items you are buying
[[trade_number]] - The number of trades you have made with this seller.
[[receipt_link]] - The link to the receipt of the trade.
[[prices_link]] - The link to your price list.
[[forum_link]] - The link to your forum thread.

Example:
Hi [[seller_name]], thank you for the trade, the total is $[[total]], here is your receipt [[receipt_link]]. This is our trade N[[trade_number]]. Don't forget to rate my price list [[prices_link]]. Have a nice day!'''),
            HTML("""
                <div>
                Legend:</br>
<code>
[[seller_name]] - The name of the seller</br>
[[total]] - The total price of the items you are buying</br>
[[trade_number]] - The number of trades you have made with this seller.</br>
[[receipt_link]] - The link to the receipt of the trade.</br>
[[prices_link]] - The link to your price list.</br>
[[forum_link]] - The link to your forum thread.</br></br>
</code>
                </div>
                """),
            HTML("</div>"),
            #### Job Seeking Tab ####
            HTML("""
                <div class="tab-pane fade " id="jobseekers" role="tabpanel" aria-labelledby="jobseekers-tab">"""),
            HTML("<p class=' small text-muted'>NOTE: It will take a couple of minutes for your workstats to be displayed on your ad.</p>"),
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
            HTML("</div>"),
            ButtonHolder(
                    Submit('submit', 'Submit', css_class='btn btn-primary')
            )
        )
