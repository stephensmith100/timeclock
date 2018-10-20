# Python Clocking In Software for Raspberry Pi
This is a very basic piece of software for logging people in and out of a workplace. It is designed to work on a Raspberry Pi using Kivy and Gspread to take a list of employees from a Google Sheet and log their IN and OUT time to the same spreadsheet.

## Requirements:
- Kivy
- Gspread

## Setup
The sample-config.py file must be filled in with the appropriate details:

- 'clientSecretFile'  : The name of the google authentication file.
- 'fileName'          : Name of the Google spreadsheet file.
- 'employeeSheet'     : Name of the sheet containing employee names.
- 'hoursSheet'        : Name of the sheet to log in and log out times.

Change name of file to config.py

## Google Spreadsheet
Add a google spreadsheet with the following structure:

### Spreadsheet Structure
The google spreadsheet needs to comprise of two sheets: One for storing the employee names and one for storing the hours worked. The sheets can be given any name you wish as long as you define them in the config.py file.

#### Sheet 1 - Employees
The first sheet must be filled out with the following column heading and names of the people.
- Column A - employeeNo (Int 1, 2, 4, etc)
- Column B - name
- Column C - surname
- Column D - active (bool)
- Column E - signedIn (bool)
- Column F - timeIn
- Column G - timeOut
- Column H - normalHours (employees normal daily working hours)

#### Sheet 2 - Hours
This sheet will automatically be populated by the program.
- Column A - employeeNo
- Column B - dateTimeIn
- Column C - dateTimeOut

### Setup Google Access
Follow gspread instructions for setting up authenticated access to your spreadsheet.
https://gspread.readthedocs.io/en/latest/oauth2.html#oauth-credentials