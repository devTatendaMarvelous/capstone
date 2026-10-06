from django.contrib.admin import AdminSite


class SmartCropAdminSite(AdminSite):
    site_header = "SmartCrop"
    site_title = "SmartCrop administration"
    index_title = "Maize yield system"
    index_template = "admin/smartcrop_index.html"

    def index(self, request, extra_context=None):
        from apps.analytics.services import admin_dashboard

        extra = extra_context or {}
        extra["smartcrop"] = admin_dashboard()
        return super().index(request, extra)


admin_site = SmartCropAdminSite(name="smartcrop_admin")
