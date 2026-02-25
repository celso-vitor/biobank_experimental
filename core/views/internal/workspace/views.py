from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from core.context import base_context

# Models
from core.models.biobanks.biobank import Biobank
from core.models.collections.collection import Collection
from core.models.samples.sample import Sample
from core.models.events.model import Event

# Imports de Views (Mantidos para o roteamento)
from core.views.internal.biobanks.views import biobanks_view
from core.views.internal.collections.views import collections_view
from core.views.internal.samples.views import samples_list_view
from core.views.internal.tags.views import (
    tags_view, search_view, create_tag_view, edit_tag_view, delete_tag_view
)
from core.views.internal.keywords.views import (
    keywords_view, edit_keyword_view, delete_keyword_view
)

@login_required
def home(request):
    page = request.GET.get("page", "workspace")

    ROUTES = {
        "workspace": workspace_view,
        "biobanks": biobanks_view,
        "collections": collections_view,
        "samples": samples_list_view,
        "tags": tags_view,
        "search_tags": search_view,
        "add_tag": create_tag_view,
        "edit_tag": edit_tag_view,
        "delete_tag": delete_tag_view,
        "keywords": keywords_view,
        "edit_keyword": edit_keyword_view,
        "delete_keyword": delete_keyword_view,
    }

    view_func = ROUTES.get(page, workspace_view)
    return view_func(request)

def workspace_view(request):
    ctx = base_context(request)
    user = request.user

    # --- 1. KPI COUNTERS ---
    # Total Active Samples
    total_samples = Sample.objects.filter(is_active=True).count()
    
    # Samples Pending QC (Quality Control) or Validation
    pending_qc = Sample.objects.filter(is_active=True, status__in=['pending', 'qc']).count()
    
    # Samples created in the last 30 days
    last_30_days = timezone.now() - timedelta(days=30)
    new_samples = Sample.objects.filter(is_active=True, created_at__gte=last_30_days).count()

    # Total Collections
    total_collections = Collection.objects.filter(is_active=True).count()

    # --- 2. CHART DATA (Distribution by Sample Type) ---
    # Agrupa amostras por tipo e conta. Ex: [{'sample_type': 'DNA', 'total': 10}, ...]
    type_distribution = (
        Sample.objects.filter(is_active=True)
        .values('sample_type')
        .annotate(total=Count('id'))
        .order_by('-total')[:5] # Top 5 types
    )
    
    # Prepare data for Chart.js
    chart_labels = [item['sample_type'] or 'Unspecified' for item in type_distribution]
    chart_data = [item['total'] for item in type_distribution]

    # --- 3. RECENT ACTIVITY ---
    recent_activity = Event.objects.all().select_related('performed_by', 'sample').order_by("-timestamp")[:6]

    ctx["stats"] = {
        "total_samples": total_samples,
        "pending_qc": pending_qc,
        "new_samples_30d": new_samples,
        "total_collections": total_collections,
        "recent_activity": recent_activity,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    }

    return render(request, "internal/workspace/workspace.html", ctx)
