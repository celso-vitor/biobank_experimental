from django.db import models
from django.core.validators import MinValueValidator
from .sample import Sample

# =========================================================
# 1. BACTERIA (Hosts)
# =========================================================
class Bacteria(Sample):
    genus = models.CharField(max_length=100, blank=True, null=True, help_text="Genus. Ex: Escherichia")
    species = models.CharField(max_length=150, help_text="Scientific name. Ex: Escherichia coli")
    strain = models.CharField(max_length=100, blank=True, null=True, help_text="Strain (Ex: BL21, MG1655)")
    genotype = models.TextField(blank=True, null=True, help_text="Genetic markers")
    resistance_markers = models.JSONField(default=list, blank=True, help_text="List of antibiotic resistance markers")
    additional_info = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Bacteria"
        verbose_name_plural = "Bacteria"

# =========================================================
# 2. PHAGES (Viruses)
# =========================================================
class Phage(Sample):
    MORPHOTYPE_CHOICES = [
        ('myovirus', 'Myovirus'),
        ('siphovirus', 'Siphovirus'),
        ('podovirus', 'Podovirus'),
        ('other', 'Other'),
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

    genus = models.CharField(max_length=100, blank=True, null=True, help_text="Genus. Ex: Tequatrovirus")
    morphotype = models.CharField(max_length=50, choices=MORPHOTYPE_CHOICES, blank=True, null=True)
    taxonomy = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: Autographiviridae, Straboviridae")
    lifestyle = models.CharField(max_length=50, choices=LIFESTYLE_CHOICES, blank=True, null=True)
    isolation_source = models.CharField(max_length=255, blank=True, null=True, help_text="Ex: Sewage, soil, clinical sample")
    genome_type = models.CharField(max_length=20, choices=GENOME_CHOICES, blank=True, null=True)
    genome_size_bp = models.PositiveIntegerField(blank=True, null=True, help_text="Size in base pairs (bp)")
    ncbi_accession = models.CharField(max_length=100, blank=True, null=True, help_text="GenBank Link/ID")
    temp_C = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="Optimal growth temperature")

    class Meta:
        verbose_name = "Phage"

# =========================================================
# 3. HOST RANGE (The Junction Table / Graph)
# =========================================================
class HostRange(models.Model):
    phage = models.ForeignKey(Phage, on_delete=models.CASCADE, related_name='host_interactions')
    bacteria = models.ForeignKey(Bacteria, on_delete=models.CASCADE, related_name='phage_interactions')
    is_isolation_host = models.BooleanField(default=False, help_text="Defines if this is the isolation host bacteria")
    efficiency_eop = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0.0)])
    plaque_morphology = models.ImageField(upload_to='plaque_images/', blank=True, null=True)

    class Meta:
        unique_together = ('phage', 'bacteria')
        verbose_name = "Host Range Interaction"

# =========================================================
# 4. VECTOR BACKBONES (Empty Vectors)
# =========================================================
class VectorBackbone(Sample):
    VECTOR_TYPE_CHOICES = [
        ('expression', 'Expression'),
        ('suicide', 'Suicide'),
        ('conjugation', 'Conjugation'),
        ('cloning', 'Cloning'),
    ]

    name_official = models.CharField(max_length=100, help_text="Ex: pET28a(+)")
    aliases = models.TextField(blank=True, null=True, help_text="Alternative names or aliases")
    vector_type = models.CharField(max_length=50, choices=VECTOR_TYPE_CHOICES, blank=True, null=True)
    resistance_markers = models.JSONField(default=list, blank=True)
    induction_system = models.CharField(max_length=100, blank=True, null=True, help_text="Ex: T7, lac, araBAD")
    vector_size_bp = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Vector Backbone"

# =========================================================
# 5. INSERTS (Genes/Parts)
# =========================================================
class Insert(Sample):
    insert_name = models.CharField(max_length=100, help_text="Name of the inserted gene/part. Ex: eGFP")
    insert_size_bp = models.PositiveIntegerField(default=0)
    sequence = models.TextField(blank=True, null=True, help_text="FASTA or raw sequence")

    class Meta:
        verbose_name = "Insert"

# =========================================================
# 6. PLASMIDS (Backbone + Insert Assembly)
# =========================================================
class Plasmid(Sample):
    backbone = models.ForeignKey(VectorBackbone, on_delete=models.PROTECT, related_name='plasmids')
    
    # ATUALIZADO AQUI para evitar colisão E006
    insert_part = models.ForeignKey(Insert, on_delete=models.SET_NULL, null=True, blank=True, related_name='plasmids')
    
    construction_name = models.CharField(max_length=150, blank=True, null=True, help_text="Ex: pET28a-GFP. Leave empty to auto-fill with Backbone name if no insert.")
    actual_resistances = models.JSONField(default=list, blank=True, help_text="Resistances of the final construction")
    origin_lab = models.CharField(max_length=150, blank=True, null=True)
    
    final_size_bp = models.PositiveIntegerField(blank=True, null=True, help_text="Calculated automatically")

    def save(self, *args, **kwargs):
        v_size = self.backbone.vector_size_bp if self.backbone and self.backbone.vector_size_bp else 0
        i_size = self.insert_part.insert_size_bp if self.insert_part and self.insert_part.insert_size_bp else 0
        self.final_size_bp = v_size + i_size

        if not self.insert_part and not self.construction_name and self.backbone:
            self.construction_name = self.backbone.name_official

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Plasmid (Backbone + Insert)"
