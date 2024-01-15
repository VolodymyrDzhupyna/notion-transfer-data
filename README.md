# Data synchronization module between Notion and Google Sheets

This module allows you to synchronize data between Notion database and Google Sheets worksheet. It uses Notion API and Google Sheets API to retrieve and update data.

## Customizing credentials

To use this module, you must have credentials configured for Notion API and Google Sheets API. The credentials for Notion API are stored in the `notion_config.py` file, and the credentials for Google Sheets API are stored in the `google_config.json` file, where the service account (service_account) is stored. In the access settings of the google table we will work with via API, we need to add the email address of the service account ("client_email").
Example `google_config.json`
{
  "type": "service_account",
  "project_id": "here your project_id",
  "private_key_id": "here your private key id",
  "private_key": "here your private key",
  "client_email": "here your client_email",
  "client_id": "here your client_id",
  "auth_uri": "here your auth_uri",
  "token_uri": "here your token_uri",
  "auth_provider_x509_cert_url": "here your auth_provider_x509_cert_url",
  "client_x509_cert_url": "here your client_x509_cert_url",
  "universe_domain": "googleapis.com"
}

Example `notion_config.py`
secret = {
    'api_key': 'here your api_key',
    'database_id': 'here your database_id'
}


## Installing project requirements packages

```commandline
pip install -r requirements.txt
```

## Launch

```commandline
transfer_data.py
```

This will launch a module that allows you to update data in Google Sheets. When the user clicks the "Update data" button, the module retrieves data from the Notion database, compares it to the previous version of the data, writes the changes to Google Sheets, and updates the JSON files with the data. It is necessary that the json files ('new_notion_data.json', 'notion_data.json') are in the same directory as the running module (transfer_data.py), because these json files contain the entire Notion database. Also, the credentials for the Notion API in `notion_config.py` and the credentials for the Google Sheets API in `google_config.json` must be in the same directory as the launcher.