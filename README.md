
# D118-PS-GradYears

Script to automatically update graduation year fields for students based on their current grade level in PowerSchool.

## Overview

This script is designed to keep graduation year fields accurate for all students, particularly those who are pre-registered with an enrollment status of -1. While PowerSchool automatically updates the `students.classof` field during normal operations, it does not update this field for pre-registered students. For registration and planning purposes, having reliable graduation year fields that won't change unexpectedly during rollover is essential.

The script calculates the expected graduation year based on each student's current grade level (assuming graduation occurs at the end of 12th grade) and the current school year. It then compares this calculated value against two fields:

1. `studentcorefields.graduation_year` - The main graduation year field in the studentcorefields extension table - this is what shows on the demographics page.
2. `students.sched_yearofgraduation` (also known as `projected_graduation_year` in the API) - A core demographics field

If either field doesn't match the calculated graduation year, the script updates both fields via the PowerSchool API to ensure consistency.

The script processes one or more schools (configurable) and for each school it:

1. Connects to the PowerSchool database to retrieve all students at that school
2. Calculates the appropriate graduation year based on the current school year and each student's grade level
3. Retrieves the current values of both graduation year fields via the API
4. Compares the current values to the calculated value
5. Updates both fields via the API if they don't match
6. Logs a warning if the `students.classof` field is also incorrect (though it does not update this field as it *should* be automatic)

## Requirements

The following are required for the script to function:

- The following environment variables must be set on the machine running the script. These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool, as well as the plugin API credentials. Note that this script uses `POWERSCHOOL_PROD_DB` and `POWERSCHOOL_PROD_URL` which may point to either your production or resource (test/dev) PowerSchool instance depending on your naming convention. If you wish to directly edit the script and include these credentials, you can:
  - POWERSCHOOL_API_ID_2
  - POWERSCHOOL_API_SECRET_2
  - POWERSCHOOL_READ_USER
  - POWERSCHOOL_DB_PASSWORD
  - POWERSCHOOL_PROD_DB
  - POWERSCHOOL_PROD_URL

- As this script uses the PowerSchool API, you must have a plugin installed that gives you access to the API endpoints. This plugin is where you get the API ID and API secret that are included in the environment variables above.
  - In the plugin.xml file included inside the plugin, the following fields are required to be able to write to the graduation fields
    - `<field table="STUDENTCOREFIELDS" field="GRADUATION_YEAR" access="FullAccess" />`
    - `<field table="STUDENTS" field="SCHED_YEAROFGRADUATION" access="FullAccess" />`

- The following Python modules installed (links to installation guides below):
  - [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)
  - [ACME PowerSchool Python Library](https://easyregpro.com/acme.php)

## Customization

While fairly simple, the script will need to be customized for use in your specific district. The following items can and should be customized:

### Constants

- `ENABLED_SCHOOLS` - List of school IDs to process. Set this to the school numbers you want to run the script for. Example: `[901, 902, 903]` for multiple schools or `[901]` for a single school. The script will process all students at these schools regardless of enrollment status.

### School Year Calculation

The `get_school_year()` function determines what year to use as the base for graduation calculations. Because school years run from July through June of the following year, the function needs to account for whether you're before or after new years, since the graduation will happen in the spring of the later calendar year of a given school year.

The current logic assumes school rollover happens during the first week of July:

- January 1-July 6: Uses the current calendar year
- July 7-December 31: Uses the current calendar year + 1

For example, on March 15, 2025 (during the spring of the 2024-2025 school year), it returns 2025. On August 1, 2025 (the fall of the 2025-2026 school year), it returns 2026.

If your district rolls over at a different time - and the grade_level values will change, you should update the logic to modify the cutoff date in the function:

```python
if today.month > 8 or (today.month == 8 and today.day >= 15):  # Rollover on August 15
    return year + 1
return year
```

### Graduation Grade Level

The script assumes students graduate at the end of 12th grade. The calculation is:

```python
new_grad_year = 12 - grade + base_year
```

If your district has a different graduation grade level (e.g., some alternative schools graduate at grade 13), modify this calculation:

```python
new_grad_year = 13 - grade + base_year  # For grade 13 graduation
```
