import os

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

SECRETS_DIR = os.path.join(os.path.expanduser('~'), '.google_drive')
SECRETS_FILE = os.path.join(SECRETS_DIR, "client_secrets.json")
CREDS_FILE = os.path.join(SECRETS_DIR, "client_credentials.txt")

class Downloader(object):
    def __init__(self):
        self._drive = None

        if not os.path.exists(SECRETS_FILE):
            if not os.path.exists(SECRETS_DIR):
                os.mkdir(SECRETS_DIR)

            raise RuntimeError("cannot find file %s" % SECRETS_FILE)
        
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile(CREDS_FILE)
        if gauth.credentials is None:
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile(CREDS_FILE)
        self._drive = GoogleDrive(gauth)

    def file_listing(self):
        if self._drive is None:
            raise RuntimeError("Not authenticated")

        file_list = self._drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
        for file1 in file_list:
            print('title: %s, id: %s' % (file1['title'], file1['id']))

d = Downloader()
d.file_listing()
