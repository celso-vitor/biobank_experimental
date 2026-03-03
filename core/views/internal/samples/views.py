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
    Bacteria,
    Phage,
    Vector,
    Construction
)
from core.models.events.model import Event
from core.models.samples.relationship import SampleRelationship

from core.forms import SampleForm, get_form_class_for_sample
from core.permissions.samples import can_view_sample, can_edit_sample, can_delete_sample
from core.permissions.collections import can_edit_collection

# =========================================================
# 1. DASHBOARD (LISTING & FILTERS)
# =========================================================
@login_required
def samples_list_view(request):
    user = request.user
    
    qs = Sample.objects.filter(is_active=True).select_related('biobank', 'owner').prefetch_related('collections').order_by("-created_at")

    query = request.GET.get('q')
    if query:
        qs = qs.filter(
            Q(sample_id__icontains=query) |
            Q(organism_name__icontains=query) |
            Q(sample_type__icontains=query)
        )

    status_filter = request.GET.get('status')
    if status_filter and status_filter not in ['', 'All Statuses']:
        qs = qs.filter(status=status_filter)

    collection_id = request.GET.get('collection')
    if collection_id and collection_id.isdigit():
        qs = qs.filter(collections__id=collection_id)

    ctx = base_context(request)
    ctx.update({
        'samples': qs,
        'filter_collections': Collection.objects.all(),
        'all_samples_for_modal': Sample.objects.filter(is_active=True).values('id', 'sample_id', 'sample_type', 'organism_name'),
    })
    return render(request, "internal/samples/list.html", ctx)


# =========================================================
# 2. CREATE SAMPLE
# =========================================================
@login_required
def sample_create_view(request):
    user = request.user

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_sample":
            try:
                sample_id_base = request.POST.get("sample_id")
                sample_type = request.POST.get("sample_type")
                organism_name = request.POST.get("organism_name")
                scientific_notes = request.POST.get("scientific_notes") 
                storage_location = request.POST.get("storage_location", "")

                is_public = request.POST.get("is_public") == "true" or request.POST.get("is_public") == "on"
                
                collection_id = request.POST.get("collection")
                collection_obj = Collection.objects.filter(id=collection_id).first() if collection_id else None

                if collection_obj and not can_edit_collection(user, collection_obj):
                    raise PermissionDenied(f"No permission to add samples to collection {collection_obj.name}")

                parent_sample_id_input = request.POST.get("parent_sample_id", "").strip()
                parent_rel_type = request.POST.get("parent_relationship_type", "aliquot")
                parent_sample_obj = None

                if parent_sample_id_input:
                    parent_sample_obj = Sample.objects.filter(sample_id=parent_sample_id_input).first()
                    if not parent_sample_obj:
                        raise ValueError(f"Source sample '{parent_sample_id_input}' not found.")

                biobank_ids = request.POST.getlist("dist_biobank_id[]")
                quantities = request.POST.getlist("dist_quantity[]")

                if not biobank_ids:
                    raise ValueError("No biobank selected.")

                created_samples = []

                with transaction.atomic():
                    for i in range(len(biobank_ids)):
                        bb_id = biobank_ids[i]
                        qty = int(quantities[i]) if quantities[i] else 1
                        biobank = get_object_or_404(Biobank, id=bb_id)

                        for j in range(qty):
                            final_id = sample_id_base if qty == 1 and len(biobank_ids) == 1 else f"{sample_id_base}_{i+1}.{j+1}"

                            if Sample.objects.filter(sample_id=final_id).exists():
                                raise ValueError(f"The ID '{final_id}' already exists in the system.")

                            base_data = {
                                "sample_id": final_id,
                                "organism_name": organism_name,
                                "sample_type": sample_type,
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
                                sample = Sample.objects.create(**base_data)
                            
                            # CORRECT PLURAL ADDITION FOR M2M
                            if collection_obj:
                                sample.collections.add(collection_obj)

                            if parent_sample_obj:
                                SampleRelationship.objects.create(
                                    source_sample=parent_sample_obj,
                                    target_sample=sample,
                                    relationship_type=parent_rel_type,
                                    created_by=user,
                                    notes="Relationship generated automatically during registration."
                                )

                            tag_ids = request.POST.getlist("tags")
                            if tag_ids:
                                sample.tags.set(tag_ids)

                            for raw in request.POST.getlist("keyword_pairs"):
                                if ":::" in raw:
                                    key, value = raw.split(":::")
                                    keyword_obj, _ = Keyword.objects.get_or_create(name=key.strip())
                                    kv, _ = KeywordValue.objects.get_or_create(
                                        keyword=keyword_obj,
                                        value=value.strip()
                                    )
                                    sample.keywords.add(kv)
                            
                            Event.objects.create(
                                sample=sample,
                                performed_by=user,
                                event_type="entry",
                                location_snapshot=storage_location,
                                notes=f"Sample registered: {sample.organism_name}."
                            )

                            created_samples.append(sample)

                    # =========================================================
                    # FILES UPLOAD
                    # =========================================================
                    files = request.FILES.getlist("file")
                    categories = request.POST.getlist("file_category")
                    descriptions = request.POST.getlist("file_description")
                    from core.models.samples.sample import SampleStorageLevel 
                    
                    for sample in created_samples:
                        for k, f in enumerate(files):
                            cat = categories[k] if k < len(categories) else "Other"
                            desc = descriptions[k] if k < len(descriptions) else ""
                            SampleFile.objects.create(sample=sample, file=f, category=cat, description=desc)
                            
                        # STORAGE LEVELS
                        if storage_location:
                            limpo = storage_location.replace('>', '|').replace(',', '|').replace(';', '|')
                            fatias = [f.strip() for f in limpo.split('|') if f.strip()]
                            
                            for nivel_atual, nome_fatia in enumerate(fatias):
                                SampleStorageLevel.objects.create(
                                    sample=sample,
                                    name=nome_fatia,
                                    level_index=nivel_atual
                                )

                messages.success(request, f"{len(created_samples)} sample(s) registered successfully!")
                return redirect("samples_list")

            except ValueError as ve:
                messages.error(request, str(ve))
            except Exception as e:
                print(f"CRITICAL ERROR CREATE SAMPLE: {e}") 
                messages.error(request, f"Error processing sample: {str(e)}")

    user_biobanks = Biobank.objects.filter(
        Q(owner=user) |
        Q(is_public=True)
    ).distinct()

    ctx = base_context(request)
    ctx.update({
        "collections": Collection.objects.all(),
        "all_tags": Tag.objects.all(),
        "biobanks": user_biobanks,
        "all_samples": Sample.objects.filter(is_active=True).values('sample_id', 'organism_name', 'sample_type'),
    })
    return render(request, "internal/samples/samples.html", ctx)


# =========================================================
# 3. PRINT & CSV EXPORT
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
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig') 
    response['Content-Disposition'] = 'attachment; filename="advanced_samples_report.csv"'
    writer = csv.writer(response, delimiter=';') 
    
    headers = [
        'ID / Barcode', 'Biological Type', 'Organism', 'Status', 'Visibility', 
        'Collections', 'Biobank', 'Storage Location', 'Owner', 'Created At',
        'Phage: Morphotype', 'Phage: Taxonomy', 'Phage: Lifestyle', 'Genome (Type)', 'Genome Size (bp)',
        'Bacteria: Species', 'Bacteria: Strain', 'Genotype', 'Resistance Markers',
        'Construction: Parent Vector', 'Construction: Insert', 'Insert Size (bp)'
    ]
    writer.writerow(headers)
    
    samples = Sample.objects.filter(is_active=True).select_related('biobank', 'owner').prefetch_related('collections')
    
    for s in samples:
        cols = ", ".join([c.name for c in s.collections.all()])

        row = [
            s.sample_id, s.sample_type or '', s.organism_name or '', 
            s.get_status_display(), "Public" if s.is_public else "Private", 
            cols, 
            s.biobank.name if s.biobank else '',
            s.storage_location or '',
            s.owner.username, s.created_at.strftime('%Y-%m-%d %H:%M')
        ]
        
        morphotype = taxonomy = lifestyle = genome_type = genome_size = ""
        species = strain = genotype = resistance = ""
        parent_vector = insert_name = insert_size = ""

        if hasattr(s, 'phage'):
            morphotype = s.phage.morphotype or ""
            taxonomy = s.phage.taxonomy or ""
            lifestyle = s.phage.lifestyle or ""
            genome_type = s.phage.genome_type or ""
            genome_size = s.phage.genome_size_bp or ""
            
        elif hasattr(s, 'bacteria'):
            species = s.bacteria.species or ""
            strain = s.bacteria.strain or ""
            genotype = s.bacteria.genotype or ""
            resistance = ", ".join(s.bacteria.resistance_markers) if isinstance(s.bacteria.resistance_markers, list) else s.bacteria.resistance_markers
            
        elif hasattr(s, 'vector'):
            resistance = ", ".join(s.vector.resistance_markers) if isinstance(s.vector.resistance_markers, list) else s.vector.resistance_markers
            
        elif hasattr(s, 'construction'):
            parent_vector = s.construction.parent_vector.sample_id if s.construction.parent_vector else ""
            insert_name = s.construction.insert_name or ""
            insert_size = s.construction.insert_size_bp or ""

        row.extend([
            morphotype, taxonomy, lifestyle, genome_type, genome_size,
            species, strain, genotype, resistance,
            parent_vector, insert_name, insert_size
        ])
        
        writer.writerow(row)
        
    return response

# =========================================================
# 4. EDIT VIEW 
# =========================================================
@login_required
def sample_edit_view(request, sample_id):
    base_sample = get_object_or_404(Sample, id=sample_id)
    
    if hasattr(base_sample, 'bacteria'): real_sample = base_sample.bacteria
    elif hasattr(base_sample, 'phage'): real_sample = base_sample.phage
    elif hasattr(base_sample, 'vector'): real_sample = base_sample.vector
    elif hasattr(base_sample, 'construction'): real_sample = base_sample.construction
    else: real_sample = base_sample

    if not can_edit_sample(request.user, real_sample) and not request.user.is_superuser:
        raise PermissionDenied
    
    FormClass = get_form_class_for_sample(real_sample)
    
    if request.method == "POST":
        form = FormClass(request.POST, request.FILES, instance=real_sample)
        if form.is_valid():
            form.save()
            tag_ids = request.POST.getlist("tags")
            if tag_ids:
                real_sample.tags.set(tag_ids)
                
            storage_location = form.cleaned_data.get('storage_location', '')
            from core.models.samples.sample import SampleStorageLevel
            
            SampleStorageLevel.objects.filter(sample=real_sample).delete()
            
            if storage_location:
                limpo = storage_location.replace('>', '|').replace(',', '|').replace(';', '|')
                fatias = [f.strip() for f in limpo.split('|') if f.strip()]
                
                for nivel_atual, nome_fatia in enumerate(fatias):
                    SampleStorageLevel.objects.create(
                        sample=real_sample,
                        name=nome_fatia,
                        level_index=nivel_atual
                    )
            
            files = request.FILES.getlist("file")
            categories = request.POST.getlist("file_category")
            descriptions = request.POST.getlist("file_description")
            
            for k, f in enumerate(files):
                cat = categories[k] if k < len(categories) else "Other"
                desc = descriptions[k] if k < len(descriptions) else ""
                SampleFile.objects.create(sample=base_sample, file=f, category=cat, description=desc)

            messages.success(request, "Sample updated successfully!")
            return redirect("samples_list")
        else:
            messages.error(request, "Error updating. Please check the fields.")
    else:
        form = FormClass(instance=real_sample)

    parents = base_sample.incoming_relationships.all() 
    children = base_sample.outgoing_relationships.all() 
    sample_files = SampleFile.objects.filter(sample=base_sample).order_by('-uploaded_at')

    ctx = base_context(request)
    ctx.update({
        'form': form, 
        'sample': real_sample,
        'parents': parents,
        'children': children,
        'sample_files': sample_files
    })
    return render(request, "internal/samples/edit.html", ctx)

# =========================================================
# 5. RELATIONSHIPS (NETWORK GRAPH)
# =========================================================
@login_required
def sample_relate_view(request, sample_id):
    """
    Handles Multi-Selection relationships and biological interactions (HostRange).
    """
    current_sample = get_object_or_404(Sample, id=sample_id)
    
    if not can_edit_sample(request.user, current_sample) and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == "POST":
        # Supports the Grid/Table layout we created earlier
        target_ids_str = request.POST.get("target_ids", "")
        target_ids = [tid for tid in target_ids_str.split(",") if tid]
        general_notes = request.POST.get("notes", "")

        if not target_ids:
            messages.warning(request, "No samples selected to relate.")
            return redirect("samples_list")

        try:
            with transaction.atomic():
                for t_id in target_ids:
                    target_sample = Sample.objects.get(id=t_id)
                    if current_sample == target_sample: continue
                    
                    # Capture specific row data (Fallback to global if using simple modal)
                    direction = request.POST.get(f"direction_{t_id}") or request.POST.get("direction", "out")
                    rel_type = request.POST.get(f"type_{t_id}") or request.POST.get("relationship_type")
                    eop = request.POST.get(f"eop_{t_id}") or request.POST.get("eop")

                    if direction == "in":
                        source, destination = target_sample, current_sample
                    else:
                        source, destination = current_sample, target_sample

                    # 1. Create visual graph relationship
                    SampleRelationship.objects.create(
                        source_sample=source,
                        target_sample=destination,
                        relationship_type=rel_type,
                        notes=general_notes,
                        created_by=request.user
                    )
                    
                    # Log event
                    Event.objects.create(
                        sample=current_sample,
                        performed_by=request.user,
                        event_type="update",
                        notes=f"Relationship added: {rel_type} with {target_sample.sample_id}"
                    )

                    # 2. Host-Range scientific logic
                    if rel_type == "infects":
                        phage_obj = None
                        bacteria_obj = None
                        
                        if hasattr(source, 'phage') and hasattr(destination, 'bacteria'):
                            phage_obj, bacteria_obj = source.phage, destination.bacteria
                        elif hasattr(destination, 'phage') and hasattr(source, 'bacteria'):
                            phage_obj, bacteria_obj = destination.phage, source.bacteria
                            
                        if phage_obj and bacteria_obj:
                            from core.models.samples.subtypes import HostRange
                            HostRange.objects.update_or_create(
                                phage=phage_obj, bacteria=bacteria_obj,
                                defaults={'efficiency_eop': eop if eop else None}
                            )

            messages.success(request, f"Relationships connected successfully for {len(target_ids)} sample(s)!")
        
        except Exception as e: 
            messages.error(request, f"Error processing relationship: {str(e)}")
            
    return redirect("samples_list")
