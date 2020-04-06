# MobilitySystems
Optimized Route Modelling and User Choice Modelling for Mobility as a Service Packages

The procedure to run these programs consist of the following steps:
1. Creating the database from the csv data files downloaded from this site: 
2. Creating a sqlite3 database from these files where each file is a table
3. Running the file runEntireNetwork.py to create the gpickle file after scanning through every route from the sqlite database.

Since we have already run this program, which will take around 16 hours to finish, we have also uploaded the final gpickle file in the github, which is called "networkBerlinNew.gpickle" 

For getting the results of optimization we only have to carry out the following steps.

4. Optimized routes for each package have to be run separately, through the following files respectively for each package:
	PAYG Package    - PAYGSelectionFinal.py
	Weekly Package  - WeeklySelectionFinalUpdated.py
	Monthly Package - MonthlySelectionFinal.py

5. When running for PAYG, these are the variables that need to be edited:
	- In the file PAYGSelectionFinal.py:
		- The variable "directory" should specify the directory in which you would like your final output file to be saved in. 
		- In this line "nx.read_gpickle" the location of the gpickle file should be given correctly.
	- In the file getData.py:
		-In the method "getUserPAYGTripsDetails", the location for the input file should be given based on the user for which you would like to run the route optimization process.

6. Similarly when runnning for Weekly Package, these are the variables that needs to be edited:
	- In the file WeeklySelectionFinalUpdated.py:
		- The variable "directory" should specify the directory in which you would like your final output file to be saved in.
		- In this line "nx.read_gpickle" the location of the gpickle file should be given correctly.
	- In the file getData.py:
		- In the method "getUserWeeklyTripDetails", the location for the input file should be given based on the user for which you would like to run the route optimization process.

7. Now for the Monthly Package, these are the variables that needs to be edited:
	- In the file MonthlySelectionFinal.py:
		- The variable "directory" should specify the directory in which you would like your final output file to be saved in.
		- In this line "nx.read_gpickle" the location of the gpickle file should be given correctly.	
	- In the file getData.py:
		- In the method "getUserMonthlyTripDetails", the location for the input file should be given based on the user for which you would like to run the route optimization process.

8. Finally after getting all these results, they can be put in one single folder, and then the file "PackageSelection.py" can be run to choose the final package that will be most cost effecient for the user. 
	- In the variable "directory", the folder location has to be edited and saved according to where the previous result files are located.
	- The variable "user" should have the name of the user for which we are running the program. 
