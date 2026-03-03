from django.db import models
from django.core.validators import MinValueValidator
from .sample import Sample

# =========================================================
# 1. BACTÉRIAS (Hospedeiros)
# =========================================================
class Bacteria(Sample):
    species = models.CharField(max_length=150, help_text="Nome científico. Ex: Escherichia coli")
    strain = models.CharField(max_length=100, blank=True, null=True, help_text="Linhagem (Ex: BL21, MG1655)")
    genotype = models.TextField(blank=True, null=True, help_text="Marcadores genéticos")
    resistance_markers = models.JSONField(default=list, blank=True, help_text="Lista de antibióticos de resistência")
    additional_info = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Bacteria"
        verbose_name_plural = "Bacteria"

# =========================================================
# 2. FAGOS (Vírus)
# =========================================================
class Phage(Sample):
    MORPHOTYPE_CHOICES = [
        ('myovirus', 'Myovirus'),
        ('siphovirus', 'Siphovirus'),
        ('podovirus', 'Podovirus'),
        ('outros', 'Outros'),
    ]
    LIFESTYLE_CHOICES = [
        ('lytic', 'Lytic'),
        ('lysogenic', 'Lysogenic'),
    ]
    GENOME_CHOICES = [
        ('dsDNA', 'dsDNA'),
        ('ssDNA', 'ssDNA'),
        ('dsRNA', 'dsRNA'),
        ('ssRNA', 'ssRNA'),
    ]

    morphotype = models.CharField(max_length=50, choices=MORPHOTYPE_CHOICES, blank=True, null=True)
    taxonomy = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: Autographiviridae, Straboviridae")
    lifestyle = models.CharField(max_length=50, choices=LIFESTYLE_CHOICES, blank=True, null=True)
    isolation_source = models.CharField(max_length=255, blank=True, null=True, help_text="Ex: Esgoto, solo, amostra clínica")
    genome_type = models.CharField(max_length=20, choices=GENOME_CHOICES, blank=True, null=True)
    genome_size_bp = models.PositiveIntegerField(blank=True, null=True, help_text="Tamanho em pares de bases")
    ncbi_accession = models.CharField(max_length=100, blank=True, null=True, help_text="Link/ID do GenBank")
    temp_C = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="Temperatura ideal de crescimento")

    # Arquivos movidos para o sistema genérico SampleFile!

    class Meta:
        verbose_name = "Phage"

# =========================================================
# 3. HOST RANGE (A Tabela de Junção / Grafo)
# =========================================================
class HostRange(models.Model):
    phage = models.ForeignKey(Phage, on_delete=models.CASCADE, related_name='host_interactions')
    bacteria = models.ForeignKey(Bacteria, on_delete=models.CASCADE, related_name='phage_interactions')
    is_isolation_host = models.BooleanField(default=False, help_text="Define se esta é a bactéria mãe do isolamento")
    efficiency_eop = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0.0)])
    
    # Faz sentido manter aqui, pois a imagem da placa pertence à *interação* e não apenas ao fago!
    plaque_morphology = models.ImageField(upload_to='plaque_images/', blank=True, null=True)

    class Meta:
        unique_together = ('phage', 'bacteria')
        verbose_name = "Host Range Interaction"

# =========================================================
# 4. VETORES (Backbones / Catálogo)
# =========================================================
class Vector(Sample):
    VECTOR_TYPE_CHOICES = [
        ('expression', 'Expression'),
        ('suicide', 'Suicide'),
        ('conjugation', 'Conjugation'),
        ('cloning', 'Cloning'),
    ]

    name_official = models.CharField(max_length=100, help_text="Ex: pET28a(+)")
    aliases = models.TextField(blank=True, null=True, help_text="Nomes alternativos ou apelidos")
    vector_type = models.CharField(max_length=50, choices=VECTOR_TYPE_CHOICES, blank=True, null=True)
    resistance_markers = models.JSONField(default=list, blank=True)
    induction_system = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: T7, lac, araBAD")
    vector_size_bp = models.PositiveIntegerField(blank=True, null=True)

    # Relação default_host movida para a rede de Rastreabilidade (SampleRelationship)

    class Meta:
        verbose_name = "Vector"

# =========================================================
# 5. CONSTRUÇÕES
# =========================================================
class Construction(Sample):
    parent_vector = models.ForeignKey(Vector, on_delete=models.PROTECT, related_name='constructions')
    construction_name = models.CharField(max_length=150, help_text="Ex: pET28a-GFP")
    insert_name = models.CharField(max_length=100, blank=True, null=True, help_text="Nome do gene/peça inserida. Ex: eGFP")
    insert_size_bp = models.PositiveIntegerField(default=0)
    actual_resistances = models.JSONField(default=list, blank=True, help_text="Resistências da construção final")
    origin_lab = models.CharField(max_length=150, blank=True, null=True)
    
    # Campo físico para permitir filtros rápidos no banco de dados (Ex: order by tamanho)
    final_size_bp = models.PositiveIntegerField(blank=True, null=True, help_text="Calculado automaticamente")

    def save(self, *args, **kwargs):
        v_size = self.parent_vector.vector_size_bp if self.parent_vector and self.parent_vector.vector_size_bp else 0
        i_size = self.insert_size_bp if self.insert_size_bp else 0
        self.final_size_bp = v_size + i_size
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Construction"
