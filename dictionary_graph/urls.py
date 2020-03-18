from django.urls import path
from django.views.decorators.csrf import csrf_exempt  # FOR DEBUGGING PURPOSES ONLY
from graphene_django.views import GraphQLView


app_name = "graph"

urlpatterns = [path("", csrf_exempt(GraphQLView.as_view(graphiql=True)), name="endpoint")]
