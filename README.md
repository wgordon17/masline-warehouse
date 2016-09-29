# Environment

The intended environment for this application is either Linux or Windows hosting the application, with a Microsoft
SQL Server installed and configured to be accessible by ODBC. For this sample, some of the SQL has been rewritten
to access a locally included SQLite database; however, the database still needs to be accessible via ODBC.

## System Requirements

+ Python 3.5
+ Tornado package
+ PyODBC package
+ SQLite ODBC Drivers

----

+ This document assumes that git is installed locally
+ Clone the project from GitHub:

  >     git clone https://github.com/wgordon17/masline-warehouse.git

### Ubunutu Hosts

> **NOTE:** This works best on Ubuntu based on easy access to SQLite ODBC driver; however, 
this application runs easily on any properly configured linux server 

+ Install the necessary packages provided by the default package manager:

  >     sudo apt install unixodbc-dev python3-dev python3-venv python3-pip libsqliteodbc
  
+ Create a virtual environment:

  >     pyvenv masline-warehouse/warehouse-env
  
+ Activate the virtual environment:

  >     source masline-warehouse/warehouse-env/bin/activate
  
+ Install required packages:

  >     pip install -r masline-warehouse/requirements.txt
  
### Windows Hosts

Continuum's Anaconda python install provides the easiest method for getting this application running on Windows.

+ Install Miniconda for Python 3.5 from http://conda.pydata.org/miniconda.html
+ Download and install SQLite ODBC drivers for windows from http://www.ch-werner.de/sqliteodbc/
+ Create a virtual environment:

  >     conda create -n warehouse-env
  
+ Activate the virtual environment:

  >     activate warehouse-env
  
+ Install required packages:

  >     pip install -r masline-warehouse/requirements.txt

# Running the application

## Ubunutu Hosts

+ Activate the virtual environment:
  >     source masline-warehouse/warehouse-env/bin/activate
+ Start the application:
  >     python masline-warehouse/application.py
  
## Windows Hosts

+ Activate the virtual environment:

  >     activate warehouse-env
  
+ Start the application:

  >     python masline-warehouse/application.py

# Navigating the web application

+ The default port in settings.py is 9000
  + You can confirm the current port by viewing the logging output
  
    > :INFO     - Server listening at port #### - controller.run_server(25)
  
+ Navigate to the page `http://127.0.0.1:9000`<sub>This assumes default settings and locally running application</sub>
+ The application automatically redirects to `/login`, and prompts for a password
  + This application is intended to run without a keyboard interface, 
  and instead uses a bluetooth barcode scanner as a keyboard wedge
  + It's possible to simulate scanning a barcode by typing the output normally and hitting <kbd>Enter</kbd>
+ This application sample has been pre-programmed with two users
  + Will: password `1234`
  + John: password `5678`
+ Once authenticated, there are two avenues of operation:
  + Starting with a picking ticket
    + "Scan" the picking ticket with Shipment# `123456`
      + This can be simluated by typing `123456` and hitting <kbd>Enter</kbd></sub>
    + If the screen is not large enough to show all items on the ticket, you can page between screens by long pressing the shown arrows
      + This can be simluated by right-clicking the arrows
    + Tapping/clicking on an Item button will display item information, lots and images, and allow the user to confirm picked amount
  + Starting with a lot number
    + "Scan" the lot barcode with Lot# `5001`
    + Tap/click/scan on the lot that's being picked
    + Confirm the quantity being picked from the location
      + The top row of numbers provides additive counting
      + The bottom row of numbers behaves like a keyboard and allows for direct entry
      + Click `Done` to confirm the lot has been picked
  + Once lots have been picked, they are no longer available to be picked and are displayed green on the Item screen
  + Once lots have been picked, their location is crossed through on the Shipment screen to illustrate that location is done
  + Once all lots for an item on any particular shipment have been picked, that entire Item button displays as green
      
# What I would do differently

This project was a great opportunity to learn new technologies, as well as push my understanding and grasp on asynchronous
processing. If it were available, I would definitely not have interfaced with a Microsoft SQL Server, but it was the ERP requirement.
Also, I would utilize more frameworks; at the time, Django did not work well with websockets, however with the inclusion of
Channels in their official repository, it would be a great way to go. Utilizing a more decoupled REST API, with a front end
framework would also have simplified the workflow.

Also, this architecture was designed to be extensible; however, with time constraints, my manager deemed this "good enough" 
and I didn't have the opporunity to build in more functionality. I would have definitely enjoyed building more warehousing
capabilities into it.
