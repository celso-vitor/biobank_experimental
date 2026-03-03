from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html

from import_export import resources
from import_export.admin import ImportExportModelAdmin

from core.models import (
    Biobank,
    Collection,
    Sample,
    SampleFile,
    Event,
    Tag,
    Keyword,
    KeywordValue,
    # Modelos biológicos atualizados
    Bacteria,
    Phage,
    HostRange,
    Vector,
    Construction
)

# ============================================================
# RESOURCES (PARA IMPORTAÇÃO/EXPORTAÇÃO)
# ============================================================
class SampleResource(resources.ModelResource):
    class Meta:
        model = Sample
        fields = ('id', 'sample_id', 'sample_type', 'organism_name', 'status', 'owner__username', 'created_at')

# ============================================================
# INLINES
# ============================================================
class SampleFileInline(admin.TabularInline):
    model = SampleFile
    extra = 0
    readonly_fields = ("uploaded_at", "mime_type", "file_size")

# ============================================================
# ADMIN CLASSES
# ============================================================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(Biobank)
class BiobankAdmin(admin.ModelAdmin):
    list_display = ("name", "location_label", "is_public", "is_active")
    filter_horizontal = ("tags", "keywords")

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_public")
    filter_horizontal = ("tags", "keywords")

@admin.register(Sample)
class SampleAdmin(ImportExportModelAdmin):
    resource_classes = [SampleResource]
    list_display = ("sample_id", "sample_type", "organism_name", "status", "owner", "created_at")
    list_filter = ("status", "sample_type", "is_public")
    search_fields = ("sample_id", "organism_name")
    inlines = [SampleFileInline]
    filter_horizontal = ("collections", "tags", "keywords")

# --- ADMINISTRAÇÃO DOS SUBTIPOS BIOLÓGICOS ---

@admin.register(Bacteria)
class BacteriaAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "species", "strain", "owner")
    search_fields = ("sample_id", "species", "strain")
    filter_horizontal = ("collections", "tags", "keywords")

@admin.register(Phage)
class PhageAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "taxonomy", "morphotype", "lifestyle")
    list_filter = ("morphotype", "lifestyle")
    filter_horizontal = ("collections", "tags", "keywords")

@admin.register(HostRange)
class HostRangeAdmin(admin.ModelAdmin):
    list_display = ("phage", "bacteria", "is_isolation_host", "efficiency_eop")
    list_filter = ("is_isolation_host",)

@admin.register(Vector)
class VectorAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "name_official", "vector_type", "vector_size_bp")
    search_fields = ("sample_id", "name_official")
    filter_horizontal = ("collections", "tags", "keywords")

@admin.register(Construction)
class ConstructionAdmin(admin.ModelAdmin):
    # host_strain removido para evitar erro de campo inexistente
    list_display = ("sample_id", "construction_name", "parent_vector", "final_size_bp", "owner")
    search_fields = ("sample_id", "construction_name", "insert_name")
    readonly_fields = ("final_size_bp",) # Campo calculado no save() do model
    filter_horizontal = ("collections", "tags", "keywords")

@admin.register(SampleFile)
class SampleFileAdmin(admin.ModelAdmin):
    list_display = ("file", "sample", "category", "uploaded_at")

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("sample", "event_type", "timestamp", "performed_by")
    readonly_fields = ("timestamp",)
