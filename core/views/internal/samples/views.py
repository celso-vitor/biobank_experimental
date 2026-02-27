import qrcode
import io
import base64
import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

from core.context import base_context
from core.models import (
    Sample,
    Collection,
    SampleFile,
    Biobank,
    Tag,
    Keyword,
    KeywordValue,
    # IMPORTS DOS NOVOS MODELOS BIOLÓGICOS
    Bacteria,
    Phage,
    Vector,
    Construction
)
from core.models.events.model import Event
# IMPORT ATUALIZADO: Agora importamos a função que deteta o tipo de formulário
from core.forms import SampleForm, get_form_class_for_sample
from core.permissions.samples import can_view_sample, can_edit_sample, can_delete_sample
from core.permissions.collections import can_edit_collection

# =========================================================
# 1. DASHBOARD (LISTAGEM & FILTROS)
# =========================================================
@login_required
def samples_list_view(request):
    user = request.user
    
    # Busca amostras ativas
    qs = Sample.objects.filter(is_active=True).select_related('collection', 'owner').order_by("-created_at")

    # Filtros de busca
    query = request.GET.get('q')
    if query:
        qs = qs.filter(
            Q(sample_id__icontains=query) |
            Q(organism_name__icontains=query) |
            Q(sample_type__icontains=query)
        )

    status_filter = request.GET.get('status')
    if status_filter and status_filter not in ['', 'Todos os Status']:
        qs = qs.filter(status=status_filter)

    collection_id = request.GET.get('collection')
    if collection_id and collection_id.isdigit():
        qs = qs.filter(collection_id=collection_id)

    ctx = base_context(request)
    ctx.update({
        'samples': qs,
        'filter_collections': Collection.objects.all(),
    })
    return render(request, "internal/samples/list.html", ctx)


# =========================================================
# 2. CREATE SAMPLE (COM ROTEAMENTO BIOLÓGICO)
# =========================================================
@login_required
def sample_create_view(request):
    user = request.user

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_sample":
            try:
                # 1. Captura de metadados globais base
                sample_id_base = request.POST.get("sample_id")
                sample_type = request.POST.get("sample_type")
                organism_name = request.POST.get("organism_name")
                scientific_notes = request.POST.get("scientific_notes") 
                storage_location = request.POST.get("storage_location", "")

                is_public = request.POST.get("is_public") == "true" or request.POST.get("is_public") == "on"
                
                collection_id = request.POST.get("collection_id")
                collection = Collection.objects.filter(id=collection_id).first() if collection_id else None

                if collection and not can_edit_collection(user, collection):
                    raise PermissionDenied(f"Sem permissão para adicionar amostras à coleção {collection.name}")

                # 2. Captura das listas de distribuição
                biobank_ids = request.POST.getlist("dist_biobank_id[]")
                quantities = request.POST.getlist("dist_quantity[]")

                if not biobank_ids:
                    raise ValueError("Nenhum biobanco selecionado para registrar a localização da amostra.")

                created_samples = []

                with transaction.atomic():
                    for i in range(len(biobank_ids)):
                        bb_id = biobank_ids[i]
                        qty = int(quantities[i]) if quantities[i] else 1
                        biobank = get_object_or_404(Biobank, id=bb_id)

                        for j in range(qty):
                            final_id = sample_id_base if qty == 1 and len(biobank_ids) == 1 else f"{sample_id_base}_{i+1}.{j+1}"

                            if Sample.objects.filter(sample_id=final_id).exists():
                                raise ValueError(f"O ID '{final_id}' já existe no sistema.")

                            # =======================================================
                            # ROTEAMENTO INTELIGENTE (HERANÇA DE MODELOS)
                            # =======================================================
                            base_data = {
                                "sample_id": final_id,
                                "organism_name": organism_name,
                                "sample_type": sample_type,
                                "collection": collection,
                                "biobank": biobank,
                                "scientific_notes": scientific_notes,
                                "is_public": is_public,
                                "owner": user,
                                "is_active": True,
                                "status": "pending",
                                "storage_location": storage_location,
                            }

                            if sample_type == "Bacteria (Host)":
                                r_markers = request.POST.get("resistance_markers", "")
                                r_list = [r.strip() for r in r_markers.split(",") if r.strip()]
                                
                                sample = Bacteria.objects.create(
                                    **base_data,
                                    species=request.POST.get("species", organism_name),
                                    strain=request.POST.get("strain", ""),
                                    genotype=request.POST.get("genotype", ""),
                                    resistance_markers=r_list
                                )

                            elif sample_type == "Phage (Virus)":
                                sample = Phage.objects.create(
                                    **base_data,
                                    morphotype=request.POST.get("morphotype"),
                                    taxonomy=request.POST.get("taxonomy"),
                                    lifestyle=request.POST.get("lifestyle"),
                                    isolation_source=request.POST.get("isolation_source"),
                                    genome_type=request.POST.get("genome_type"),
                                    genome_size_bp=request.POST.get("genome_size_bp") or None,
                                    ncbi_accession=request.POST.get("ncbi_accession"),
                                    temp_C=request.POST.get("temp_C") or None
                                )

                            elif sample_type == "Vector (Backbone)":
                                r_markers = request.POST.get("resistance_markers", "")
                                r_list = [r.strip() for r in r_markers.split(",") if r.strip()]
                                
                                sample = Vector.objects.create(
                                    **base_data,
                                    name_official=request.POST.get("name_official", organism_name),
                                    vector_type=request.POST.get("vector_type"),
                                    induction_system=request.POST.get("induction_system"),
                                    vector_size_bp=request.POST.get("vector_size_bp") or None,
                                    resistance_markers=r_list
                                )

                            elif sample_type == "Construction (Plasmid)":
                                p_vector_id = request.POST.get("parent_vector_id")
                                p_vector = Vector.objects.filter(id=p_vector_id).first() if p_vector_id else None
                                
                                sample = Construction.objects.create(
                                    **base_data,
                                    parent_vector=p_vector,
                                    construction_name=request.POST.get("construction_name", organism_name),
                                    insert_name=request.POST.get("insert_name", ""),
                                    insert_size_bp=request.POST.get("insert_size_bp") or 0
                                )

                            else:
                                # Fallback genérico para DNA, Serum ou outros não mapeados
                                sample = Sample.objects.create(**base_data)
                            
                            # =======================================================

                            # TAGS Genéricas
                            tag_ids = request.POST.getlist("tags")
                            if tag_ids:
                                sample.tags.set(tag_ids)

                            # KEYWORDS Adicionais
                            for raw in request.POST.getlist("keyword_pairs"):
                                if ":::" in raw:
                                    key, value = raw.split(":::")
                                    keyword_obj, _ = Keyword.objects.get_or_create(name=key.strip())
                                    kv, _ = KeywordValue.objects.get_or_create(
                                        keyword=keyword_obj,
                                        value=value.strip()
                                    )
                                    sample.keywords.add(kv)
                            
                            # EVENTO (LOG)
                            Event.objects.create(
                                sample=sample,
                                performed_by=user,
                                event_type="entry",
                                location_snapshot=storage_location,
                                notes=f"Amostra criada: {sample.organism_name}."
                            )

                            created_samples.append(sample)

                    # ARQUIVOS
                    files = request.FILES.getlist("file")
                    for sample in created_samples:
                        for f in files:
                            SampleFile.objects.create(sample=sample, file=f)

                messages.success(request, f"{len(created_samples)} amostra(s) registrada(s) com sucesso!")
                return redirect("samples_list")

            except ValueError as ve:
                messages.error(request, str(ve))
            except Exception as e:
                print(f"ERRO CRÍTICO CREATE SAMPLE: {e}") 
                messages.error(request, f"Erro ao processar amostra: {str(e)}")

    user_biobanks = Biobank.objects.filter(
        Q(owner=user) |
        Q(is_public=True)
    ).distinct()

    ctx = base_context(request)
    ctx.update({
        "collections": Collection.objects.all(),
        "all_tags": Tag.objects.all(),
        "biobanks": user_biobanks,
    })
    return render(request, "internal/samples/samples.html", ctx)


# =========================================================
# 3. IMPRESSÃO E EXPORTAÇÃO
# =========================================================
@login_required
def print_sample_label(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    if not can_view_sample(request.user, sample):
        raise PermissionDenied

    qr_data = str(sample.uuid)
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render(request, "internal/samples/print_label.html", {'sample': sample, 'qr_code': qr_base64})

@login_required
def export_samples_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_amostras.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['ID', 'UUID', 'Tipo', 'Organismo', 'Status', 'Visibilidade', 'Coleção', 'Biobanco', 'Localização', 'Dono', 'Criado em'])
    
    for s in Sample.objects.filter(is_active=True).select_related('collection', 'biobank', 'owner'):
        writer.writerow([
            s.sample_id, s.uuid, s.sample_type or '', s.organism_name or '', 
            s.get_status_display(),
            "Público" if s.is_public else "Privado", 
            s.collection.name if s.collection else '', 
            s.biobank.name if s.biobank else '',
            s.storage_location or '',
            s.owner.username, s.created_at.strftime('%d/%m/%Y %H:%M')
        ])
    return response

# =========================================================
# 4. EDIÇÃO (COM POLIMORFISMO DE MODELOS)
# =========================================================
@login_required
def sample_edit_view(request, sample_id):
    # 1. Pega a amostra genérica da base de dados
    base_sample = get_object_or_404(Sample, id=sample_id)
    
    # 2. Descobre a identidade real da amostra (Herança/Polimorfismo)
    if hasattr(base_sample, 'bacteria'):
        real_sample = base_sample.bacteria
    elif hasattr(base_sample, 'phage'):
        real_sample = base_sample.phage
    elif hasattr(base_sample, 'vector'):
        real_sample = base_sample.vector
    elif hasattr(base_sample, 'construction'):
        real_sample = base_sample.construction
    else:
        real_sample = base_sample

    # Verifica permissões no objeto real
    if not can_edit_sample(request.user, real_sample) and not request.user.is_superuser:
        raise PermissionDenied
    
    # 3. Puxa o formulário correto (ex: PhageForm em vez de SampleForm genérico)
    FormClass = get_form_class_for_sample(real_sample)
    
    if request.method == "POST":
        form = FormClass(request.POST, instance=real_sample)
        if form.is_valid():
            form.save()
            tag_ids = request.POST.getlist("tags")
            if tag_ids:
                real_sample.tags.set(tag_ids)
            messages.success(request, "Amostra atualizada com sucesso!")
            return redirect("samples_list")
        else:
            messages.error(request, "Erro ao atualizar. Verifique os campos.")
    else:
        form = FormClass(instance=real_sample)

    ctx = base_context(request)
    ctx.update({'form': form, 'sample': real_sample})
    return render(request, "internal/samples/edit.html", ctx)
