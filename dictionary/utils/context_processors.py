def get_current_path(request):
    return {'current_path': request.get_full_path()}