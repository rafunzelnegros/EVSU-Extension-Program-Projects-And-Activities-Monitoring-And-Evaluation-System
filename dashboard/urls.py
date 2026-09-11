from django.urls import path
from . import views
urlpatterns=[
 path('login/',views.login_view,name='login'),path('logout/',views.logout_view,name='logout'),path('',views.dashboard,name='dashboard'),
 path('ppas/',views.ppa_list,name='ppa_list'),path('ppas/add/program/',views.ppa_add_program,name='ppa_add_program'),path('ppas/add/project/',views.ppa_add_project,name='ppa_add_project'),path('ppas/<int:pk>/',views.ppa_detail,name='ppa_detail'),path('ppas/<int:pk>/lifecycle/',views.ppa_lifecycle,name='ppa_lifecycle'),
 path('qpar/',views.qpar_list,name='qpar_list'),path('qpar/add/',views.qpar_edit,name='qpar_add'),path('qpar/<int:pk>/edit/',views.qpar_edit,name='qpar_edit'),
 path('taep/',views.taep_report,name='taep_report'),
 path('quarterly-monitoring/',views.qmr_list,name='qmr_list'),path('quarterly-monitoring/add/',views.qmr_edit,name='qmr_add'),path('quarterly-monitoring/<int:pk>/edit/',views.qmr_edit,name='qmr_edit'),path('quarterly-monitoring/<int:pk>/print/',views.qmr_print,name='qmr_print'),
 path('field-visits/',views.field_visit_list,name='field_visit_list'),path('field-visits/add/',views.field_visit_create,name='field_visit_add'),path('field-visits/<int:pk>/print/',views.field_visit_print,name='field_visit_print'),
 path('analytics/',views.analytics,name='analytics'),path('admin/users/',views.manage_users,name='manage_users'),path('admin/activity-log/',views.activity_logs,name='activity_logs')]
