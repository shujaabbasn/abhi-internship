library_books=[
    {"title":"Clean Code", "author":"Robert Martin", "is_borrowed":False, "borrowed_by":None},
    {"title":"The Pragmatic Programmer", "author":"David Thomas", "is_borrowed":False, "borrowed_by":None},
    {"title":"Deep Work", "author":"Cal Newport", "is_borrowed":False, "borrowed_by":None},
    {"title":"Atomic Habits", "author":"James Clear", "is_borrowed":False, "borrowed_by":None},
    {"title":"Sapiens", "author":"Yuval Noah", "is_borrowed":False, "borrowed_by":None}
]

def add_book(title, author):
    for book in library_books:
        if book["title"]==title:
            print("Add Failed: The book '" + title + "' already exists in the library.")
            return
            
    new_book={
        "title":title,
        "author":author,
        "is_borrowed":False,
        "borrowed_by":None
    }
    library_books.append(new_book)
    print("Added: '" + title + "' by " + author + " has been added to the library.")

def borrow_book(title, borrowed_by):
    for book in library_books:
        if book["title"]==title:
            if book["is_borrowed"]==True:
                print("Borrow Failed: '" + title + "' is already borrowed by " + book['borrowed_by'])
                return
            else:
                book["is_borrowed"]=True
                book["borrowed_by"]=borrowed_by
                print("Borrowed: '" + title + "' has been successfully borrowed by " + borrowed_by)
                return
                
    print("Borrow Failed: The book '" + title + "' does not exist.")

def return_book(title):
    for book in library_books:
        if book["title"]==title:
            if book["is_borrowed"]==False:
                print("Return Failed: '" + title + "' cannot be returned because it isn't currently borrowed.")
                return
            else:
                book["is_borrowed"]=False
                book["borrowed_by"]=None
                print("Returned: '" + title + "' has been successfully returned.")
                return
                
    print("Return Failed: The book '" + title + "' does not exist.")

def show_available_books():
    print("\nAvailable Books:")
    found_available_book=False
    
    for book in library_books:
        if book["is_borrowed"]==False:
            print(" - " + book['title'] + " by " + book['author'])
            found_available_book=True
            
    if found_available_book==False:
        print(" - No books are currently available.")

def show_borrowed_books():
    print("\nBorrowed Books")
    found_borrowed_book=False
    
    for book in library_books:
        if book["is_borrowed"]==True:
            print(" - " + book['title'] + " (Borrowed by: " + book['borrowed_by'] + ")")
            found_borrowed_book=True
            
    if found_borrowed_book==False:
        print(" - No books are currently borrowed.")

def delete_book(title):
    index_to_remove = -1

    for current_index in range(len(library_books)):
        current_book = library_books[current_index]
        if current_book["title"] == title:
            index_to_remove = current_index
            break

    if index_to_remove != -1:
        del library_books[index_to_remove]
        print("Deleted: '" + title + "' has been removed from the library.")
    else:
        print("Delete Failed: The book '" + title + "' does not exist.")
        
#tests
show_available_books()
print("\nRUNNING TESTS")
add_book("Dune", "Frank Herbert")
add_book("Clean Code", "Robert Martin")

borrow_book("Dune", "Ahmed")
borrow_book("Atomic Habits", "Sara")
borrow_book("Dune", "Ali")

show_borrowed_books()
show_available_books()

print("\n--- Testing Returns & Deletions ---")
return_book("Dune")
return_book("Sapiens")

delete_book("Deep Work")
delete_book("Harry Potter")

print("\nfinal state:")
show_available_books()
show_borrowed_books()