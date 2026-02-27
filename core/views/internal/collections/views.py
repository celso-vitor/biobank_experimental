from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

from core.context import base_context
from core.forms import CollectionForm

from core.models import (
    Collection,
    Tag,
    Keyword,
    KeywordValue,
)

from core.permissions.collections import (
    can_view_collection,
    can_edit_collection,
)

@login_required
def collections_view(request):
    user = request.user
    action = request.POST.get("action") if request.method == "POST" else None

    # 1. CREATE COLLECTION
    if action == "add_collection":
        form = CollectionForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    collection = form.save(commit=False)
                    collection.owner = user
                    collection.is_active = True
                    collection.save()

                    selected_tags = request.POST.getlist("tags")
                    if selected_tags:
                        collection.tags.set(selected_tags)

                    pairs = request.POST.getlist("keyword_pairs")
                    for raw in pairs:
                        if ":::" not in raw: continue
                        key, value = raw.split(":::")
                        if key.strip() and value.strip():
                            keyword_obj, _ = Keyword.objects.get_or_create(name=key.strip())
                            kv, _ = KeywordValue.objects.get_or_create(keyword=keyword_obj, value=value.strip())
                            collection.keywords.add(kv)

                    messages.success(request, "Collection criada com sucesso!")
                    return redirect("/?page=collections")

            except Exception as e:
                messages.error(request, f"Erro ao criar Collection: {e}")
                return redirect("/?page=collections")
        else:
            errors = form.errors.as_text()
            messages.error(request, f"Dados inválidos: {errors}")
            return redirect("/?page=collections")

    # 2. DEACTIVATE
    elif action == "deactivate_collection":
        cid = request.POST.get("collection_id")
        collection = get_object_or_404(Collection, id=cid)
        # Mudamos para can_edit_collection já que não há mais permissão de "management" separada
        if not can_edit_collection(user, collection):
            raise PermissionDenied
        collection.is_active = False
        collection.save(update_fields=["is_active"])
        messages.success(request, "Collection desativada com sucesso.")
        return redirect("/?page=collections")

    # 3. LISTAGEM (GET)
    initial = {}
    biobank_id = request.GET.get("biobank")
    if biobank_id:
        initial["biobank"] = biobank_id

    form = CollectionForm(initial=initial)
    ctx = base_context(request)
    ctx["collection_form"] = form
    ctx["all_tags"] = Tag.objects.all().order_by("name")

    collections_qs = Collection.objects.filter(is_active=True)
    if biobank_id:
        collections_qs = collections_qs.filter(biobank_id=biobank_id)

    visible_collections = []
    for c in collections_qs:
        if can_view_collection(user, c):
            c.can_edit = can_edit_collection(user, c)
            c.can_manage_members = False
            visible_collections.append(c)

    ctx["collections"] = visible_collections

    return render(request, "internal/collections/collections.html", ctx)
