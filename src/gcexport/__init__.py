# HACK: if not utf-8, change so minidom doesn't mess up when it 
# encouters unicode chars -- i.e. when it calls ''.join(foo)
import sys
enc = sys.getdefaultencoding()
if enc != 'utf-8':
    reload(sys)
    sys.setdefaultencoding('utf-8')

