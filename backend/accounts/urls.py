from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_step1, name='signup'),
    path('signup/farm/', views.signup_step2, name='signup_step2'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.user_settings_view, name='user_settings'),
    path('update-language/', views.update_language_preference, name='update_language'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
]
