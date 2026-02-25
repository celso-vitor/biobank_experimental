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
)
from core.models.events.model import Event
from core.forms import SampleForm
from core.permissions.samples import can_view_sample, can_edit_collection

# =========================================================
# 1. DASHBOARD (LISTAGEM & FILTROS)
# =========================================================
@login_required
def samples_list_view(request):
    user = request.user
    qs = Sample.objects.filter(is_active=True).select_related('collection', 'owner').order_by("-created_at")

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
# 2. CREATE SAMPLE (CORRIGIDO)
# =========================================================
@login_required
def sample_create_view(request):
    user = request.user

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_sample":
            try:
                # 1. Captura de metadados globais
                sample_id_base = request.POST.get("sample_id")
                sample_type = request.POST.get("sample_type")
                organism_name = request.POST.get("organism_name")
                scientific_notes = request.POST.get("scientific_notes") 
                visibility = request.POST.get("visibility", "private")
                
                # NOVO: Captura da localização física
                storage_location = request.POST.get("storage_location", "")

                # 2. Captura das listas de distribuição
                biobank_ids = request.POST.getlist("dist_biobank_id[]")
                collection_ids = request.POST.getlist("dist_collection_id[]")
                quantities = request.POST.getlist("dist_quantity[]")

                if not biobank_ids:
                    raise ValueError("Nenhum biobanco selecionado para a distribuição.")

                created_samples = []

                with transaction.atomic():
                    for i in range(len(biobank_ids)):
                        bb_id = biobank_ids[i]
                        col_id = collection_ids[i]
                        qty = int(quantities[i]) if quantities[i] else 1

                        biobank = get_object_or_404(Biobank, id=bb_id)
                        collection = Collection.objects.filter(id=col_id).first() if col_id else None

                        if collection and not can_edit_collection(user, collection):
                             raise PermissionDenied(f"Sem permissão para a coleção {collection.name}")

                        for j in range(qty):
                            final_id = sample_id_base if qty == 1 and len(biobank_ids) == 1 else f"{sample_id_base}_{i+1}.{j+1}"

                            if Sample.objects.filter(sample_id=final_id).exists():
                                raise ValueError(f"O ID '{final_id}' já existe no sistema.")

                            # CRIAÇÃO DA AMOSTRA
                            sample = Sample.objects.create(
                                sample_id=final_id,
                                organism_name=organism_name,
                                sample_type=sample_type,
                                collection=collection,
                                biobank=biobank,
                                notes=scientific_notes,
                                visibility=visibility,
                                owner=user,
                                is_active=True,
                                status="pending",
                                storage_location=storage_location  # Salva a localização
                            )

                            # TAGS
                            tag_ids = request.POST.getlist("tags")
                            if tag_ids:
                                sample.tags.set(tag_ids)

                            # KEYWORDS
                            for raw in request.POST.getlist("keyword_pairs"):
                                if ":::" in raw:
                                    key, value = raw.split(":::")
                                    keyword_obj, _ = Keyword.objects.get_or_create(name=key.strip())
                                    kv, _ = KeywordValue.objects.get_or_create(
                                        keyword=keyword_obj,
                                        value=value.strip()
                                    )
                                    sample.keywords.add(kv)
                            
                            # EVENTO (CORRIGIDO PARA O SEU MODELO)
                            Event.objects.create(
                                sample=sample,           # FK direta para Sample
                                performed_by=user,       # Campo correto do seu model
                                event_type="entry",      # Tipo válido ("entry")
                                location_snapshot=storage_location, # Snapshot da localização inicial
                                notes=f"Amostra criada: {sample.organism_name}"
                            )

                            created_samples.append(sample)

                    files = request.FILES.getlist("file")
                    for sample in created_samples:
                        for f in files:
                            SampleFile.objects.create(sample=sample, file=f)

                messages.success(request, f"{len(created_samples)} amostras registradas com sucesso!")
                return redirect("samples_list")

            except ValueError as ve:
                messages.error(request, str(ve))
            except Exception as e:
                # Log do erro real para debug
                print(f"ERRO CRÍTICO CREATE SAMPLE: {e}") 
                messages.error(request, f"Erro crítico: {str(e)}")

    user_biobanks = Biobank.objects.filter(
        Q(owner=user) |
        Q(research_group__coordinator=user) |
        Q(research_group__members=user) |
        Q(visibility='public')
    ).distinct()

    ctx = base_context(request)
    ctx.update({
        "collections": Collection.objects.all(),
        "all_tags": Tag.objects.all(),
        "biobanks": user_biobanks,
    })
    return render(request, "internal/samples/samples.html", ctx)

# =========================================================
# 3. IMPRESSÃO E EXPORTAÇÃO (Mantidos iguais)
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
            s.get_status_display(), s.get_visibility_display(), 
            s.collection.name if s.collection else '', 
            s.biobank.name if s.biobank else '',
            s.storage_location or '',  # Exportando localização
            s.owner.username, s.created_at.strftime('%d/%m/%Y %H:%M')
        ])
    return response

@login_required
def sample_edit_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    if sample.owner != request.user and not request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == "POST":
        form = SampleForm(request.POST, instance=sample)
        if form.is_valid():
            form.save()
            tag_ids = request.POST.getlist("tags")
            if tag_ids:
                sample.tags.set(tag_ids)
            messages.success(request, "Amostra atualizada!")
            return redirect("samples_list")
        else:
            messages.error(request, "Erro ao atualizar.")
    else:
        form = SampleForm(instance=sample)

    ctx = base_context(request)
    ctx.update({'form': form, 'sample': sample})
    return render(request, "internal/samples/edit.html", ctx)
