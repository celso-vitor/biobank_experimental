import os
import shutil
import mimetypes
from django.db import models
from django.utils.text import slugify
from django.conf import settings

# Import relativo dentro do mesmo pacote (samples)
from .sample import Sample

def sample_file_upload_to(instance, filename):
    sample = instance.sample
    if not sample.collection or not sample.biobank:
        path = os.path.join("_unassigned_samples", slugify(sample.sample_id))
    else:
        path = os.path.join(slugify(sample.biobank.name), slugify(sample.collection.name), slugify(sample.sample_id))
    return os.path.join(path, filename)

class SampleFile(models.Model):
    # Categorias para o visualizador no Frontend
    VIEW_CATEGORIES = [
        ('image', 'Imagem (Microscopia/Gel)'),
        ('table', 'Tabela (CSV/Excel)'),
        ('sequence', 'Sequência (FASTA/FASTQ)'),
        ('pdf', 'Documento PDF'),
        ('raw', 'Dados Brutos / Outros'),
    ]

    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name="files",
    )

    file = models.FileField(upload_to=sample_file_upload_to)
    description = models.TextField(blank=True, null=True)
    
    # Metadados para o Visualizador
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=VIEW_CATEGORIES, default='raw')
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-detecta metadados antes de salvar
        if self.file:
            self.file_size = self.file.size
            guess, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = guess
            
            ext = os.path.splitext(self.file.name)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                self.category = 'image'
            elif ext in ['.csv', '.xlsx', '.xls']:
                self.category = 'table'
            elif ext in ['.fasta', '.fastq', '.gb']:
                self.category = 'sequence'
            elif ext == '.pdf':
                self.category = 'pdf'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"File for {self.sample.sample_id} ({self.category})"

def move_sample_files(sample):
    """Lógica de movimentação física de arquivos ao associar coleção"""
    if not sample.collection or not sample.biobank:
        return

    old_base_rel = os.path.join("_unassigned_samples", slugify(sample.sample_id))
    old_base_abs = os.path.join(settings.MEDIA_ROOT, old_base_rel)

    if not os.path.exists(old_base_abs):
        return

    new_base_rel = os.path.join(
        slugify(sample.biobank.name),
        slugify(sample.collection.name),
        slugify(sample.sample_id),
    )
    new_base_abs = os.path.join(settings.MEDIA_ROOT, new_base_rel)

    os.makedirs(new_base_abs, exist_ok=True)
    for filename in os.listdir(old_base_abs):
        old_file_path = os.path.join(old_base_abs, filename)
        new_file_path = os.path.join(new_base_abs, filename)
        shutil.move(old_file_path, new_file_path)

    if not os.listdir(old_base_abs):
        os.rmdir(old_base_abs)

    # CORREÇÃO: Atualizar o caminho dos arquivos no banco de dados
    for sample_file in sample.files.all():
        if str(sample_file.file.name).startswith(old_base_rel):
            filename = os.path.basename(sample_file.file.name)
            sample_file.file.name = os.path.join(new_base_rel, filename)
            # update_fields evita acionar o super().save() inteiro sem necessidade
            sample_file.save(update_fields=['file'])
