import os

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

SECRETS_DIR = os.path.join(os.path.expanduser('~'), '.google_drive')
SECRETS_FILE = "credentials.json"
CREDS_FILE = "credentials.txt"
SECRETS_PATH = os.path.join(SECRETS_DIR, SECRETS_FILE)
CREDS_PATH = os.path.join(SECRETS_DIR, CREDS_FILE)

GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = SECRETS_PATH

DIR_LIST_KEY = "list"
DIR_ID_KEY = "id"
DIR_NAME_KEY = "name"

# Split a path into individual components
def pathsplit(path):
    folders = []
    path = os.path.normpath(path)

    while 1:
	path, folder = os.path.split(path)

	if folder != "":
	    folders.append(folder)
	else:
	    break

    folders.reverse()
    return folders

class Downloader(object):
    """
    Wrapper class to simplify authentication & file listing with Google Drive
    using PyDrive.
    """

    def __init__(self):
        self._drive = None
        self._tree = None

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

    # Recursively build up a tree of all files and subfolders
    def _build_tree(self, parent='root'):
        tree = []
        list_cmd = {'q': "'%s' in parents and trashed=false" % parent}
        file_list = self._drive.ListFile(list_cmd).GetList()

        for f in file_list:
            if f['mimeType']=='application/vnd.google-apps.folder': # if folder
                tree.append({
                    DIR_ID_KEY : f['id'],
                    DIR_NAME_KEY : f['title'],
                    DIR_LIST_KEY : self._build_tree(f['id'])
                })
            else:
                tree.append(f['title'])

        return tree

    # Given a tree of all files and subfolders, generate a list of paths to all files
    def _file_listing_from_tree(self, tree, parentname=''):
        ret = []

        for item in tree:
            if type(item) in [unicode, str]:
                ret.append(os.path.join(parentname, item))
            elif type(item) is dict:
                dirname = os.path.join(parentname, item[DIR_NAME_KEY])
                ret.extend(self._file_listing_from_tree(item[DIR_LIST_KEY], dirname))

        return ret

    # Given the path to a drive file, find the ID of the containing folder
    def _get_folder_id_from_path(self, path_components):
        if self._tree is None:
            self._tree = self._build_tree()

        dirnames = path_components[:-1]
        curr = self._tree
        folder_id = None
        i = 0

        for i in range(len(dirnames)):
            found = False
            for item in curr:
                if (type(item) is dict) and (item[DIR_NAME_KEY] == dirnames[i]):
                    curr = item[DIR_LIST_KEY]
                    folder_id = item[DIR_ID_KEY]
                    found = True
                    break

            if not found:
                return None

        return folder_id

    # Get a list of filenames in the given directory
    def _list_files_in_dir(self, dir_id='root'):
        list_cmd = {'q': "'%s' in parents and trashed=false" % dir_id}
        return self._drive.ListFile(list_cmd).GetList()

    def _file_not_found(self, filename):
        raise RuntimeError("Unable to find file '%s'" % filename)

    def download_file(self, file_path, force=False):
        """
        Download a file from authenticated google drive account by filename.
        Raises RuntimeError if downloading the file fails for any reason.

        :param str file_path: path to file to download.
        :param bool force: if True, the file will be ovewritten if it already\
            exists locally. If False, an exception will be thrown if the file\
            already exists locally.
        """

        if self._drive is None:
            raise RuntimeError("Not authenticated")

        filename = None
        folderid = None

        parts = pathsplit(file_path)
        if len(parts) == 1:
            # Path has 1 part only, no subfolders
            folderid = 'root'
            filename = file_path
        else:
            # Path has multiple parts, find corresponding subfolder ID
            folderid = self._get_folder_id_from_path(parts)
            if folderid is None:
                self._file_not_found(file_path)

            filename = parts[-1]

        file_list = self._list_files_in_dir(folderid)

        for filedata in file_list:
            if filedata['title'] == filename:
                if (not force) and os.path.exists(filedata['title']):
                    raise RuntimeError("local file already exists: %s"
                                       % filedata['title'])

                filedata.GetContentFile(filedata['title'])
                return

        self._file_not_found(file_path)

    def file_listing(self):
        """
        Get a list of the names of files available to dowload. Subfolders are
        indicated using the standard path seperator for your system, e.g.
        ["folder/file1.txt", "folder/subfolder/file2.txt"]

        :return: list of filenames available for download.
        :rtype: list
        """

        if self._drive is None:
            raise RuntimeError("Not authenticated")

        self._tree = self._build_tree()
        return self._file_listing_from_tree(self._tree)

if __name__ == "__main__":
    d = Downloader()
    for filename in d.file_listing():
        print(filename)

    # Example output:
    # ['file1.txt', 'subfolder/file2.txt']

    # Example of downloading a file:
    # d.download_file('subfolder/file2.txt')
