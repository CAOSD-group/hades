from django.urls import path

from api import views

urlpatterns = [
    path('hello-view/', views.HelloAPIView.as_view()),
    path('nodes/', views.KubeNodes.as_view()),
    path('ns/', views.NSPackages.as_view()),
    path('top-clusters/', views.TopClusters.as_view()),
    path('nsi/', views.NSInstances.as_view()),
    path('knf/', views.KNFInstances.as_view()),
    path('ids/', views.IdList.as_view()),
    path('location/', views.Location.as_view()),
    path('manager/', views.Manager.as_view()),
    path('deployment/', views.Deployment.as_view())
    # path('top/', views.KubeTopNodes.as_view()),
    # path('namespaces/', views.KubeNamespaces.as_view()),
    # path('deployments/', views.KubeDeployments.as_view()),
    # # services
    # path('ports/', views.KubePorts.as_view()),
    # path('specs/', views.KubeSpecs.as_view()),
]
