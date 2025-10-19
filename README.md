# Daily Tracker Application

## Description
A time tracking application built with Streamlit that allows users to log their daily activities, view analytics, and generate reports.

## Prerequisites
- Python 3.7 or higher
- Required packages: streamlit, pandas, matplotlib, psycopg2-binary

## Installation
1. Install Python from https://www.python.org/
2. Install required packages:
   ```
   pip install streamlit pandas matplotlib psycopg2-binary
   ```

## How to Run
```bash
streamlit run pie_graph.py
```

Or if you need to specify the full path to Python:
```bash
python -m streamlit run pie_graph.py
```

## Features
- Time logging with date, time ranges, and activity descriptions
- Pie charts for visualizing time breakdown
- Dashboard with detailed analytics
- User management capabilities
- Profile photos
- Admin features for managing other users

## Access
Once running, the application will be available at http://localhost:8501

# How to call def to another def in another class.
### To call a def to another def to another one in different class first you have to assign the class to a variable then you write the variables name then dot. After that, you write the def and the arguments which you put it in round brackets.
## Example:
class a :
def_1(self)
 print("I am def_1 from class a")


class B:
    def a(self):
        obj_a = A()         # Create object of class A
        obj_a.def_1()       # Call def_1 from class A
        print("I am def a() from class B")

# How to call a def to another def in the same class.
