from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.context import base_context
from core.models.biobanks.biobank_user_role import BiobankUserRole
from core.models.collections.collection_user_role import CollectionUserRole

@login_required
def profile_view(request):
    user = request.user
    ctx = base_context(request)

    # Buscar permissões
    biobank_roles = BiobankUserRole.objects.filter(user=user).select_related('biobank')
    collection_roles = CollectionUserRole.objects.filter(user=user).select_related('collection')

    ctx['biobank_roles'] = biobank_roles
    ctx['collection_roles'] = collection_roles
    
    return render(request, "internal/profile/profile.html", ctx)
