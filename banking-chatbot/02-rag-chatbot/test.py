import pymongo

mongo_client=pymongo.MongoClient("mongodb://localhost:27017/")
school_database=mongo_client["school_db"]
students_collection=school_database["students"]
students_collection.drop() #for a clean slate each run and to avoid duplicates

starting_students = [
    {"name": "Ahmed", "age": 25, "grade": "A"},
    {"name": "Sara",  "age": 22, "grade": "B"},
    {"name": "Ali",   "age": 23, "grade": "A"},
    {"name": "Zara",  "age": 24, "grade": "C"},
    {"name": "Umar",  "age": 21, "grade": "D"}
]

students_collection.insert_many(starting_students)
print("database seeded")

def add_student(name, age, grade):
    existing_student=students_collection.find_one({"name": name})
    if existing_student is not None:
        print("student "+name+" already exists")
        return
    new_student={
        "name":name,
        "age":age,
        "grade":grade
    }
    students_collection.insert_one(new_student)
    print("added student: "+name)


def update_grade(name, new_grade):
    update_result=students_collection.update_one(
        {"name":name},
        {"$set":{"grade":new_grade}}
    )
    if update_result.matched_count==0:
        print("no student found with name: "+name)
    else:
        print("updated "+name+" grade to "+new_grade)


def get_students_by_grade(grade):
    grade_cursor=students_collection.find(
        {"grade":grade},
        {"name":1,"age":1,"grade":1,"_id":0}
    )

    student_list=[]
    for student in grade_cursor:
        student_list.append(student)

    for student in student_list:
            print(student["name"])

def get_students_by_age(age):
    age_cursor=students_collection.find(
        {"age":age},
        {"name":1,"age":1,"grade":1,"_id":0}
    )
    student_list=[]
    for student in age_cursor:
        student_list.append(student)
        
    for student in student_list:
            print(student["name"])

def delete_student(name):
    delete_result=students_collection.delete_one({"name": name})
    if delete_result.deleted_count==0:
        print("no student found with name: "+name)
    else:
        print("deleted student: "+name)

def show_all_students():
    all_cursor=students_collection.find().sort({"name":-1})
    print("\nall students:")
    for student in all_cursor:
        print(" ", student["name"], "| age:", student["age"], "| grade:", student["grade"])

show_all_students()

add_student("Bilal", 20, "B")
add_student("Ahmed", 99, "A")  #should say already exists

update_grade("Umar", "C")
update_grade("Ghost", "A")     #should say not found

get_students_by_grade("A")
get_students_by_grade("F")     #should say none found

print("AGE:")
get_students_by_age(21)

delete_student("Zara")
delete_student("huwahuiuhawhiudifha")        #should say not found

print("\nfinal state:")
show_all_students()