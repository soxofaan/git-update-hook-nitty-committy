Git update hook Nitty Committy
==============================
Git update hook that manages a commit message histogram
and complains about or blocks pushes with messages that are too common.

Usage as hook
-------------

Usage as a git hook is very easy: just copy/symlink the file ``update.py`` to a file
``hooks/update`` (without extension) inside the git repo to protect and you're done.

As a hook, this script will be invoked by git with three arguments: 

1. ref name (e.g. 'refs/head/master')

2. current SHA1 of that ref (or 0000...0 for new refs)

3. newly pushed SHA1 for the ref

Depending on the operational mode, the hook will just complain on standard output
with a warning or block the git push.

Additional usage
----------------
Additionally you can also invoke this script manually without with extra
options (and possibly without those hook-related argments) 
for inspection or additional functionality. 
Use option --help for more info.

Configuration
-------------
TBW
