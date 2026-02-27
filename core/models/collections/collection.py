from django.db import models
from django.contrib.auth.models import User

# Imports atualizados para a nova hierarquia de diretórios
from core.models.biobanks.biobank import Biobank
from core.models.tags import Tag
from core.models.keywords import KeywordValue

class Collection(models.Model):
    """
    Coleção científica pertencente a um Biobank.
    Controla acesso, visibilidade e governança de amostras.
    No contexto do CEPID B3, agrupa linhagens por projeto ou laboratório.
    """

    # =========================
    # METADADOS BÁSICOS
    # =========================
    name = models.CharField(max_length=200)
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="Finalidade científica da coleção"
    )

    biobank = models.ForeignKey(
        Biobank,
        on_delete=models.CASCADE,
        related_name="collections",
    )

    # =========================
    # GOVERNANÇA / PERMISSÕES
    # =========================
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_collections",
        help_text="Responsável científico/PI pela coleção",
    )

    # Novo formato simplificado
    is_public = models.BooleanField(
        default=False,
        help_text="Marque para disponibilizar esta coleção publicamente"
    )

    # =========================
    # CICLO DE VIDA E AUDITORIA
    # =========================
    is_active = models.BooleanField(
        default=True,
        help_text="Indica se a Collection está ativa para novos cadastros",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # =========================
    # CLASSIFICAÇÃO
    # =========================
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="collections",
    )

    keywords = models.ManyToManyField(
        KeywordValue,
        blank=True,
        related_name="collections",
    )

    # =========================
    # REPRESENTAÇÃO
    # =========================
    def __str__(self):
        return f"{self.name} ({self.biobank.name})"
