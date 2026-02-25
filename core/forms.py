# core/forms.py
from django import forms
from core.models import Biobank, Collection, Tag

# ----------------------------------------------------------
# BIOBANK FORM
# ----------------------------------------------------------
class BiobankForm(forms.ModelForm):
    class Meta:
        model = Biobank
        # Removido "institution" da lista de campos
        fields = [
            "name",
            "visibility",
            "location_label",
            "latitude",
            "longitude",
            "description", 
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "visibility": forms.Select(attrs={"class": "form-select"}),
            
            # Campo de endereço que agora aparece para busca dinâmica
            "location_label": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex: Universidade de São Paulo, USP",
                "autocomplete": "off"
            }),
            
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "description": forms.Textarea(attrs={ 
                "class": "form-control",
                "rows": 4,
                "placeholder": "Relevant description about this Biobank"
            }),
        }


# ----------------------------------------------------------
# COLLECTION FORM
# ----------------------------------------------------------
class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "biobank", "description", "visibility"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Collection name"
            }),
            "biobank": forms.Select(attrs={
                "class": "form-select"
            }),
            "visibility": forms.Select(attrs={
                "class": "form-select"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe the collection"
            }),
        }

# ----------------------------------------------------------
# TAG FORM
# ----------------------------------------------------------
class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

# ----------------------------------------------------------
# SAMPLE FORM (PARA EDIÇÃO)
# ----------------------------------------------------------
from core.models import Sample

class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = [
            "sample_id", "sample_type", "organism_name", 
            "status", "visibility", "storage_location",
            "biobank", "collection", "scientific_notes"
        ]
        widgets = {
            "sample_id": forms.TextInput(attrs={"class": "form-control"}),
            "sample_type": forms.TextInput(attrs={"class": "form-control"}),
            "organism_name": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "visibility": forms.Select(attrs={"class": "form-select"}),
            "storage_location": forms.TextInput(attrs={"class": "form-control"}),
            "biobank": forms.Select(attrs={"class": "form-select"}),
            "collection": forms.Select(attrs={"class": "form-select"}),
            "scientific_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
