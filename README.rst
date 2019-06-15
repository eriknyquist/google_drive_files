First time setup
================

#. Install PyDrive package:

   ::

       pip install pydrive

#. Open a browser and log into the Google Drive account that you would like to
   access files from

#. Visit the `"Python Quickstart" page for the Google Drive REST API <https://developers.google.com/drive/api/v3/quickstart/python>`_,
   and click the "ENABLE THE DRIVE API" button.

#. In the resulting dialog, click "DOWNLOAD CLIENT CONFIGURATION"

#. The downloaded file ``credentials.json`` needs to be moved to a specific
   directory. Run the ``google_drive_files.py`` script with no arguments: it
   will detect that ``credentials.json`` is missing and print a message telling
   you where it needs to go on your system.

   ::

	   $ python google_drive_files.py

	   Traceback (most recent call last):
	     File "google_drive_files.py", line 84, in <module>
		   d = Downloader()
	     File "google_drive_files.py", line 29, in __init__
		   SECRETS_DIR))
	   RuntimeError: Please put a credentials.json file in /home/erik/.google_drive

#. Once ``credentials.json`` is in the right directory, run
   ``google_drive_files.py`` again, and it will open a browser window and
   prompt you to log in to google drive. **Log in to the account containing the
   files you want to access** (TODO: not sure about this, maybe any account
   with access to the source account would work).

#. You're done, you should now be able to download files using
   ``google_drive_files.Downloader`` without logging in or re-authenticating,
   as long as you don't delete the ``credentials.json`` file or the
   ``credentials.txt`` file that was created alongside it.


Downloading files
=================

If you already know the name of the file you want you can just call
``download_file()`` with the filename. Otherwise, you can get a list of available
filenames with ``file_listing()``. The following example shows both:

::

    >>> from google_drive_files import Downloader
    >>> d = Downloader()
    >>> d.file_listing()
    [u'file1.txt', u'file2.txt', u'file3.txt']
    >>> d.download_files(['file1.txt', 'file3.txt'])
    True
    >>>

