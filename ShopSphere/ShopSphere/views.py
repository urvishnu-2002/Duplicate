from django.shortcuts import render, redirect

def home(request):
    # Redirect to the main product listing
    return redirect('home_api')

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)