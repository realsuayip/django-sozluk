from django.urls import path

from graphene_django.views import GraphQLView


app_name = "graph"

urlpatterns = [path("", GraphQLView.as_view(graphiql=True), name="endpoint")]
