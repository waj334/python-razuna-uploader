import os
import sys

import requests
from requests_toolbelt.multipart import encoder

import xmltodict

import tkinter as tk
from tkinter import filedialog

from pathlib import Path

ignore = {
    '',
    '.',
    '$',
    'RECYCLER',
    'autorun.ini',
    'System Volume Information'
}

tkroot = tk.Tk()
tkroot.withdraw()

rootPath = ''
c = 0

while len(rootPath) == 0:
    if c > 3:
        input("Invalid path. Press Enter To Exit...")
        sys.exit()
    else:
        rootPath = filedialog.askdirectory()
        tkroot.focus()
        c = c+1

print("Selected {0}".format(rootPath))

endpoint = 'http://[ADDRESS TO TOMCAT SERVER]/razuna/global/api2'
upload_url = 'http://[ADDRESS TO TOMCAT SERVER]/razuna/raz2/dam/index.cfm'
apiKey = 'GET YOUR OWN'
folder_id = ''

# Folder ID Entry Box
c = 0
while len(folder_id) == 0:
    if c > 3:
        input("Invalid path. Press Enter To Exit...")
        sys.exit()
    else:
        folder_id = input("Enter Folder ID: ")
        c += 1

def get_folder(id):
    params = {
        'method': 'getfolder',
        'api_key': apiKey,
        'folderid': id,
    }

    r = requests.post(endpoint+'/folder.cfc', params=params)

    if r.status_code == requests.codes.ok:
        data = r.json()

    return data

def create_folder(name, parent_id):
    params = {
        'method': 'setfolder',
        'api_key': apiKey,
        'folder_name': name,
        'folder_related': parent_id
    }

    r = requests.post(endpoint+'/folder.cfc', params=params)

    if r.status_code == requests.codes.ok:
        data = r.json()
        if int(data['responsecode']) == 0:
            print('Created folder "{0}" ID: {1}'.format(name, data['folder_id']))

        # Wait for folder to become available
            while True:
                f = get_folder(data['folder_id'])
                
                if len(f['DATA']) > 0:
                    break

            return data['folder_id']
        else:
            print('Could not create folder "{0}"'.format(name))
            return -1

    return -1

def upload(fname, folderid):
    if os.path.getsize(fname) == 0:
        print ("{0} is empty! Skipping...".format(os.path.split(fname)[1]))
        return 0

    try:
        file = open(fname, 'rb')
    except Exception:
        print ("{0} could not be opened! Skipping...".format(os.path.split(fname)[1]))
        return 0

    payload = encoder.MultipartEncoder(
        {
            'fa': 'c.apiupload',
            'api_key': apiKey,
            'destfolderid': folderid,
            'filedata': (fname.name, file, "application/octet-stream")
        }
    )

    print ("Uploading {0}...".format(os.path.split(fname)[1]))
    r = requests.post(upload_url, data=payload, headers={"Content-Type": payload.content_type})

    file.close()

    if r.status_code == requests.codes.ok:
        data = xmltodict.parse(r.content)
        if int(data['Response']['responsecode']) == 0:
            print('Uploaded {0}'.format(os.path.split(fname)[1]))
            return 0
        else:
            if data['Response']['message'] == 'File already exists in Razuna':
                print("File already exists! Skipping...")
                return 0
            else:
                print('Could not upload {0}'.format(os.path.split(fname)[1]))
                print(data['Response']['message'])
    return -1

def process(basePath, parent):
    path = Path(basePath)
    foldername = os.path.basename(path)

    if len(foldername) == 0:
        # Upload directly to parent
        fid = parent
    else:
        # Create this folder
        fid = create_folder(foldername, parent)

    if fid == -1:
        return -1

    for p in os.listdir(path):
         # Ignore some files or folders
        if p[0] in ignore or p in ignore:
            continue

        #absolute path
        absPath = path.joinpath(p)
        # absPath = basePath+'/'+p

        if os.path.isfile(absPath):
            # Upload any files in this path
            if upload(absPath, fid) == -1:
                return -1
        else: # Recursively upload subdirs

            if process(absPath, fid) == -1:
                return -1
    return 0

# Begin Upload Routine
print("Upload Started...")
if process(rootPath, folder_id) == -1:
    print("!!! Upload Failed !!!")
else:
    print("Upload Complete")

input("Press Enter to Exit...")
