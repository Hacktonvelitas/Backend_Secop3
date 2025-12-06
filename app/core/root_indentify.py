import sys
import os
 
 
def get_abs_path():
 path = os.path.abspath(__file__)
 return path[:path.find("Backend_Secop3")]
 
 
def basic_setup():
 path = os.path.dirname(get_abs_path())
 sys.path.append(path)
 
 
basic_setup()