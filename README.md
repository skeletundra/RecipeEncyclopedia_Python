# SDEV265_Project
Installation Instructions
The following instructions provide the necessary steps to install, configure, and execute the Recipe Encyclopedia software solution on your local machine.

Prerequisites
Before installing the recipe encyclopedia, ensure your system meets the following prerequisites:

Operating System: Windows 10/11 OR macOS
Python Environment: Python 3.11 or higher must be installed on the system. You can verify your python installation by opening the terminal or command prompt and typing python --version.

Step 1: Install Required Dependencies
The Recipe Encyclopedia relies on modern UI and image-processing libraries. Open the terminal or command prompt and execute the following command to install the required python packages: pip install customtkinter pillow 

Step 2: Download the Project Files
Download the provided .zip file containing the project source code, or clone the repository directly from GitHub. 
Extract the contents of the folder to an easily accessible location on your computer.
Ensure that the main executable file is present in the root directory of the extracted folder.

Step 3: Launching the Application
Open your computer’s file explorer and navigate to the folder where you extracted the project.
Double-click the main.py file to launch the application.
(Note: If double-clicking does not work due to your computer’s default file associations, you can right-click the file and select ‘Open With…’, and select Python.)

Step 4: First-Run Configuration
Upon running the software for the very first time, you may notice a brief pause. During the initial launch, the software is automatically building a localized environment. It will:
-Generate a local recipes/ folder in the same directory as your python script.
-Create a placeholder.png image asset.
-Generate a local recipes.db SQLite database file
-Populate your database and folder with basic tags and an example recipe.

From this point forward, you may additionally utilize the ‘Manage Recipes’ and ‘Manage tags’ buttons located at the top of the application to begin building a personalized offline cookbook. Additional instructions are included on the landing page.
