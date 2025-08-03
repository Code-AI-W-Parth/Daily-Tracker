# How  to call def to another def in another class.
### To call  a def to  another def to another one  in different  class first you have to assign   the class to a variable  then you write the variables name then dot. After that, you write the def and the arguments  which you put it in round brackets.
## Example:
class a :
def_1(self)
 print("I am def_1 from class a")


class B:
    def a(self):
        obj_a = A()         # Create object of class A
        obj_a.def_1()       # Call def_1 from class A
        print("I am def a() from class B")






# How  to call a def to another def in the same class.




# How to run UI
## streamlit run pie_graph.py --server.address=0.0.0.0