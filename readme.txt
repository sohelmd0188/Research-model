H2 Dashboard — Design A (Updated)

Contents:
- H2app.py                   : Streamlit app (main)
- requirements.txt           : Python dependencies
- readme.txt                 : This file
- design_preview_updated.png : Static design mockup image

How to run (offline, after extracting to a local folder):
1. Ensure Python 3.8+ is installed and added to PATH.
2. Open Command Prompt and navigate to the folder:
   cd "C:\Users\<your-user>\Downloads\H2model"
3. (Optional) Create and activate a virtual environment:
   python -m venv venv
   venv\Scripts\activate
4. Install dependencies:
   pip install -r requirements.txt
5. Run the app:
   streamlit run H2app.py
6. The dashboard opens at http://localhost:8501

2nd optioon:

Quick run steps (copy-paste)
Download the .zip files and extract it to download folder. 
Extract ZIP into e.g ( "C:\Users\Sohel pc\Downloads\H2model" ) (or your preferred folder).

Open Command Prompt and run:
cd "C:\Users\Sohel pc\Downloads\H2model"
pip install -r requirements.txt
streamlit run H2app.py

Dashboard will open in your browser at http://localhost:8501.

Notes about this updated version:
- All energy values are in MWh (converted from kWh).
- Default Solar = 80 MWh (editable in the sidebar).
- Grid Import = max(0, Demand - Solar)  (units: MWh)
- Grid Export = max(0, Solar - Demand)  (units: MWh)
- All Tk values are converted to USD using the exchange rate (editable in sidebar).
- Monthly selector available to show details of a single month.
- The "Cumulative cashflow (USD, last month)" metric was removed as requested.
