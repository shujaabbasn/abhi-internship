import pymongo

mongo_client=pymongo.MongoClient("mongodb://localhost:27017/")
library_database=mongo_client["library_db"]
books_collection=library_database["books"]


starting_books=[
    {"title": "Clean Code","author": "Robert Martin","is_borrowed": False,"borrowed_by": None},
    {"title": "The Pragmatic Programmer","author":"David Thomas","is_borrowed": False, "borrowed_by": None},
    {"title": "Deep Work","author": "Cal Newport","is_borrowed": False,"borrowed_by": None},
    {"title": "Atomic Habits","author": "James Clear","is_borrowed":False, "borrowed_by": None},
    {"title": "Sapiens","author": "Yuval Noah","is_borrowed": False,"borrowed_by": None}
]

if books_collection.count_documents({})==0:
    books_collection.insert_many(starting_books)
    print("database seeded for the first time")
else:
    print("database already has data, skipping seed")

def add_book(title, author):
    if books_collection.find_one({"title": title}) is not None:
        print("Add Failed: '"+title+"' already exists in the library.")
        return

    new_book={
        "title": title,
        "author": author,
        "is_borrowed": False,
        "borrowed_by": None
    }
    books_collection.insert_one(new_book)
    print("Added: '"+title+"' by "+author+" has been added.")


def borrow_book(title, borrowed_by):

    if books_collection.find_one({"title": title}) is None:
        print("Borrow Failed: '"+title+"' does not exist.")
        return

    if books_collection.find_one({"title": title})["is_borrowed"]==True:
        print("Borrow Failed: '"+title+"' is already borrowed by "+books_collection.find_one({"title": title})["borrowed_by"]+".")
        return

    books_collection.update_one(
        {"title": title},
        {"$set": {"is_borrowed": True, "borrowed_by": borrowed_by}}
    )
    print("Borrowed: '"+title+"' has been borrowed by "+borrowed_by+".")


def return_book(title):

    if books_collection.find_one({"title": title}) is None:
        print("Return Failed: '"+title+"' does not exist.")
        return

    if books_collection.find_one({"title": title})["is_borrowed"]==False:
        print("Return Failed: '"+title+"' is not currently borrowed.")
        return

    books_collection.update_one(
        {"title": title},
        {"$set": {"is_borrowed": False, "borrowed_by": None}}
    )
    print("Returned: '"+title+"' has been returned.")


def show_available_books():
    print("\nAvailable Books:")
    available_cursor=books_collection.find({"is_borrowed": False}, {"_id": 0})

    available_list=[]
    for book in available_cursor:
        available_list.append(book)

    if len(available_list)==0:
        print(" - No books currently available.")
    else:
        for book in available_list:
            print(" - "+book["title"]+" by "+book["author"])


def show_borrowed_books():
    print("\nBorrowed Books:")
    borrowed_cursor=books_collection.find({"is_borrowed": True},{"_id": 0})

    borrowed_list=[]
    for book in borrowed_cursor:
        borrowed_list.append(book)

    if len(borrowed_list)==0:
        print(" - No books currently borrowed.")
    else:
        for book in borrowed_list:
            print(" - "+book["title"]+" (Borrowed by: "+book["borrowed_by"]+")")


def delete_book(title):
    delete_result=books_collection.delete_one({"title": title})

    if delete_result.deleted_count==0:
        print("Delete Failed: '"+title+"' does not exist.")
    else:
        print("Deleted: '"+title+"' has been removed from the library.")


#TESTS
show_available_books()

add_book("Dune", "Frank Herbert")
add_book("Clean Code", "Robert Martin")  # already exists

borrow_book("Dune", "Ahmed")
borrow_book("Atomic Habits", "Sara")
borrow_book("Dune", "Ali")               # already borrowed

show_borrowed_books()
show_available_books()

return_book("Dune")
return_book("Sapiens")                   # not borrowed

delete_book("Deep Work")
delete_book("Harry Potter")              # doesn't exist

print("\nfinal state:")
show_available_books()
show_borrowed_books()
return_book("Atomic Habits")
show_available_books()

#compass tool gui
#for visual

#vector: look into either chromaDB, Qdrant, postgres. vector db, backend is same
#rag give contents, a text file, stored in vectordb, then query


#dummyjson
#webhook