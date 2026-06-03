from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.users.models import User


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 30

    def get_queryset(self):
        qs = User.objects.order_by('email')
        q = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '')
        active = self.request.GET.get('active', '')
        if q:
            qs = qs.filter(email__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
        if role:
            qs = qs.filter(role=role)
        if active == '1':
            qs = qs.filter(is_active=True)
        elif active == '0':
            qs = qs.filter(is_active=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['roles'] = User.Role.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['current_role'] = self.request.GET.get('role', '')
        ctx['current_active'] = self.request.GET.get('active', '')
        ctx['total_count'] = User.objects.count()
        ctx['active_count'] = User.objects.filter(is_active=True).count()
        ctx['pending_count'] = User.objects.filter(role='customer', is_active=False).count()
        return ctx


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'profile'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['roles'] = User.Role.choices
        return ctx


class UserToggleActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('users:user-detail', pk=pk)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        state = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'{user.email} has been {state}.')
        return redirect('users:user-detail', pk=pk)


class UserChangeRoleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, 'You cannot change your own role here.')
            return redirect('users:user-detail', pk=pk)
        new_role = request.POST.get('role')
        valid_roles = [r for r, _ in User.Role.choices]
        if new_role in valid_roles:
            user.role = new_role
            user.save(update_fields=['role'])
            messages.success(request, f'{user.email} role changed to {user.get_role_display()}.')
        return redirect('users:user-detail', pk=pk)
