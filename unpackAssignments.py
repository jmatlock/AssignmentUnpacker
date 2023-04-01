"""
unpackAssignments
Mar 17, 2021
Jim Matlock

This Python script will take an assignment zip file from Blackboard and
unzip it into appropriate student-named directories based on the names
of the files within the zip archive.

The names of the files inside the zip are assumed to have the following
format:

<Assignment Name>_<StudentID>_attempt_<timestamp>_<submitted file name>

With this format, the script will perform the separation creating a top
level <Assignment Name> directory that contains multiple <StudentID>
directories which contain the appropriate <submitted file name> files.

Additionally, if a feedback.txt file is provided, that will be copied into
each student directory. Otherwise, a blank feedback.txt file is created.
"""

# Features under consideration
# TODO: Create a GUI interface
# TODO: Add an option for just getting updated submissions from a zip
# TODO: Add incorrect file name flagging
# TODO: Add an option to only update feedback files

import argparse
import os
from string import Template
from zipfile import ZipFile
from datetime import datetime


def copy_feedback_file(student, feedback, feedback_filename):
    # Get student name from attempt file
    student_filelist = os.listdir(f'{student}')
    attempt_filename = ''
    for filename in student_filelist:
        if filename.find('attempt') != -1:
            attempt_filename = os.path.join(f'{student}', f'{filename}')
            break
    student_name = ''
    with open(attempt_filename, 'r') as attempt_file:
        name_line = attempt_file.readline().strip()
        student_name = name_line.replace('Name: ', '')
    if feedback:  # Feedback file was supplied, copy it
        # Substitute $student_name in template
        feedback_template = Template(feedback)
        updated_template = feedback_template.substitute(
            student_name=student_name)
        # Write file
        with open(f'{student}/{student}-{feedback_filename}',
                  'w') as custom_feedback:
            custom_feedback.write(updated_template)
    else:  # No supplied feedback file, creating one customized for student
        title_string = f'==  Feedback for {student_name}  =='
        with open(f'{student}/feedback.txt', 'a') as f:
            f.write('=' * len(title_string) + '\n')
            f.write(title_string + '\n')
            f.write('=' * len(title_string) + '\n')


def process_zipfile(destdir, zipfile):
    # print(f'Zipfile found for {destdir}: {zipfile}')
    with ZipFile(zipfile) as z:
        infolist = z.infolist()
        for info in infolist:
            # Exclude directories which don't include student files
            if '.idea' in info.filename or 'venv' in info.filename \
                    or '__MACOSX' in info.filename:
                continue
            z.extract(info, path=destdir)
            # print(f'In {z.filename}: {info.filename}')


def get_dt_submitted(student, timestamp_dict):
    timestamp = timestamp_dict[student]
    dt_timestamp = datetime.strptime(timestamp, '%Y-%m-%d-%H-%M-%S')
    return dt_timestamp


def get_dt_submitted_str(student, timestamp_dict):
    dt_timestamp = get_dt_submitted(student, timestamp_dict)
    return dt_timestamp.strftime('%a %b %d, %I:%M %p')


def main():
    parser = argparse.ArgumentParser(
        description='Unpack submissions from Blackboard gradebook zip file '
                    'and provide feedback file')
    parser.add_argument('infile', metavar='zip-filename',
                        help='zip file from Blackboard')
    parser.add_argument('-f', '--feedback', metavar='feedback-filename',
                        nargs='?', type=str, help='use feedback template')
    parser.add_argument('-np', '--noprefix', action='store_true',
                        help='no section name prefix on created folder')
    parser.add_argument('-px', '--postfix',
                        help='add postfix to created folder')
    parser.add_argument('-eg', '--earlygrade',
                        help='add postfix "EG" to students who submit before date (mm-dd-yyyy)')

    args = parser.parse_args()

    if not (os.path.isfile(args.infile)):
        print(f'File not found: {args.infile}')
        exit(1)
    elif args.feedback and not (os.path.isfile(args.feedback)):
        print(f'File not found: {args.feedback}')
        exit(1)

    feedback_template = None
    if args.feedback:
        with open(args.feedback, 'r') as feedback_file:
            feedback_template = feedback_file.read()

    prefix = ''
    if not args.noprefix:
        # prefix = args.prefix + '-'
        prefix = args.infile.split('_')[1].split('.')[3] + '-'

    postfix = ''
    if args.postfix:
        # prefix = args.prefix + '-'
        postfix = '-' + args.postfix

    earlygrade = None
    if args.earlygrade:
        try:
            earlygrade = datetime.strptime(args.earlygrade, '%m-%d-%Y')
        except ValueError:
            print(f'Could not parse provided date {args.earlygrade}')
            print('Format expected: mm-dd-yyyy')
            exit(-1)
        args.postfix = 'EG'
        postfix = '-' + args.postfix

    assignment = None
    student_list = []
    timestamp_dict = {}
    # Currently this dictionary is unused, but I'm keeping it
    # in place in case it is useful for additional features.
    # This dictionary will be populated with { studentid : [file1, ...], ...}
    student_files = {}
    file_count = 0

    with ZipFile(args.infile) as bb_zip:
        files = bb_zip.infolist()
        # first get assignment name and create directory
        if len(files) > 0:
            fname = files[0].filename
            assignment = fname.split('_')[0]
            group_dir = prefix + assignment + postfix
            # If directory already exists, move it to a backup
            if os.path.exists(group_dir):
                os.rename(group_dir, group_dir + '-backup')
            os.makedirs(group_dir)
            os.chdir(group_dir)
        for file in files:
            fname = file.filename
            parts = fname.split('_')
            student = parts[1]
            timestamp = parts[3]
            if parts[1] not in student_list:
                student_list.append(student)
                timestamp_dict[student] = timestamp
                os.makedirs(student)
                student_files[student] = []
            bb_zip.extract(file, student)
            new_fname = fname.replace(
                assignment + '_' + student + '_attempt_' + timestamp + '_', '')
            if new_fname == '.txt':
                new_fname = 'attempt_' + timestamp + new_fname
            os.rename(student + '/' + fname, student + '/' + new_fname)
            student_files[student].append(new_fname)
            # print(f'Student: {student}, file: {new_fname}')
            if new_fname[-4:] == '.zip':  # Zip file inside original zip file
                process_zipfile(student + '/' + new_fname[:-4],
                                student + '/' + new_fname)
                os.remove(student + '/' + new_fname)  # Remove inner zip
            file_count += 1
    for student in student_list:
        copy_feedback_file(student, feedback_template, args.feedback)

    # Create text file with students who submitted assignment
    student_file_name = 'students-' + assignment.replace(' ', '') + '.txt'
    counter = 0
    with open(student_file_name, 'w') as student_file:
        prefix = prefix.rstrip('-')
        header = assignment + ' - ' + prefix
        student_file.write(f'{header}\n')
        student_file.write((len(header) * '-') + '\n')
        student_list.sort()
        for student in student_list:
            if counter % 10 == 0 and counter != 0:
                student_file.write('-\n')
            if earlygrade:
                if earlygrade > get_dt_submitted(student, timestamp_dict):
                    student_file.write(f'{student} (EG)\n')
                else:
                    student_file.write(f'{student}\n')
            else:
                student_file.write(
                    f'{get_dt_submitted_str(student, timestamp_dict)}: {student}\n')
            counter += 1

    print(f'Assignment: {assignment}')
    print(f"{file_count} files extracted for {len(student_list)} students")


if __name__ == '__main__':
    main()
