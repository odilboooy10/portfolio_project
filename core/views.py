from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.views import View


class RootView(View):
    def get(self, request):
        if request.META.get('SERVER_PORT') == '8001':
            return redirect('/store/login/')
        return redirect('/dashboard/')


class LoginView(View):
    template_name = 'auth/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        return render(request, self.template_name, {'form': AuthenticationForm()})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == 'customer':
                return render(request, self.template_name, {
                    'form': form,
                    'error': 'Customer accounts use the store login at /store/login/'
                })
            if user.role != 'admin':
                return render(request, self.template_name, {
                    'form': form,
                    'error': 'Access denied. This panel is for administrators only.'
                })
            login(request, user)
            return redirect(request.POST.get('next') or 'dashboard:index')
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('login')

    def get(self, request):
        logout(request)
        return redirect('login')
