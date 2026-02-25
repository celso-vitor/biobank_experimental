from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html

# Novas importações para Import/Export em Massa (Planilhas)
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from core.models import (
    Biobank,
    Collection,
    Sample,
    SampleFile,
    Event,
    CollectionUserRole,
    Tag,
    Keyword,
    KeywordValue,
)

# ============================================================
# RESOURCES (REGRAS PARA IMPORTAÇÃO/EXPORTAÇÃO DE PLANILHAS)
# ============================================================
class BiobankResource(resources.ModelResource):
    class Meta:
        model = Biobank
        # Campos que o usuário verá no Excel
        fields = ('id', 'name', 'description', 'location_label', 'visibility', 'is_active', 'owner__username')
        export_order = fields

class CollectionResource(resources.ModelResource):
    class Meta:
        model = Collection
        fields = ('id', 'name', 'description', 'biobank__name', 'owners_display')
        export_order = fields

class SampleResource(resources.ModelResource):
    class Meta:
        model = Sample
        # Ajuste esta lista com os campos exatos que existem no seu modelo Sample
        fields = (
            'id', 'sample_id', 'sample_type', 'organism_name', 'status', 
            'visibility', 'collection__name', 'biobank__name', 'owner__username', 
            'scientific_notes', 'created_at'
        )
        export_order = fields

# ============================================================
# TAGS & KEYWORDS
# ============================================================
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(KeywordValue)
class KeywordValueAdmin(admin.ModelAdmin):
    list_display = ("keyword", "value", "biobanks_list", "collections_list", "samples_list")
    list_filter = ("keyword",)
    search_fields = ("keyword__name", "value")
    ordering = ("keyword__name", "value")

    def biobanks_list(self, obj):
        return ", ".join(b.name for b in obj.biobanks.all())
    biobanks_list.short_description = "Biobanks"

    def collections_list(self, obj):
        return ", ".join(c.name for c in obj.collections.all())
    collections_list.short_description = "Collections"

    def samples_list(self, obj):
        return ", ".join(s.sample_id for s in obj.samples.all())
    samples_list.short_description = "Samples"

# ============================================================
# INLINES
# ============================================================
class SampleFileInline(admin.TabularInline):
    model = SampleFile
    extra = 0
    readonly_fields = ("uploaded_at", "mime_type", "file_size")

class CollectionUserRoleInline(admin.TabularInline):
    model = CollectionUserRole
    extra = 0

# ============================================================
# BIOBANK (AGORA COM SUPORTE A PLANILHAS)
# ============================================================
@admin.register(Biobank)
class BiobankAdmin(ImportExportModelAdmin): # <-- Trocado
    resource_classes = [BiobankResource]    # <-- Nova configuração
    
    list_display = ("name", "location_label", "visibility", "is_active")
    search_fields = ("name", "location_label")
    list_filter = ("visibility", "is_active")
    ordering = ("name",)
    filter_horizontal = ("tags", "keywords")
    readonly_fields = ("latitude", "longitude")

# ============================================================
# COLLECTION (AGORA COM SUPORTE A PLANILHAS)
# ============================================================
@admin.register(Collection)
class CollectionAdmin(ImportExportModelAdmin): # <-- Trocado
    resource_classes = [CollectionResource]    # <-- Nova configuração
    
    list_display = ("name", "biobank", "owners_display")
    search_fields = ("name", "description")
    list_filter = ("biobank",)
    inlines = [CollectionUserRoleInline]
    filter_horizontal = ("tags", "keywords")

# ============================================================
# SAMPLE (DASHBOARD COM PLANILHAS MANTENDO SUA LÓGICA)
# ============================================================
@admin.register(Sample)
class SampleAdmin(ImportExportModelAdmin):     # <-- Trocado
    resource_classes = [SampleResource]        # <-- Nova configuração

    list_display = (
        "sample_id", "show_status_color", "visibility", "owner", 
        "sample_type", "organism_name", "collection", "created_at",
    )
    list_filter = ("status", "visibility", "collection", "biobank", "is_active", "created_at")
    search_fields = ("sample_id", "organism_name", "sample_type", "uuid", "owner__username", "scientific_notes")
    ordering = ("-created_at",)
    date_hierarchy = 'created_at'
    list_per_page = 20

    inlines = [SampleFileInline]
    filter_horizontal = ("tags", "keywords")
    readonly_fields = ("uuid", "created_at", "updated_at")

    @admin.display(description='Status')
    def show_status_color(self, obj):
        colors = {
            'available': 'green', 'pending': 'orange', 'qc': 'blue',
            'rejected': 'red', 'depleted': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(owner=request.user) | Q(visibility='public') | Q(visibility='biobank') | Q(visibility='group')
        ).distinct()

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if obj and obj.owner == request.user: return True
        return False

# ============================================================
# OUTROS
# ============================================================
@admin.register(SampleFile)
class SampleFileAdmin(admin.ModelAdmin):
    list_display = ("file", "sample", "category", "mime_type", "uploaded_at")
    list_filter = ("category", "uploaded_at")
    search_fields = ("file", "description")

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("sample", "event_type", "location_snapshot", "timestamp")
    list_filter = ("event_type", "timestamp")
    search_fields = ("sample__sample_id", "notes", "location_snapshot")
    readonly_fields = ("timestamp",)
