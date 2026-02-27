# core/forms.py
from django import forms
from core.models import Biobank, Collection, Tag, Sample
# IMPORTS DOS NOVOS MODELOS BIOLÓGICOS
from core.models import Bacteria, Phage, Vector, Construction

# ----------------------------------------------------------
# BIOBANK, COLLECTION & TAG FORMS (Mantidos originais)
# ----------------------------------------------------------
class BiobankForm(forms.ModelForm):
    class Meta:
        model = Biobank
        fields = ["name", "is_public", "location_label", "latitude", "longitude", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "location_label": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Ex: Universidade de São Paulo, USP", "autocomplete": "off"
            }),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "biobank", "description", "is_public"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Collection name"}),
            "biobank": forms.Select(attrs={"class": "form-select"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

# ----------------------------------------------------------
# 1. SAMPLE FORM (O Formulário Pai)
# ----------------------------------------------------------
class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = [
            "sample_id", "sample_type", "organism_name", 
            "status", "is_public", "storage_location",
            "biobank", "collection", "scientific_notes"
        ]
        widgets = {
            "sample_id": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}), # Protegido na edição
            "sample_type": forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"}), # Protegido na edição
            "organism_name": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "is_public": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "storage_location": forms.TextInput(attrs={"class": "form-control"}),
            "biobank": forms.Select(attrs={"class": "form-select"}),
            "collection": forms.Select(attrs={"class": "form-select"}),
            "scientific_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

# ----------------------------------------------------------
# 2. FORMULÁRIOS ESPECÍFICOS (Filhos)
# ----------------------------------------------------------
class BacteriaForm(SampleForm):
    # Campo extra para transformar o array JSON em texto separado por vírgulas para o utilizador
    resistance_markers_text = forms.CharField(
        required=False, label="Marcadores de Resistência", 
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Ap100, Km50"})
    )

    class Meta(SampleForm.Meta):
        model = Bacteria
        fields = SampleForm.Meta.fields + ["species", "strain", "genotype"]
        widgets = {
            **SampleForm.Meta.widgets,
            "species": forms.TextInput(attrs={"class": "form-control"}),
            "strain": forms.TextInput(attrs={"class": "form-control"}),
            "genotype": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            markers = self.instance.resistance_markers
            if isinstance(markers, list):
                self.initial['resistance_markers_text'] = ", ".join(markers)

    def save(self, commit=True):
        instance = super().save(commit=False)
        markers_text = self.cleaned_data.get('resistance_markers_text', '')
        instance.resistance_markers = [m.strip() for m in markers_text.split(',') if m.strip()]
        if commit: instance.save()
        return instance

class PhageForm(SampleForm):
    class Meta(SampleForm.Meta):
        model = Phage
        fields = SampleForm.Meta.fields + ["morphotype", "taxonomy", "lifestyle", "isolation_source", "genome_type", "genome_size_bp", "temp_C", "ncbi_accession"]
        widgets = {
            **SampleForm.Meta.widgets,
            "morphotype": forms.Select(attrs={"class": "form-select"}),
            "taxonomy": forms.TextInput(attrs={"class": "form-control"}),
            "lifestyle": forms.Select(attrs={"class": "form-select"}),
            "isolation_source": forms.TextInput(attrs={"class": "form-control"}),
            "genome_type": forms.Select(attrs={"class": "form-select"}),
            "genome_size_bp": forms.NumberInput(attrs={"class": "form-control"}),
            "temp_C": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "ncbi_accession": forms.TextInput(attrs={"class": "form-control"}),
        }

class VectorForm(SampleForm):
    resistance_markers_text = forms.CharField(
        required=False, label="Marcadores de Resistência", 
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Ap100, Km50"})
    )

    class Meta(SampleForm.Meta):
        model = Vector
        fields = SampleForm.Meta.fields + ["name_official", "vector_type", "induction_system", "vector_size_bp"]
        widgets = {
            **SampleForm.Meta.widgets,
            "name_official": forms.TextInput(attrs={"class": "form-control"}),
            "vector_type": forms.Select(attrs={"class": "form-select"}),
            "induction_system": forms.TextInput(attrs={"class": "form-control"}),
            "vector_size_bp": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            markers = self.instance.resistance_markers
            if isinstance(markers, list):
                self.initial['resistance_markers_text'] = ", ".join(markers)

    def save(self, commit=True):
        instance = super().save(commit=False)
        markers_text = self.cleaned_data.get('resistance_markers_text', '')
        instance.resistance_markers = [m.strip() for m in markers_text.split(',') if m.strip()]
        if commit: instance.save()
        return instance

class ConstructionForm(SampleForm):
    class Meta(SampleForm.Meta):
        model = Construction
        fields = SampleForm.Meta.fields + ["parent_vector", "construction_name", "insert_name", "insert_size_bp"]
        widgets = {
            **SampleForm.Meta.widgets,
            "parent_vector": forms.Select(attrs={"class": "form-select"}),
            "construction_name": forms.TextInput(attrs={"class": "form-control"}),
            "insert_name": forms.TextInput(attrs={"class": "form-control"}),
            "insert_size_bp": forms.NumberInput(attrs={"class": "form-control"}),
        }

# ==========================================================
# FUNÇÃO DETETIVE: Descobre qual formulário usar
# ==========================================================
def get_form_class_for_sample(sample_instance):
    if hasattr(sample_instance, 'bacteria'): return BacteriaForm
    if hasattr(sample_instance, 'phage'): return PhageForm
    if hasattr(sample_instance, 'vector'): return VectorForm
    if hasattr(sample_instance, 'construction'): return ConstructionForm
    return SampleForm
