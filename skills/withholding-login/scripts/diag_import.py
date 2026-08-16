import sys, traceback
sys.path.insert(0, r"C:/rpa")
try:
    import check_status
    msg = "IMPORT_OK"
except Exception as e:
    msg = "IMPORT_FAIL: %r\n%s" % (e, traceback.format_exc())
open(r"C:/rpa/diag_import.txt", "w").write(msg)
