import os

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

SECRETS_DIR = os.path.join(os.path.expanduser('~'), '.google_drive')
SECRETS_FILE = "credentials.json"
CREDS_FILE = "credentials.txt"
SECRETS_PATH = os.path.join(SECRETS_DIR, SECRETS_FILE)
CREDS_PATH = os.path.join(SECRETS_DIR, CREDS_FILE)
LIST_CMD = {'q': "'root' in parents and trashed=false"}

GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = SECRETS_PATH

class Downloader(object):
    """
    Wrapper class to simplify authentication & file listing with Google Drive
    using PyDrive
    """

    def __init__(self):
        self._drive = None

        if not os.path.exists(SECRETS_PATH):
            if not os.path.exists(SECRETS_DIR):
                os.mkdir(SECRETS_DIR)

            raise RuntimeError("Please put a %s file in %s" % (SECRETS_FILE,
                                                               SECRETS_DIR))
        
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile(CREDS_PATH)

        if gauth.credentials is None:
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile(CREDS_PATH)
        self._drive = GoogleDrive(gauth)

    def get_file(self, filename):
        """
        Download a file from authenticated google drive account by filename

        :param str filename: name of file to download
        :return: True if file was downloaded successfully, False otherwise
        :rtype: bool
        """

        if self._drive is None:
            raise RuntimeError("Not authenticated")

        file_list = self._drive.ListFile(LIST_CMD).GetList()
        for filedata in file_list:
            if filedata['title'] == filename:
                try:
                    filedata.GetContentFile(filename)
                except Exception as e:
                    print(e)
                    return False

                return True

        return False

    def file_listing(self):
        """
        Get a list of the names of files available to download

        :return: list of filenames available for download
        :rtype: list
        """

        if self._drive is None:
            raise RuntimeError("Not authenticated")

        file_list = self._drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
        return [f['title'] for f in file_list]


if __name__ == "__main__":
    d = Downloader()
    for filename in d.file_listing():
        print filename
