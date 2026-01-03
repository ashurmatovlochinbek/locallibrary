import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView

from .forms import RenewBookForm
from .models import Book, BookInstance, Author, Genre
from django.views import generic

# Create your views here.

def index(request):
    """View function for home page of site."""

    # Generate counts of some of the main objects
    num_books = Book.objects.count()
    num_instances = BookInstance.objects.count()

    # Available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()

    # The 'all()' is implied by default.
    num_authors = Author.objects.count()

    genres = Genre.objects.count()

    num_visits = request.session.get('num_visits', 0)
    num_visits += 1
    request.session['num_visits'] = num_visits

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': genres,
        'num_visits': num_visits,
    }

    # Render the HTML template index.html with the data in the context variable
    return render(request, 'catalog/index.html', context=context)

class BookListView(generic.ListView):
    model = Book
    context_object_name = 'books'
    paginate_by = 10
    template_name = 'catalog/book_list.html'

    def get_queryset(self):
        return Book.objects.all()

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        # Create any data and add it to the context
        context['some_data'] = 'This is just some data'
        return context

class BookDetailView(generic.DetailView):
    model = Book
    context_object_name = 'book'
    template_name = 'catalog/book_detail.html'

class AuthorListView(generic.ListView):
    model = Author
    context_object_name = 'authors'
    template_name = 'catalog/author_list.html'
    paginate_by = 10

class AuthorDetailView(generic.DetailView):
    model = Author
    context_object_name = 'author'
    template_name = 'catalog/author_detail.html'


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10
    context_object_name = 'my_books'

    def get_queryset(self):
        return (BookInstance.objects.filter(borrower=self.request.user)
                .filter(status__exact='o')
                .order_by('due_back'))


class AllBorrowedBooksListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_all.html'
    paginate_by = 10
    context_object_name = 'all_borrowed_books'
    permission_required = 'catalog.can_mark_returned'

    def get_queryset(self):
        return (BookInstance.objects.filter(status__exact='o')
                .order_by('due_back'))


# @login_required
# @permission_required('catalog.can_mark_returned', raise_exception=True)
# def renew_book_librarian(request, pk):
#     book_instance = BookInstance.objects.get(pk=pk)
#     if request.method == 'POST':
#         # Create a form instance and populate it with data from the request (binding):
#         form = RenewBookForm(request.POST)
#         # Check if the form is valid:
#         if form.is_valid():
#             # Process the data in form.cleaned_data as required (here we just write it to the model due_back field)
#             book_instance.due_back = form.cleaned_data['renewal_date']
#             book_instance.save()
#
#             # Redirect to a new URL:
#             return HttpResponseRedirect(reverse('all-borrowed'))
#     # If this is a GET (or any other method) create the default form.
#     else:
#         proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
#         form = RenewBookForm(initial={'renewal_date': proposed_renewal_date})
#
#     context = {
#         'form': form,
#         'book_instance': book_instance,
#     }
#     return render(request, 'catalog/book_renew_librarian.html', context)

class RenewBookLibrarianView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    template_name = 'catalog/book_renew_librarian.html'
    form_class = RenewBookForm
    permission_required = 'catalog.can_mark_returned'

    def get_success_url(self):
        return reverse_lazy('all-borrowed')

    def get_initial(self):
        """
        Provide initial form data for GET request
        """
        return {'renewal_date': datetime.date.today() + datetime.timedelta(weeks=3)}

    def get_context_data(self, **kwargs):
        """
        Pass the book_instance to the template
        """
        context = super().get_context_data(**kwargs)
        context['book_instance'] = BookInstance.objects.get(pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        """
        Called when valid form is submitted
        """
        book_instance = BookInstance.objects.get(pk=self.kwargs['pk'])
        book_instance.due_back = form.cleaned_data['renewal_date']
        book_instance.save()
        return super().form_valid(form)


from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Author
class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']
    initial = {'date_of_death': '11/06/2024'}
    template_name = 'catalog/author_form.html'
    permission_required = 'catalog.add_author'
    #success_url = reverse_lazy('author_detail') Django will call get_absolute_url method of the model


class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    # Not recommended (potential security issue if more fields added)
    fields = '__all__'
    permission_required = 'catalog.change_author'
    template_name = 'catalog/author_form.html'


class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.delete_author'
    template_name = 'catalog/author_confirm_delete.html'

    def form_valid(self, form):
        try:
            self.object.delete()
            return HttpResponseRedirect(self.success_url)
        except Exception as e:
            return HttpResponseRedirect(
                reverse("author-delete", kwargs={"pk": self.object.pk})
            )