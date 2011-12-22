Git update hook Nitty Committy
==============================
Git update hook that manages a commit message histogram
and complains about or blocks pushes with messages that are too common.

Usage as hook
-------------
Copy/symlink update.py to hooks/update in the git repo to protect.

This script will be invoked by git with three arguments: 
1) ref name
2) current SHA1 of that ref (or 0000...0 for new refs)
3) newly pushed SHA1 for the ref

Additional usage
----------------
Additionally you can also invoke this script manually without with extra
options (and possibly without those hook-related argments) 
for inspection or additional functionality. 
Use option --help for more info.
