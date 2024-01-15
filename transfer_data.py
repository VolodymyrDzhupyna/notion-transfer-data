from notion_client import Client
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import *
import gspread
import json
import notion_config
import time
import os
import logging
from datetime import datetime


logging.basicConfig(filename='app.log', 
                    filemode='a', 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO
                )

# google Sheets API credentials
link = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google_config.json', link)
google_client = gspread.authorize(creds)

# notion API credentials
notion_client = Client(auth=notion_config.secret['api_key'])
database_id = notion_config.secret['database_id']

# open Google sheet and worksheet
sheet = google_client.open('My_test_table')
worksheet = sheet.get_worksheet(0)


def write_data_as_json(content, file_name):
    # if the file exists, read its contents
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            existing_content = json.load(f)
    else:
        existing_content = []

    # create a dictionary to quickly search for records by record_id
    existing_content_dict = {item['record_id']: item for item in existing_content}

    # combine existing content with new content
    for item in content:
        if item['record_id'] in existing_content_dict:
            # update an existing record
            existing_content_dict[item['record_id']].update(item)
        else:
            # add a new record
            existing_content.append(item)

    content_as_json_str = json.dumps(existing_content, indent=2)
    decoded_content = content_as_json_str.encode('utf-8').decode('unicode_escape')
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(decoded_content)


def get_nested_value(data, dot_chained_keys):
    '''
        {'a': {'b': [{'c': 1}]}}
        get_nested_value(data, 'a.b.0.c') -> 1
    '''
    keys = dot_chained_keys.split('.')
    for key in keys:
        try:
            if isinstance(data, list):
                data = data[int(key)]
            else:
                data = data[key]
        except (KeyError, TypeError, IndexError):
            return None
    return data


def check_headers(worksheet, headers):
    first_row = worksheet.row_values(5)
    for header in headers:
        if header not in first_row:
            return False
    return True


def update_google_sheets(changes):
    # get the existing data from the Google Sheet
    all_data = worksheet.get_all_values()
    existing_data = [row[0:8] for row in all_data[5:]]

    for row in changes['modified']:
        time.sleep(2)
        values = [
            row['record_id'], row['comment'], 
            row['work_time_start'], row['work_time_end'],
            row['owner'], row['hours'], 
            row['count_acc'], row['task']
        ]
        # check if the row already exists in the Google Sheet
        for i, existing_row in enumerate(existing_data):
            if existing_row[0] == row['record_id']:
                # update the existing row
                cell_range = f'A{i+6}:H{i+6}'
                worksheet.update(cell_range, [values])
                break

    for row in changes['new']:
        time.sleep(1)
        values = [
            row['record_id'], row['comment'], 
            row['work_time_start'], row['work_time_end'],
            row['owner'], row['hours'],
            row['count_acc'], row['task']
        ]
        worksheet.append_row(values)


def compare_data(new_data_file, old_data_file):
    with open(new_data_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    with open(old_data_file, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    changes = {
        'new': [],
        'modified': []
    }

    old_record_ids = [row['record_id'] for row in old_data]
    for new_row in new_data:
        # check if the row is new
        if new_row['record_id'] not in old_record_ids:
            changes['new'].append(new_row)
        else:
            # check if the row has been modified
            for old_row in old_data:
                if new_row['record_id'] == old_row['record_id']:
                    if new_row != old_row:
                        changes['modified'].append(new_row)
                    break
    print(changes)
    return changes


def get_notion_data():
    
    db_rows = notion_client.databases.query(database_id=database_id)

    # with open('test.json', 'w') as f:
    #     content = json.dumps(db_rows)
    #     f.write(content)

    simple_rows = []

    # cache to store data from 'Task' and 'Owner'
    cache = {}

    for row in db_rows['results']:
        record_id = get_nested_value(row, 'id')

        comment = get_nested_value(row, 'properties.Comment.title.0.plain_text')
        if comment is not None:
            comment = comment.replace('"', '\'').replace('\\', '').replace('”', '\'').replace('“', '\'') # 54816da4-399c-49b6-a933-f3d0f84e325c -- 1c71b4d0-34e2-46b8-b0f9-494700e656ab
            comment = comment.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        else:
            comment = ''

        work_time_start = get_nested_value(row, 'properties.Work time.date.start')
        if work_time_start is not None:
            work_time_start_dt = datetime.fromisoformat(work_time_start)
            work_time_start = work_time_start_dt.strftime('%d.%m.%Y')
        else:
            work_time_start = ''

        work_time_end = get_nested_value(row, 'properties.Work time.date.end')
        if work_time_end is not None:
            # work_time_end = work_time_end[:10]
            work_time_end_dt = datetime.fromisoformat(work_time_end)
            work_time_end = work_time_end_dt.strftime('%d.%m.%Y')
        else:
            work_time_end = ''

        hours = get_nested_value(row, 'properties.Hours.formula.number')

        count_acc = get_nested_value(row, 'properties.Count acc.number')
        if count_acc is None:
            count_acc = ''

        # get 'Task' from related page
        task_related_data = get_nested_value(row, 'properties.🔳 Task.relation')
        task_related_page_ids = [item["id"] for item in task_related_data]
        tasks = []
        for task_related_page_id in task_related_page_ids:
            # check if the task name is already in the cache
            if task_related_page_id in cache:
                tasks.append(cache[task_related_page_id])
            else:
                task_related_page = notion_client.pages.retrieve(task_related_page_id)
                task_name = get_nested_value(task_related_page, 'properties.Name.title.0.plain_text')
                tasks.append(task_name)
                cache[task_related_page_id] = task_name
        task = ', '.join(tasks)

        # get 'Owner' from related page
        owner_related_page_id = get_nested_value(row, 'properties.Owner.relation.0.id')
        owner = ''
        if owner_related_page_id is not None:
            # check if the owner name is already in the cache
            if owner_related_page_id in cache:
                owner = cache[owner_related_page_id]
            else:
                owner_related_page = notion_client.pages.retrieve(owner_related_page_id)
                owner = get_nested_value(owner_related_page, 'properties.Name.title.0.plain_text')
                cache[owner_related_page_id] = owner

        simple_rows.append({
            'record_id': record_id,
            'comment': comment,
            'work_time_start': work_time_start,
            'work_time_end': work_time_end,
            'owner': owner,
            'hours': hours,
            'count_acc': count_acc,
            'task': task
        })
    return simple_rows


def main():
    headers = [
        'Record_id', 'Comment', 'Work Time Start', 'Work Time End',
        'Owner', 'Hours', 'Count Acc', 'Task'
    ]
    if not check_headers(worksheet, headers):

        worksheet.append_row(headers, table_range='A5:H5')
        worksheet.format('A5:H5', {'textFormat': {'bold': True}})

    last_update_time = time.time()
    while True:
        try:
            # check the value of cell A1
            time.sleep(1)
            update_value = worksheet.acell('A3').value
            current_time = time.time()
            if update_value == 'update' or current_time - last_update_time >= 20:
                # Get the new data from Notion
                worksheet.update_acell('A3', '')

                if not check_headers(worksheet, headers):
                    # worksheet.append_row(headers, table_range='A5:H5')
                    worksheet.update('A5:H5', [headers])
                    worksheet.format('A5:H5', {'textFormat': {'bold': True}})

                new_notion_data = get_notion_data()
                # Save the new data to a json file
                write_data_as_json(new_notion_data, 'new_notion_data.json')
                # Compare the new data with the old data using the compare_data function and json files
                changes = compare_data('new_notion_data.json', 'notion_data.json')
                # Update the Google Sheet with the changes
                update_google_sheets(changes)
                # write the new data to the old json so that the two files are updated to the current version
                write_data_as_json(new_notion_data, 'notion_data.json')
                logging.info('Records successfully updated in Google Sheets')
                last_update_time = current_time
        except Exception as er:
            logging.error(f'Exception: {er}')

if __name__ == '__main__':
    main()
