from django.http import HttpResponse
from django.urls import reverse


def hx_redirect(viewname: str):
    response = HttpResponse()
    response["HX-Redirect"] = reverse(viewname)
    return response
