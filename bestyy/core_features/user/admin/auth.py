from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name')

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

class CustomAdminSite(admin.AdminSite):
    site_header = 'Bestyy Admin'
    site_title = 'Bestyy Admin Portal'
    index_title = 'Welcome to Bestyy Admin'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._custom_views = []
    
    def has_permission(self, request):
        """
        Only superusers can access the admin site.
        """
        return request.user.is_active and request.user.is_superuser
    
    def register_view(self, path, view, name=None, visible=True, label=None, icon_class=None):
        """
        Register a custom admin view.
        
        Args:
            path: The URL path for the view
            view: The view function or class
            name: The URL name (defaults to the view's name)
            visible: Whether to show the view in the admin index
            label: The display name in the admin index
            icon_class: CSS class for the icon (e.g., 'fas fa-chart-bar')
        """
        self._custom_views.append({
            'path': path,
            'view': view,
            'name': name or view.__name__,
            'visible': visible,
            'label': label or name or view.__name__.replace('_', ' ').title(),
            'icon_class': icon_class or 'fas fa-link'
        })
    
    def get_urls(self):
        """
        Add custom views to the URL configuration.
        """
        from django.urls import path
        
        # Get the standard URLs
        urls = super().get_urls()
        
        # Add custom views
        for view_info in self._custom_views:
            urls.insert(
                0,
                path(
                    view_info['path'],
                    self.admin_view(view_info['view']),
                    name=view_info['name']
                )
            )
        
        return urls