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
    # === NOVOS MODELOS BIOLÓGICOS ===
    Bacteria,
    Phage,
    HostRange,
    Vector,
    Construction
)

# ============================================================
# RESOURCES (REGRAS PARA IMPORTAÇÃO/EXPORTAÇÃO DE PLANILHAS)
# ============================================================
class BiobankResource(resources.ModelResource):
    class Meta:
        model = Biobank
        fields = ('id', 'name', 'description', 'location_label', 'is_public', 'is_active', 'owner__username')
        export_order = fields

class CollectionResource(resources.ModelResource):
    class Meta:
        model = Collection
        fields = ('id', 'name', 'description', 'biobank__name')
        export_order = fields

class SampleResource(resources.ModelResource):
    class Meta:
        model = Sample
        # ATUALIZADO: removido collection__name temporariamente, 
        # pois exportar ManyToMany diretamente para CSV requer lógica extra (dehydrate).
        fields = (
            'id', 'sample_id', 'sample_type', 'organism_name', 'status', 
            'is_public', 'biobank__name', 'owner__username', 
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
    # ATUALIZADO: os métodos dinâmicos foram movidos para dentro da classe corretamente
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

# ============================================================
# BIOBANK 
# ============================================================
@admin.register(Biobank)
class BiobankAdmin(ImportExportModelAdmin): 
    resource_classes = [BiobankResource]    
    
    list_display = ("name", "location_label", "is_public", "is_active")
    search_fields = ("name", "location_label")
    list_filter = ("is_public", "is_active")
    ordering = ("name",)
    filter_horizontal = ("tags", "keywords")
    readonly_fields = ("latitude", "longitude")

# ============================================================
# COLLECTION 
# ============================================================
@admin.register(Collection)
class CollectionAdmin(ImportExportModelAdmin): 
    resource_classes = [CollectionResource]    
    
    list_display = ("name", "biobank")
    search_fields = ("name", "description")
    list_filter = ("biobank",)
    filter_horizontal = ("tags", "keywords")

# ============================================================
# SAMPLE (CLASSE BASE)
# ============================================================
@admin.register(Sample)
class SampleAdmin(ImportExportModelAdmin):     
    resource_classes = [SampleResource]        

    # ATUALIZADO: 'collection' removido do list_display (Django não aceita M2M aqui) e criado método 'get_collections'
    list_display = (
        "sample_id", "show_status_color", "is_public", "owner", 
        "sample_type", "organism_name", "get_collections", "created_at",
    )
    # ATUALIZADO: list_filter atualizado para 'collections'
    list_filter = ("status", "is_public", "collections", "biobank", "is_active", "created_at")
    search_fields = ("sample_id", "organism_name", "sample_type", "uuid", "owner__username", "scientific_notes")
    ordering = ("-created_at",)
    date_hierarchy = 'created_at'
    list_per_page = 20

    inlines = [SampleFileInline]
    # ATUALIZADO: Adicionado 'collections' ao filter_horizontal para facilitar a seleção múltipla
    filter_horizontal = ("collections", "tags", "keywords")
    readonly_fields = ("uuid", "created_at", "updated_at")

    @admin.display(description='Coleções')
    def get_collections(self, obj):
        # Cria uma string com o nome de todas as coleções às quais a amostra pertence
        return ", ".join([c.name for c in obj.collections.all()])

    @admin.display(description='Status')
    def show_status_color(self, obj):
        colors = {
            'available': 'green', 'pending': 'orange', 'qc': 'blue',
            'rejected': 'red', 'depleted': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())

    def get_queryset(self, request):
        # ATUALIZADO: prefetch_related adicionado para otimizar a listagem no banco (evita N+1 queries)
        qs = super().get_queryset(request).prefetch_related('collections')
        if request.user.is_superuser:
            return qs
        return qs.filter(
            Q(owner=request.user) | Q(is_public=True)
        ).distinct()

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser: return True
        if obj and obj.owner == request.user: return True
        return False

# ============================================================
# === NOVAS CLASSES BIOLÓGICAS (HERANÇA DE SAMPLE) ===
# ============================================================

@admin.register(Bacteria)
class BacteriaAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "species", "strain", "owner", "is_public")
    search_fields = ("sample_id", "species", "strain")
    list_filter = ("is_public", "status")
    filter_horizontal = ("collections", "tags", "keywords")

@admin.register(Phage)
class PhageAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "taxonomy", "morphotype", "lifestyle", "owner")
    search_fields = ("sample_id", "taxonomy", "morphotype")
    list_filter = ("morphotype", "lifestyle", "genome_type")
    filter_horizontal = ("collections", "tags", "keywords")

@admin.register(HostRange)
class HostRangeAdmin(admin.ModelAdmin):
    list_display = ("phage", "bacteria", "is_isolation_host", "efficiency_eop")
    list_filter = ("is_isolation_host",)
    search_fields = ("phage__sample_id", "bacteria__sample_id", "phage__taxonomy", "bacteria__species")

@admin.register(Vector)
class VectorAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "name_official", "vector_type", "vector_size_bp", "owner")
    search_fields = ("sample_id", "name_official", "vector_type")
    list_filter = ("vector_type",)
    filter_horizontal = ("collections", "tags", "keywords")

@admin.register(Construction)
class ConstructionAdmin(admin.ModelAdmin):
    list_display = ("sample_id", "construction_name", "parent_vector", "host_strain", "final_size_bp")
    search_fields = ("sample_id", "construction_name", "insert_name")
    filter_horizontal = ("collections", "tags", "keywords")

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
