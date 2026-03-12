from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', TemplateView.as_view(template_name='chat.html'), name='home'),
    path('api/sessions/', views.list_sessions, name='list_sessions'),
    path('api/sessions/create/', views.create_session, name='create_session'),
    path('api/sessions/<int:session_id>/', views.get_session, name='get_session'),
    path('api/sessions/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('api/sessions/<int:session_id>/summarize/', views.summarize_session, name='summarize_session'),
    path('api/chat/', views.chat, name='chat'),
    path('api/chat/stream/', views.chat_stream, name='chat_stream'),
    path('api/math/recognize/', views.recognize_formula, name='recognize_formula'),
    path('api/math/chat/', views.math_chat, name='math_chat'),
    path('api/math/check/', views.check_answer, name='check_answer'),
    path('api/auth/login/', views.login_view, name='login'),
    path('api/auth/register/', views.register_view, name='register'),
    path('api/auth/logout/', views.logout_view, name='logout'),
    path('api/stats/usage/', views.get_usage_stats, name='usage_stats'),
]
