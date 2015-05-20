Before running any of the .py applications make sure:
1. Change admin_config.ini
    1.1. Specify storage root directory
    1.2. Specify configuration root directory
2. Make sure config directory is in same place as specified in admin_config.ini
3. Make sure all the required configuration files are inside the specified config directory
4. Make sure powerdiff.ini is in place before running power_diff.py
5. pue_calculator can be run with the argument in console in a format YYYY/M/DD of which the PUE should be calculated
6. If no arguments passed when running pue_calculator make sure you've specified the date of which the PUE should be calculated in getDate() function
