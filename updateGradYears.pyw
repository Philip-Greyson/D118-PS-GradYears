"""Script to update the graduation years of students in a few places based on their current gradelevel.

This is needed because while the students.classof field is automatically updated, it does not do so while they are pre-registered with an enrollment_status of -1.
For registration purposes, we need to have a reliable field to reference knowing what grade level or what year they graduate, that will not change with the rollover.

https://github.com/Philip-Greyson/D118-PS-GradYears

Needs oracledb: pip install oracledb --upgrade
Needs the ACME PowerSchool library from https://easyregpro.com/acme.php
"""

import datetime
import json  # needed to manipulate the json objects we pass and receive from the API
import os  # needed to get environement variables

import acme_powerschool  # a library to interact with the PowerSchool REST API. Found and documented here: https://easyregpro.com/acme.php
import oracledb  # used to connect to PowerSchool database

D118_API_ID = os.environ.get("POWERSCHOOL_API_ID_2")
D118_API_SECRET = os.environ.get("POWERSCHOOL_API_SECRET_2")

DB_UN = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
DB_PW = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
DB_CS = os.environ.get('POWERSCHOOL_RES_DB')  # the IP address, port, and database name to connect to in format x.x.x.x:port/db
PS_URL = os.environ.get('POWERSCHOOL_RES_URL')  # the base URL of the PowerSchool instance, used for API calls

print(f'DBUG: DB Username: {DB_UN} | DB Password: {DB_PW} | DB Server: {DB_CS}')  # debug so we can see where oracle is trying to connect to/withPS

ENABLED_SCHOOLS = [901]  # list of school IDs that we will update the grad years of students inside

def get_school_year() -> int:
    """Return the appropriate calendar year for graduation math.

    Because school years run from July - June, we need to add 1 to the calendar year when we are in the fall, and keep it in the spring.
    We Usually roll over the school year during the first week of July, so we set the cutoff at July 7, but this can be adjusted as needed.
    This leaves us with:
    Jan 1st-July 6th: current calendar year
    July 7th-Dec 31st: calendar year + 1
    """
    today = datetime.date.today()
    year = today.year

    if today.month > 7 or (today.month == 7 and today.day >= 7):
        return year + 1
    return year

if __name__ == '__main__':  # main file execution
    with open('grad_year_log.txt', 'w') as log:
        startTime = datetime.datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
            with con.cursor() as cur:  # start an entry cursor
                ps = acme_powerschool.api(PS_URL, client_id=D118_API_ID, client_secret=D118_API_SECRET)  # create ps object via the API to do requests on

                # first get the year end of the current school year so we can calculate the grad years of the students based on their grade level
                base_year = get_school_year()
                print(f'DBUG: Base year for grad year calculations is {base_year}')  # debug log the base year we are using for calculations
                print(f'DBUG: Base year for grad year calculations is {base_year}', file=log)

                for school in ENABLED_SCHOOLS:  # loop through the schools we want to update
                    cur.execute("SELECT dcid, student_number, classof, grade_level FROM students WHERE schoolid =: school", school=school)  # get the student number, DCID, and current grad year of all students in the school
                    students = cur.fetchall()
                    for student in students:  # loop through the students we got back from the database
                        dcid = student[0]  # get the DCID of the student
                        student_number = str(int(student[1]))  # get the student number of the student
                        classof = student[2]
                        grade = int(student[3])
                        # get the current grad year fields from the API
                        result = ps.get(f'/ws/v1/student/{dcid}?expansions=demographics,school_enrollment,initial_enrollment,schedule_setup&extensions=studentcorefields')
                        # print(json.dumps(result.json(), indent=2))
                        current_grad_year = None  # initialize to None in case we dont find it for the current student
                        current_sched_grad_year = None  # initialize to None in case we dont find it for the current student

                        # get the current studentcorefields.graduation_year value
                        try:
                            studentcorefields = result.json().get('student').get('_extension_data').get('_table_extension').get('_field')
                            # print(type(studentcorefields))
                            if type(studentcorefields) is dict:  # if there is only one custom field, it will come back as a dict instead of a list, so we need to convert it to a list to loop through it
                                studentcorefields = [studentcorefields]
                            for field in studentcorefields:  # loop through the custom fields to find the grad year field
                                # print(field)
                                if field.get('name') == 'graduation_year':
                                    current_grad_year = int(field.get('value'))
                                    break  # exit the loop once we find the grad year field
                        except Exception as er:
                            print(f'WARN: Failed to get custom fields for student {student_number} with DCID {dcid} | Error: {er}')
                            print(f'WARN: Failed to get custom fields for student {student_number} with DCID {dcid} | Error: {er}', file=log)
                            # print(json.dumps(result.json(), indent=2))
                        # get the current studetns.sched_yearofgraduation value
                        try:
                            current_sched_grad_year = result.json().get('student').get('demographics').get('projected_graduation_year')
                        except Exception as er:
                            print(f'WARN: Failed to get projected graduation year for student {student_number} with DCID {dcid} | Error: {er}')
                            print(f'WARN: Failed to get projected graduation year for student {student_number} with DCID {dcid} | Error: {er}',file=log)

                        new_grad_year = 12 - grade + base_year  # calulate the grady year based on graduating in 12th grade
                        if (current_grad_year != new_grad_year) or (current_sched_grad_year != new_grad_year):  # if the grad year we got from the API is different than the one we calculated, we need to update it
                            print(f'INFO: Student {student_number} has grad year {current_grad_year} and sched grad year {current_sched_grad_year} but should be {new_grad_year}, it will be updated')  # log the change we are about to make
                            print(f'INFO: Student {student_number} has grad year {current_grad_year} and sched grad year {current_sched_grad_year} but should be {new_grad_year}, it will be updated', file=log)
                            try:
                                # construct the data object with the graduation fields to update
                                data = {
                                    'students' : {
                                        'student' : [{
                                            'id': f'{dcid}',
                                            'client_uid': f'{dcid}',
                                            'action' : 'UPDATE',
                                            '_extension_data' : {
                                                '_table_extension' : {
                                                    '_field' : [  # update the studentcorefield that has the graduation year
                                                        {
                                                            'name' : 'graduation_year',
                                                            'value' : str(new_grad_year)
                                                        }
                                                    ],
                                                    'name' : 'studentcorefields'
                                                }
                                            },
                                            'demographics' : {
                                                'projected_graduation_year' : str(new_grad_year)  # update the sched_yearofgraduation field
                                            }
                                        }]
                                    }
                                }
                                response = ps.post('/ws/v1/student', data=json.dumps(data))  # make the actual API update
                                print(response.json())
                                if response.status_code != 200:
                                    print(f'ERROR: Failed to update grad years for student {student_number} with DCID {dcid} | Status Code: {response.status_code} | Response: {response.text}')
                                    print(f'ERROR: Failed to update grad years for student {student_number} with DCID {dcid} | Status Code: {response.status_code} | Response: {response.text}', file=log)
                            except Exception as er:
                                print(f'ERROR: Failed to update grad years for student {student_number} with DCID {dcid} | Error: {er}')
                                print(f'ERROR: Failed to update grad years for student {student_number} with DCID {dcid} | Error: {er}', file=log)
                        if new_grad_year != classof:  # if the new grad year is different than the current one, we need to update it
                            print(f'WARN: Student {student_number} has classof {classof} but should be {new_grad_year}')  # just warn about which students dont have a valid classof value
                            print(f'WARN: Student {student_number} has classof {classof} but should be {new_grad_year}', file=log)
        endTime = datetime.datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
