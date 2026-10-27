class AuthorityScopedAdminMixin:
    """Restrict non-superusers to objects owned by their assigned authority."""

    authority_lookup = "authority"

    def _authority_id(self, request):
        try:
            return request.user.examguard_profile.authority_id
        except (AttributeError, TypeError):
            return None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        authority_id = self._authority_id(request)
        if not authority_id:
            return queryset.none()
        lookup = (
            "pk" if self.authority_lookup == "pk" else f"{self.authority_lookup}_id"
        )
        return queryset.filter(**{lookup: authority_id})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "authority" and not request.user.is_superuser:
            from authorities.models import Authority

            authority_id = self._authority_id(request)
            kwargs["queryset"] = Authority.objects.filter(pk=authority_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
