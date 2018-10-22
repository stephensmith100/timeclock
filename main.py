from kivy.app import App

import config

import datetime
import time
import threading
import pprint

from operator import itemgetter
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from kivy.storage.jsonstore import JsonStore
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import ObjectProperty, StringProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.popup import Popup

# Helper Functions

pp = pprint.PrettyPrinter(indent=4)

# String to Boolean
def str2bool(s):
    return s.lower() in ['true', 'yes']

# Boolean to String
def bool2str(b):
    if b:
        return "TRUE"
    else:
        return "FALSE"

# Weekday Array
Weekday = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Column Array
col = {'employeeNo' : 'A' ,'name' : 'B' ,'surname' : 'C' ,'active' : 'D' ,'signedIn' : 'E' ,'timeIn' : 'F' ,'timeOut' : 'G', 'normalHours' : 'H' }

# Employee Popup
class EmployeePopup(Popup):
    # POPUP for displaying the controls for the employee sign in or sign out.
    greeting = StringProperty()
    message = StringProperty()

    def __init__(self, employee, **kwargs):
        self.employee = employee
        if self.employee.signedIn:
            self.greeting = "Goodbye, {} {}.".format(self.employee.name, self.employee.surname)
            self.message = "Do you want to SIGN OUT? You signed in at " + self.employee.time_in_string
        else:
            self.greeting = "Hello, {} {}.".format(self.employee.name, self.employee.surname)
            self.message = "Do you want to SIGN IN?"
        super(EmployeePopup, self).__init__(**kwargs)

    def logEmployee(self):
        self.dismiss()
        if (self.employee.signedIn):
            self.employee.save_logout(self.employee)
        else:
            self.employee.save_login(self.employee)
       

# Employee List
class EmployeeList(RecycleView):

    googleFile = "Employee Data"
    dirtyRecords = []
    threadRunning = False


    def __init__(self, **kwargs):
        # Get employee details from google and populate the app. If unable to connect,
        # get the details from local storage.
        # TODO: Check that the last saved version from google is the same as the local storage.
        
        super(EmployeeList, self).__init__(**kwargs)
        connected = True
        employees = []
        failedAttempts = 0

        # Try to open the google worksheet to load employee data.
        try:
            employeeSheet = self.get_google_sheet(config.GOOGLE_CONFIG['employeeSheet'])
        except:
            print "Error connecting to the google server"
            connected = False
        if connected:
            # Get employees from google and sort into alphabetical order (by Surname)
            employeeImport = employeeSheet.get_all_records()

            # Create local storage for the employees
            store = JsonStore('employees.json')
            for e in store:
                store.delete(e)

            for e in employeeImport :
                # Convert yes/no fields to bool. Remove inactive users.
                e['active'] = str2bool(e['active'])
                if e['active']:
                    e['signedIn'] = str2bool(e['signedIn'])
                    # Add employee to local storage.
                    store.put(
                        e['employeeNo'], 
                        name=e['name'],
                        surname=e['surname'],
                        signedIn=e['signedIn'],
                        timeIn=e['timeIn'],
                        timeOut=e['timeOut']
                    )
                    # Convert time string to datetime objects
                    if e['timeIn'] != "":
                        e['timeIn'] = datetime.datetime.strptime(e['timeIn'], "%Y-%m-%d %X")
                    if e['timeOut'] != "":
                        e['timeOut'] = datetime.datetime.strptime(e['timeOut'], "%Y-%m-%d %X")
                    
                    # Create the data clean element
                    e['clean'] = True
                    
                    # Add record to the employees
                    employees.append(e)
                else:
                    # If the employee is inactive, remove from the list.
                    # employees.remove(e)
                    print "{} {} is DELETED".format(e['name'], e['surname'])
        else:
            # If unable to connect to google server, connect to local. 
            print('Failed to connect to Google Server')

            store = JsonStore('employees.json')
            for e in store:
                # Check and convert time
                if store.get(e)['timeIn'] != "":
                    timeInString = datetime.datetime.strptime(store.get(e)['timeIn'], "%Y-%m-%d %X")
                else:
                    timeInString = ""
                if store.get(e)['timeOut'] != "":
                    timeOutString = datetime.datetime.strptime(store.get(e)['timeOut'], "%Y-%m-%d %X")
                else:
                    timeOutString = ""
                # Generate entry
                entry = {
                    'employeeNo': e,
                    'name': store.get(e)['name'],
                    'surname': store.get(e)['surname'],
                    'signedIn': store.get(e)['signedIn'],
                    'timeIn': timeInString,
                    'timeOut': timeOutString,
                }
                employees.append(entry)

        # Sort employee and set data 
        self.data = sorted(employees, key=itemgetter('surname'))

    # Log employee In
    def log_employee_in(self, employee):
        self.data[employee]['signedIn'] = True
        self.data[employee]['timeIn'] = datetime.datetime.now()
        self.data[employee]['timeOut'] = {}

        self.refresh_from_data()
        # Save data
        # Connect to store
        store = JsonStore('employees.json')
        record = str(self.data[employee]['employeeNo'])

        timeIn = self.data[employee]['timeIn'].strftime("%Y-%m-%d %X")
        timeOut = ""
        signedIn = True

        if store.exists(record):
            # store[record]['timeIn'] = str(self.data[employee]['timeIn'])
            store[record]['timeIn'] = timeIn
            store[record]['timeOut'] = timeOut
            store[record]['signedIn'] = signedIn
            store[record] = store[record]
            
        else:
            print "Unable to connect to local storage"
        
        # Create a dirty flag
        dirtyFlag = {
            'index': employee,
            'employeeNo': record,
            'signedIn' : signedIn,
            'timeIn' : timeIn,
            'timeOut' : timeOut
        }
        
        # Mark the record as dirty so that it is uploaded to the Google servers.
        # Do not add if already waiting for upload.
        if dirtyFlag not in self.dirtyRecords:
            self.dirtyRecords.append(dirtyFlag)

        print str(len(self.dirtyRecords))
        

    # Log employee Out
    def log_employee_out(self, employee):
        self.data[employee]['signedIn'] = False
        self.data[employee]['timeOut'] = datetime.datetime.now()

        #pp.pprint(self.data)
        self.refresh_from_data()

        # Connect to jsonstore
        store = JsonStore('employees.json')
        # # Check if the record exists
        record = str(self.data[employee]['employeeNo'])
        timeIn = self.data[employee]['timeIn'].strftime("%Y-%m-%d %X")
        timeOut = self.data[employee]['timeOut'].strftime("%Y-%m-%d %X")
        signedIn = False

        if store.exists(record):
            store[record]['timeOut'] = self.data[employee]['timeOut'].strftime("%Y-%m-%d %X")
            store[record]['signedIn'] = False

            store[record] = store[record]
        else:
            print "Unable to connect to local storage"

        # Create a dirty flag
        dirtyFlag = {
            'index': employee,
            'employeeNo': record,
            'signedIn' : signedIn,
            'timeIn' : timeIn,
            'timeOut' : timeOut
        }
        
        # Mark the record as dirty so that it is uploaded to the Google servers.
        # Do not add if already waiting for upload.
        if dirtyFlag not in self.dirtyRecords:
            self.dirtyRecords.append(dirtyFlag)

        print self.dirtyRecords
        print str(len(self.dirtyRecords))

    # GOOGLE SHEET FUNCTIONS
    # ----------------------
    
    # Connect to google sheet
    def get_google_sheet(self, worksheetName):
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.GOOGLE_CONFIG['clientSecretFile'], scope)
        client = gspread.authorize(creds)
        sheet = client.open(config.GOOGLE_CONFIG['fileName']).worksheet(worksheetName)
        return sheet

    # Update employee list

    def update_employee_list(self):
        # Check to see if there are any records that need updating
        if len(self.dirtyRecords) > 0 and not self.threadRunning:
            self.threadRunning = True
            print "Thread running"
            # Get first record from the list
            employee = self.dirtyRecords.pop(0)

            # Get record data for the employee
            employeeNo = employee['employeeNo']
            state = employee['signedIn']
            timeIn = employee['timeIn']
            timeOut = employee['timeOut']

            print "Updating Data for Employee: {}, Time In: {}, Time Out: {}.".format(employeeNo, timeIn, timeOut)
            try:
                sheet = self.get_google_sheet(config.GOOGLE_CONFIG['employeeSheet'])
                e = sheet.find(str(employeeNo))
                pp.pprint(employeeNo)
                # Update SignedIn state
                print str(state)
                sheet.update_acell(col['signedIn'] + str(e.row), bool2str(state))
                # Update timeIn state
                print timeIn
                sheet.update_acell(col['timeIn'] + str(e.row), str(timeIn))
                # Update timeOut state
                print timeOut
                sheet.update_acell(col['timeOut'] + str(e.row), str(timeOut))
            except:
                print "Unable to connect with Google Employee Sheet"
               
               
            # Check if the record is a complete record with signIn and signOut
            if timeOut:

                # Add the record to the Google Sheet
                try:
                    print "Trying to upload"
                    hoursSheet = self.get_google_sheet(config.GOOGLE_CONFIG['hoursSheet'])
                    hoursSheet.append_row([str(employeeNo), str(timeIn), str(timeOut)])
                except:
                    "Unable to connect with Google Hours Sheet"
                    if employee not in self.dirtyRecords:
                        self.dirtyRecords.append(employee)
                else:
                    print "Upload successful."

            self.threadRunning = False
            print "Thread Ending"
            

            
   

# Employee View
class EmployeeView(RecycleDataViewBehavior, BoxLayout):
    index = None
    employeeNo = ObjectProperty()
    name = StringProperty()
    surname = StringProperty()
    active = BooleanProperty()
    signedIn = BooleanProperty()
    timeIn = ObjectProperty()
    timeOut= ObjectProperty()
    normalHours = ObjectProperty()
    time_in_string = StringProperty()
    time_out_string = StringProperty()
    clean = BooleanProperty()

    pressed = BooleanProperty()

    def __init__(self, **kwargs):
        super(EmployeeView, self).__init__(**kwargs)
        self.pressed = False
        # Functions for calculating the string version of the time variables
        self.bind(timeIn=self.get_time_in_string)
        self.bind(timeOut=self.get_time_out_string)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        self.data = data
        return super(EmployeeView, self).refresh_view_attrs(
            rv, index, data)
            
    def get_time_out_string(self, instance, value):
        # Function bound to the timeOut variable to automatically calculate string
        #DEBUG print "Recalculated time out string"
        if isinstance(self.timeOut, datetime.datetime):
            self.time_out_string = self.timeOut.strftime("%H:%M")
            self.data['timeOut'] = self.timeOut
        else:
            self.data['timeOut'] = {}
            self.time_out_string = "N/A"

    def get_time_in_string(self, instance, value):
        # Function bound to the timeIn variable to automatically calculate string.
        #DEBUG print "Recalculated time in string"
        if isinstance(self.timeIn, datetime.datetime):
            self.time_in_string = self.timeIn.strftime("%H:%M")
            self.data['timeIn'] = self.timeIn
        else:
            self.data['timeIn'] = {}
            self.time_in_string = "N/A"

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.pressed = True

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):

            self.pressed = False
            popup = EmployeePopup(self)
            popup.open()
    
    def save_login(self, employee):
        # Pass action to the EmployeeList class
        self.parent.parent.log_employee_in(self.index)

    def save_logout(self, employee):
        # Pass action to the EmployeeList class
        self.parent.parent.log_employee_out(self.index)

def getDayOfWeek(dateString):
    t1 = time.strptime(dateString, "%m/%d/%Y")
    t2 = time.mktime(t1)
    return (time.localtime(t2)[6])

class ClockWidget(BoxLayout):
    uxTime = StringProperty('')
    uxSeconds = StringProperty('')
    uxDate = StringProperty('')
    uxDay = StringProperty('')

    def update(self, dt):
        self.uxTime = time.strftime("%H:%M", time.localtime())
        self.uxSeconds = time.strftime("%S", time.localtime())
        self.uxDate = time.strftime("%d %B %Y", time.localtime())
        self.uxDay = Weekday[getDayOfWeek(time.strftime("%m/%d/%Y", time.localtime()))]
        # Update the Employee List
        employeeList = App.get_running_app().employeeList
        threading.Thread(target=employeeList.update_employee_list).start()


class TimeApp(App):

    employeeList = EmployeeList()

    def build(self):
        clockWidget = ClockWidget()
        Clock.schedule_interval(clockWidget.update, 1)
        return clockWidget

if __name__ == '__main__':
    TimeApp().run()
