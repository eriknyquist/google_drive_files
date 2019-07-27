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

    # Given the path to a directory, return the tree data for that directory
    def _get_dir_tree_from_path(self, path_components):
        curr = self._tree
        i = 0

        for i in range(len(path_components)):
            found = False
            for item in curr:
                if (type(item) is dict) and (item[DIR_NAME_KEY] == path_components[i]):
                    if i == (len(path_components) - 1):
                        return item

                    curr = item[DIR_LIST_KEY]
                    found = True
                    break

            if not found:
                return None

        return None

    # Get a list of filenames in the given directory
    def _list_files_in_dir(self, dir_id='root'):
        list_cmd = {'q': "'%s' in parents and trashed=false" % dir_id}
        return self._drive.ListFile(list_cmd).GetList()

    def _file_not_found(self, filename):
        raise RuntimeError("Unable to find drive file '%s'" % filename)

    def download_files(self, file_paths, force=False):
        """
        Download a file from authenticated google drive account by filename.
        Raises RuntimeError if downloading the file fails for any reason.

        :param list file_paths: List of files to download. Items in the list\
            can either be be the filename of the file to download as a string,\
            where the file will be downloaded with the same name in the current\
            local directory, or a tuple of the form ``(src, dest)``, where\
            ``src`` is the name of the file to download and ``dest`` is the \
            name of the file to create on your local system.
        :param bool force: if True, files will be ovewritten if they already\
            exist locally. If False, an exception will be thrown if they \
            already exist locally.
        :return: True if all files were downloaded
        :rtype: bool
        """

        if self._drive is None:
            raise RuntimeError("Not authenticated")

        if self._tree is None:
            self._tree = self._build_tree()

        # Build dict of folder IDs and filename lists
        files_to_download = {}
        default_id = 'root'

        for pathdata in file_paths:
            filename = None
            dest_filename = None

            if type(pathdata) in [str, unicode]:
                # dest. file will use the same filename as source file
                filename = pathdata
                dest_filename = os.path.basename(pathdata)
            elif (type(pathdata) == tuple) and (len(pathdata) == 2):
                # dest. filename given
                filename, dest_filename = pathdata
            else:
                raise ValueError("Error downloading file '%s': download paths "
                                 "must be string, or tuple with two items" % pathdata)

            # use our internal tree representation of all files and subdirectories
            # to convert the given list of filenames to a dict, where the key is
            # a directory ID and the value is a list of filenames inside that
            # directory.
            parts = pathsplit(filename)
            if len(parts) == 1:
                # file is in root directory, no need to find a directory ID
                if default_id not in files_to_download:
                    files_to_download[default_id] = []

                files_to_download[default_id].append((filename, dest_filename))

            else:
                # file is in subdirectory, find containing directory ID
                dirtree = self._get_dir_tree_from_path(parts[:-1])
                if dirtree is None:
                    self._file_not_found(filename)

                folderid = dirtree[DIR_ID_KEY]
                if folderid not in files_to_download:
                    files_to_download[folderid] = []

                files_to_download[folderid].append((parts[-1], dest_filename))

        # download all files, one subdirectory at a time
        statuses = []
        for folderid in files_to_download:
            ret = self._download_files_from_dir(folderid, files_to_download[folderid], force)
            statuses.append(ret)

        return False in statuses

    # Download one or more files from the same directory
    def _download_files_from_dir(self, folderid, filenames, force):
        file_list = self._list_files_in_dir(folderid)
        num_downloaded = 0
        dest_map = {src: dest for src, dest in filenames}

        for filedata in file_list:
            if filedata['title'] in dest_map:
                dest_filename = dest_map[filedata['title']]
                if (not force) and os.path.exists(dest_filename):
                    raise RuntimeError("local file already exists: %s" % dest_filename)

                try:
                    filedata.GetContentFile(dest_filename)
                except Exception as e:
                    print("Failed to download file %s: %s" % (dest_filename, str(e)))
                else:
                    num_downloaded += 1

        return num_downloaded == len(filenames)

    def file_listing(self, directory_name=None):
        """
        Get a list of the names of files available to dowload. Subfolders are
        indicated using the standard path seperator for your system, e.g.
        ["folder/file1.txt", "folder/subfolder/file2.txt"]

        :param str directory_name: name of directory to list files under. If \
            unset, the root directory will be used.
        :return: list of filenames available for download.
        :rtype: list
        """

        if self._drive is None:
            raise RuntimeError("Not authenticated")

        if self._tree is None:
            self._tree = self._build_tree()

        if directory_name is None:
            dir_tree = self._tree
            parentname = ''
        else:
            parts = pathsplit(directory_name)
            dir_tree = self._get_dir_tree_from_path(parts)
            parentname = directory_name

        return self._file_listing_from_tree(dir_tree, parentname)

if __name__ == "__main__":
    d = Downloader()
    for filename in d.file_listing():
        print(filename)

    # Example output:
    # ['file1.txt', 'subfolder/file2.txt']

    # Example of downloading files into the current directory:
    # d.download_files(['file1.txt', 'subfolder/file2.txt'])

    # Example of downloading files with explicit destination paths:
    # d.download_files([
    #    ('file1.txt', '/home/file1.txt'),
    #    ('subfolder/file2.txt', '/home/file2.txt')
    # ])
